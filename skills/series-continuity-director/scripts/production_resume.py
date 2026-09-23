"""Report saved production evidence before deciding what a new execution needs."""
from __future__ import annotations
import copy
from pathlib import Path
import execution_contract as c
import reservation_lifecycle as lifecycle


def _action(operation: str, root: Path, run: str, *, args: dict | None = None,
            required: list[str] | None = None, external: str = "none",
            budget: str = "none", preserves: list[str] | None = None,
            invalidates: list[str] | None = None, actor: str | None = None) -> dict:
    return {"operation": operation, "args": {"root": str(root), "run": run, **(args or {})},
            "entrypoint": "scripts/production_workflow.py",
            "required_args": required or [], "external_effect": external,
            "budget_effect": budget, "preserves": preserves or ["saved-evidence"],
            "invalidates": invalidates or [], "actor": actor}


def _freshness(root: Path, prepared: dict, rows: list[dict], skill_root: Path) -> dict:
    dependencies = list(prepared["dependencies"])
    dependencies += [{**item, "space": "artifact", "receipt": row["sha256"]}
                     for row in rows for item in row["data"].get("files", []) + row["data"].get("evidence", [])]
    changes = []
    for item in dependencies:
        base = skill_root if item["space"] == "skill" else root
        try:
            current = c.digest(c.read(c.local(base, item["path"])))
            if current == item["sha256"]:
                continue
            reason = "bytes-changed"
        except (OSError, ValueError):
            current = None
            reason = "unavailable"
        changes.append({"space": item["space"], "path": item["path"],
                        "recorded_sha256": item["sha256"], "current_sha256": current,
                        "state": reason, "receipt": item.get("receipt")})
    reading = {"current": False, "reason": "The prepared record has no route reading."}
    if "route_reading" in prepared:
        import route_reading
        try:
            route_reading.require_route_reading(prepared["route_reading"], project=root,
                routes={prepared["task"]["route"]}, features=prepared["task"]["features"])
            reading = {"current": True}
        except c.EXPECTED_ERRORS as exc:
            reading = {"current": False, "reason": str(exc)}
    return {"current": not changes and reading["current"] is not False,
            "changes": changes, "reading": reading}


def _artifacts(rows: list[dict]) -> list[dict]:
    result = []
    for row in rows:
        if row["event"] in {"dispatch-results", "candidate", "review", "selection", "completion"}:
            result.append({"event": row["event"], "receipt": row["sha256"],
                "files": copy.deepcopy(row["data"].get("files", [])),
                "recorded": True})
    return result


def _execution(rows: list[dict], states: dict) -> dict:
    claims = [row for row in rows if row["event"] == "dispatch-claim"]
    results = [row for row in rows if row["event"] == "dispatch-results"]
    boundaries = [row for row in rows if row["event"] == "reservation-start"]
    claim = claims[-1] if claims else None
    result = next((row for row in reversed(results)
                   if claim is not None and row["data"].get("claim") == claim["sha256"]), None)
    traces = [{"receipt": row["sha256"], "stage": row["data"]["stage"],
               "files": copy.deepcopy(row["data"].get("files", []))}
              for row in rows if row["event"] == "dispatch-trace"
              and claim is not None and row["data"].get("claim") == claim["sha256"]]
    owned = [state for token, state in states.items()
             if claim is not None and lifecycle.claim_owns(claim, token)]
    candidate_files = {(item["path"], item["sha256"]) for row in rows if row["event"] == "candidate"
                       for item in row["data"].get("files", [])}
    registration = None
    if result is not None:
        registration = all((item["path"], item["sha256"]) in candidate_files for item in result["data"]["files"])
    if result is not None:
        state = "outputs-recorded"
    elif claim is not None and any(item["status"] == "started" for item in owned):
        state = "boundary-recorded-outcome-unconfirmed"
    elif claim is not None and owned and all(item["status"] == "released" for item in owned):
        state = "claim-cancelled-before-start"
    elif claim is not None:
        state = "claimed-before-start"
    else:
        state = "no-dispatch-claim"
    return {"state": state, "claim": claim["sha256"] if claim else None,
            "result_receipt": result["sha256"] if result else None,
            "candidate_registration_complete": registration,
            "boundaries": [{"receipt": row["sha256"], **copy.deepcopy(row["data"])} for row in boundaries],
            "traces": traces, "journal": claim["data"].get("journal") if claim else None,
            "provider_charge": {"confirmed": False, "basis": None},
            "new_submission_allowed_by_this_report": False}


