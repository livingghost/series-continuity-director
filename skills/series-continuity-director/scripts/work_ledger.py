#!/usr/bin/env python3
"""The open task and the trail of tasks in a project, so work survives a lost context.

A project holds one open task at a time in `work/current.json`: the goal, the
steps planned, which are done, what comes next, and what it is blocked on. Every
change to it is also appended to `work/ledger.jsonl`, which is never rewritten.
A session that starts without memory of what it was doing reads the open task
and continues from `next`; a session that finds no open task reads the last
finished ones and asks what to do.

Open a task before work that takes more than one step. Mark each step as it is
done, not at the end. Finish the task when every step is done, or abandon it
with the reason. A step that is not written down is a step the next session
does again or skips.

Every change holds the project lock that production runs hold, and the open
task is replaced in one step, so two sessions marking steps at once both land.
The command writes only into a project: a directory holding
project-manifest.json, outside the installed suite.

    python scripts/work_ledger.py --project DIR begin --goal "..." --step "..." --step "..."
    python scripts/work_ledger.py --project DIR step <n> [--note "..."]
    python scripts/work_ledger.py --project DIR note "..."
    python scripts/work_ledger.py --project DIR block "the question the user has to answer"
    python scripts/work_ledger.py --project DIR finish
    python scripts/work_ledger.py --project DIR abandon --reason "..."
    python scripts/work_ledger.py --project DIR show
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import execution_contract as c
from project_layout import refuse_suite, require_project

WORK_DIR = "work"
CURRENT = "current.json"
LEDGER = "ledger.jsonl"
EVENTS = ("opened", "step", "note", "blocked", "finished", "abandoned")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def work_dir(root: Path) -> Path:
    return root / WORK_DIR


def read_current(root: Path) -> dict[str, Any] | None:
    """The open task, or None. A file that is not a task raises ValueError saying so."""

    path = work_dir(root) / CURRENT
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"{WORK_DIR}/{CURRENT} is not a readable task ({exc}); it was cut off or edited by "
            f"hand. {WORK_DIR}/{LEDGER} holds every step recorded for it: rewrite the file from "
            "there, or remove it and open the task again"
        ) from exc
    if not isinstance(value, dict):
        raise ValueError(f"{WORK_DIR}/{CURRENT}: not an object")
    return value


def write_current(root: Path, value: dict[str, Any] | None) -> None:
    """Replace or remove the open task in one step, under the project lock."""

    refuse_suite(root)
    path = work_dir(root) / CURRENT
    with c.lock(root):
        if value is None:
            path.unlink(missing_ok=True)
            return
        c.atomic(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
                 replace=True)


def append(root: Path, entry: dict[str, Any]) -> None:
    refuse_suite(root)
    path = work_dir(root) / LEDGER
    with c.lock(root):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_ledger(root: Path) -> list[dict[str, Any]]:
    path = work_dir(root) / LEDGER
    if not path.is_file():
        return []
    entries = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{WORK_DIR}/{LEDGER}:{number}: not a JSON line ({exc})") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{WORK_DIR}/{LEDGER}:{number}: not an object")
        entries.append(value)
    return entries


def next_step(task: dict[str, Any]) -> dict[str, Any] | None:
    for step in task.get("steps") or []:
        if not step.get("done_at"):
            return step
    return None


def refreshed(task: dict[str, Any]) -> dict[str, Any]:
    step = next_step(task)
    task["next"] = step["text"] if step else None
    return task


def new_task_id(root: Path) -> str:
    count = sum(1 for entry in read_ledger(root) if entry.get("event") == "opened")
    return f"t{count + 1:04d}"


def _begin(root: Path, goal: str, steps: list[str]) -> dict[str, Any]:
    if read_current(root) is not None:
        raise ValueError("a task is already open; finish or abandon it before opening another")
    if not goal.strip():
        raise ValueError("a task needs a goal")
    if not steps or not all(text.strip() for text in steps):
        raise ValueError("a task needs at least one step, each with text")
    task = refreshed({
        "task_id": new_task_id(root),
        "goal": goal.strip(),
        "opened_at": now(),
        "steps": [{"n": index, "text": text.strip(), "done_at": None} for index, text in enumerate(steps, 1)],
        "next": None,
        "notes": [],
        "blocked_on": None,
    })
    write_current(root, task)
    append(root, {"at": task["opened_at"], "task_id": task["task_id"], "event": "opened", "text": task["goal"],
                  "steps": [step["text"] for step in task["steps"]]})
    return task


def require_open(root: Path) -> dict[str, Any]:
    task = read_current(root)
    if task is None:
        raise ValueError("no task is open")
    return task


def _step_done(root: Path, number: int, note: str | None = None) -> dict[str, Any]:
    task = require_open(root)
    steps = task.get("steps") or []
    found = next((step for step in steps if step.get("n") == number), None)
    if found is None:
        raise ValueError(f"the open task has no step {number}; it has 1 to {len(steps)}")
    if found.get("done_at"):
        raise ValueError(f"step {number} is already done")
    found["done_at"] = now()
    if note:
        found["note"] = note.strip()
    task["blocked_on"] = None
    write_current(root, refreshed(task))
    append(root, {"at": found["done_at"], "task_id": task["task_id"], "event": "step", "n": number,
                  "text": found["text"], "note": note.strip() if note else None})
    return task


def _note(root: Path, text: str) -> dict[str, Any]:
    task = require_open(root)
    if not text.strip():
        raise ValueError("a note needs text")
    task.setdefault("notes", []).append(text.strip())
    write_current(root, task)
    append(root, {"at": now(), "task_id": task["task_id"], "event": "note", "text": text.strip()})
    return task


def _block(root: Path, question: str) -> dict[str, Any]:
    task = require_open(root)
    if not question.strip():
        raise ValueError("say what the task is blocked on")
    task["blocked_on"] = question.strip()
    write_current(root, task)
    append(root, {"at": now(), "task_id": task["task_id"], "event": "blocked", "text": question.strip()})
    return task


def _finish(root: Path) -> dict[str, Any]:
    task = require_open(root)
    left = [step for step in task.get("steps") or [] if not step.get("done_at")]
    if left:
        raise ValueError(
            f"{len(left)} step(s) are not done: " + "; ".join(f"{s['n']} {s['text']}" for s in left)
            + ". Mark them done, or abandon the task with the reason."
        )
    if task.get("production_run"):
        from production_workflow import verify_completion
        verify_completion(root, task["production_run"], task["task_id"])
    append(root, {"at": now(), "task_id": task["task_id"], "event": "finished", "text": task["goal"]})
    write_current(root, None)
    return task


def _abandon(root: Path, reason: str) -> dict[str, Any]:
    task = require_open(root)
    if not reason.strip():
        raise ValueError("abandoning a task needs the reason")
    append(root, {"at": now(), "task_id": task["task_id"], "event": "abandoned", "text": reason.strip(),
                  "left": [s["text"] for s in task.get("steps") or [] if not s.get("done_at")]})
    write_current(root, None)
    return task


def begin(root: Path, goal: str, steps: list[str]) -> dict[str, Any]:
    """Open a task, under the project lock."""

    refuse_suite(root)
    with c.lock(root):
        return _begin(root, goal, steps)


def step_done(root: Path, number: int, note: str | None = None) -> dict[str, Any]:
    """Mark one step of the open task done, under the project lock."""

    refuse_suite(root)
    with c.lock(root):
        return _step_done(root, number, note)


def note(root: Path, text: str) -> dict[str, Any]:
    """Add a note to the open task, under the project lock."""

    refuse_suite(root)
    with c.lock(root):
        return _note(root, text)


def block(root: Path, question: str) -> dict[str, Any]:
    """Record what the open task waits on, under the project lock."""

    refuse_suite(root)
    with c.lock(root):
        return _block(root, question)


def finish(root: Path) -> dict[str, Any]:
    """Close the open task once every step is done, under the project lock."""

    refuse_suite(root)
    with c.lock(root):
        return _finish(root)


def abandon(root: Path, reason: str) -> dict[str, Any]:
    """Close the open task without finishing it, under the project lock."""

    refuse_suite(root)
    with c.lock(root):
        return _abandon(root, reason)


def show(root: Path) -> str:
    """What a session reads first: the open task and where it stands, or the trail."""
    task = read_current(root)
    lines: list[str] = []
    if task is not None:
        steps = task.get("steps") or []
        done = sum(1 for step in steps if step.get("done_at"))
        lines.append(f"open task {task['task_id']}: {task['goal']} ({done} of {len(steps)} steps done, opened {task.get('opened_at')})")
        for step in steps:
            mark = "done" if step.get("done_at") else "    "
            lines.append(f"  [{mark}] {step['n']}. {step['text']}" + (f"  ({step['note']})" if step.get("note") else ""))
        if task.get("blocked_on"):
            lines.append(f"  blocked on: {task['blocked_on']}")
        elif task.get("next"):
            lines.append(f"  next: {task['next']}")
        for text in (task.get("notes") or [])[-5:]:
            lines.append(f"  note: {text}")
        return "\n".join(lines)
    finished = [entry for entry in read_ledger(root) if entry.get("event") in ("finished", "abandoned")]
    if not finished:
        return "no task is open, and none has been recorded; open one before work that takes more than one step"
    lines.append("no task is open; the last recorded:")
    for entry in finished[-3:]:
        lines.append(f"  {entry.get('at')} {entry.get('event')} {entry.get('task_id')}: {entry.get('text')}")
    return "\n".join(lines)


def check(root: Path) -> list[str]:
    """What a validator reports: an unreadable ledger, or an open task the ledger does not know."""
    errors: list[str] = []
    try:
        entries = read_ledger(root)
    except ValueError as exc:
        return [str(exc)]
    opened = [entry.get("task_id") for entry in entries if entry.get("event") == "opened"]
    if len(opened) != len(set(opened)):
        errors.append(f"{WORK_DIR}/{LEDGER}: a task id is opened twice")
    for number, entry in enumerate(entries, 1):
        for name in ("at", "task_id", "event"):
            if not isinstance(entry.get(name), str) or not entry[name]:
                errors.append(f"{WORK_DIR}/{LEDGER}:{number}: {name} is missing")
        if entry.get("event") not in EVENTS:
            errors.append(f"{WORK_DIR}/{LEDGER}:{number}: unknown event {entry.get('event')!r}")
    try:
        task = read_current(root)
    except ValueError as exc:
        return errors + [str(exc)]
    if task is not None:
        if task.get("task_id") not in opened:
            errors.append(f"{WORK_DIR}/{CURRENT}: task {task.get('task_id')!r} was never opened in the ledger")
        closed = {entry.get("task_id") for entry in entries if entry.get("event") in ("finished", "abandoned")}
        if task.get("task_id") in closed:
            errors.append(f"{WORK_DIR}/{CURRENT}: task {task.get('task_id')!r} is open and the ledger says it is closed")
        steps = task.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append(f"{WORK_DIR}/{CURRENT}: the open task has no steps")
        elif task.get("next") != (next_step(task) or {}).get("text"):
            errors.append(f"{WORK_DIR}/{CURRENT}: next does not name the first step not done")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--project", type=Path, default=Path.cwd(),
                        help="The project directory, the one holding project-manifest.json "
                             "(default: the working directory)")
    commands = parser.add_subparsers(dest="command", required=True)
    begin_parser = commands.add_parser("begin", help="open a task")
    begin_parser.add_argument("--goal", required=True)
    begin_parser.add_argument("--step", action="append", default=[], help="one step, in order; repeat")
    step_parser = commands.add_parser("step", help="mark a step done")
    step_parser.add_argument("n", type=int)
    step_parser.add_argument("--note")
    note_parser = commands.add_parser("note", help="add a note to the open task")
    note_parser.add_argument("text")
    block_parser = commands.add_parser("block", help="record what the open task waits on")
    block_parser.add_argument("question")
    commands.add_parser("finish", help="close the open task; every step must be done")
    abandon_parser = commands.add_parser("abandon", help="close the open task without finishing it")
    abandon_parser.add_argument("--reason", required=True)
    commands.add_parser("show", help="print the open task, or the trail")
    args = parser.parse_args(argv)
    try:
        root = require_project(args.project)
        if args.command == "begin":
            begin(root, args.goal, args.step)
        elif args.command == "step":
            step_done(root, args.n, args.note)
        elif args.command == "note":
            note(root, args.text)
        elif args.command == "block":
            block(root, args.question)
        elif args.command == "finish":
            finish(root)
        elif args.command == "abandon":
            abandon(root, args.reason)
        shown = show(root)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(shown)
    return 0


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