def report(root: Path, run: str) -> dict:
    """Read frozen records first; freshness gates new work, not evidence visibility."""
    import production_workflow as workflow
    root = root.absolute()
    with c.lock(root):
        try:
            _, prepared, _, rows = workflow.load_run(root, run)
            states = lifecycle.derive(rows, prepared, run)
        except c.EXPECTED_ERRORS as exc:
            return {"ok": False, "run": run, "next": "inspect-integrity",
                    "integrity": {"ok": False, "reason": str(exc)},
                    "freshness": None, "artifacts": [], "reservations": None,
                    "execution": {"state": "unknown", "new_submission_allowed_by_this_report": False},
                    "permissions": {"assessment": "not-assessed"},
                    "blockers": [{"code": "record-integrity", "selector": run, "reason": str(exc)}],
                    "next_actions": []}
        fresh = _freshness(root, prepared, rows, workflow.ROOT)
        execution = _execution(rows, states)
        blockers = []
        if not fresh["current"]:
            blockers.append({"code": "new-execution-inputs-changed", "selector": run,
                             "reason": "Inspect changed inputs before preparing a new execution."})
        actions = []
        for token, state in states.items():
            if state["status"] == "reserved":
                actions.append(_action("draft-release", root, run, args={"reservation": token},
                    required=["out"], actor=state["actor"], budget="none-until-explicit-release",
                    preserves=["saved-evidence", "spent-reservations", "current-delegation"]))
        events = {row["event"] for row in rows}
        state = execution["state"]
        if state == "boundary-recorded-outcome-unconfirmed":
            next_stage = "recover-recording-or-resolve-remote-status"
            actions.extend(_recover_actions(root, run, execution))
        elif state == "outputs-recorded" and not execution["candidate_registration_complete"]:
            next_stage = "recover-recording"
            actions.append(_action("recover-recording", root, run,
                preserves=["same-output-bytes", "saved-request", "spent-reservations"]))
        elif "completion" in events:
            next_stage = "recorded-complete-inputs-changed"
            if fresh["current"]:
                try:
                    workflow.verify_completion(root, run, prepared["task"]["task_id"])
                    next_stage = "done"
                except c.EXPECTED_ERRORS as exc:
                    next_stage = "inspect-completion"
                    blockers.append({"code": "completion-evidence", "selector": run, "reason": str(exc)})
        elif not fresh["current"]:
            next_stage = "inspect-impact-and-refresh-inputs"
            actions.append(_action("impact", root, run,
                preserves=["saved-evidence", "accepted-history", "spent-reservations"]))
        elif state == "claim-cancelled-before-start":
            next_stage = "prepare-new-run-after-release"
            actions.append(_action("impact", root, run))
        elif state == "claimed-before-start":
            next_stage = "inspect-unstarted-claim"
        else:
            next_stage = _normal_next(workflow, root, run, prepared, rows)
        return {"ok": fresh["current"] and not blockers, "run": run, "input_sha256": prepared["input_sha256"],
                "next": next_stage, "integrity": {"ok": True}, "freshness": fresh,
                "artifacts": _artifacts(rows), "reservations": list(states.values()),
                "execution": execution, "permissions": _permissions(prepared, rows),
                "blockers": blockers, "next_actions": actions, "events": len(rows),
                "reads": prepared["route"]["reads"],
                "scope": "Saved evidence and current dependencies. Actions execute only through explicit commands."}


def _permissions(prepared: dict, rows: list[dict]) -> dict:
    authorities = [{"receipt": row["sha256"], "authorization": copy.deepcopy(row["data"]["authorization"])}
                   for row in rows if row["event"] == "authorization"]
    return {"assessment": "not-assessed-for-a-new-request", "authorizations": authorities}


def _recover_actions(root: Path, run: str, execution: dict) -> list[dict]:
    actions = [_action("impact", root, run, preserves=["saved-request", "start-boundary", "reserved-budget"])]
    # Recovery checks the retained transport response before any retrieval.
    if execution["traces"]:
        action = _action("recover-existing-results", root, run,
            external="existing-result-retrieval", budget="no-new-generation-reservation",
            preserves=["saved-request", "start-boundary", "reserved-budget"])
        action["entrypoint"] = "scripts/production_dispatch.py"
        actions.append(action)
    return actions


def _normal_next(workflow, root: Path, run: str, prepared: dict, rows: list[dict]) -> str:
    events = {row["event"] for row in rows}
    stage = "handoff"
    for event, following in [("handoff", "capture"), ("candidate", "review"),
                             ("review", "select"), ("selection", "complete")]:
        if event in events:
            stage = following
    if stage == "select":
        try:
            workflow.eligible(prepared, workflow.find(rows, "review"))
        except ValueError:
            stage = "review-or-revise-candidate"
    return stage
