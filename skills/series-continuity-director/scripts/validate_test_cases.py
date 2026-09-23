#!/usr/bin/env python3
"""Execute machine-enforceable regression cases and classify editorial cases.

The narrative catalog in examples/test-cases.md contains both executable
invariants and human editorial review prompts. Structural mutations are
re-sealed before validation so the asserted failure is the intended rule,
not a stale content hash. Hash-integrity cases intentionally skip re-sealing.
"""
from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tree_layout import SUITE, require_repository_root  # noqa: E402

ROOT = SUITE
REPO = require_repository_root()
GENERATED = ROOT / "examples" / "mixed-viewpoint-workshop" / "generated"
SOURCE = ROOT / "examples" / "mixed-viewpoint-workshop" / "source"

import state_protocol as S  # noqa: E402
import viewpoint_protocol as V  # noqa: E402
import build_release as R  # noqa: E402
import integration_contract as I  # noqa: E402
import validate_integration as VI  # noqa: E402


@dataclass(frozen=True)
class CaseSpec:
    number: int
    label: str
    mode: str
    runner: Callable[[], list[str]] | None = None
    delegated_to: str | None = None


def load_generated(relative: str) -> dict:
    return json.loads((GENERATED / relative).read_text(encoding="utf-8"))


def expect_rejected(
    *,
    number: int,
    label: str,
    artifact: dict,
    mutate: Callable[[dict], None],
    finalize: Callable[[dict], dict],
    validate: Callable[[dict], dict],
    expected: Iterable[str],
    reseal: bool = True,
) -> list[str]:
    value = copy.deepcopy(artifact)
    mutate(value)
    if reseal:
        value = finalize(value)
    report = validate(value)
    errors = [str(item) for item in report.get("errors", [])]
    findings: list[str] = []
    if report.get("ok"):
        findings.append(f"case {number} {label}: mutation was accepted")
        return findings
    for fragment in expected:
        if not any(fragment in error for error in errors):
            findings.append(
                f"case {number} {label}: expected error fragment {fragment!r}; got {errors!r}"
            )
    if reseal and any("does not match canonical artifact content" in error for error in errors):
        findings.append(
            f"case {number} {label}: structural mutation failed at stale hash instead of the intended rule"
        )
    return findings


def case_2() -> list[str]:
    return expect_rejected(
        number=2,
        label="external camera position",
        artifact=load_generated("shots/SC-WORKSHOP-01-SH01.json"),
        mutate=lambda value: value.pop("camera_position", None),
        finalize=V.finalize_artifact,
        validate=V.validate_artifact,
        expected=("missing required property 'camera_position'",),
    )


def case_3() -> list[str]:
    return expect_rejected(
        number=3,
        label="character-restricted focalization",
        artifact=load_generated("shots/SC-WORKSHOP-01-SH01.json"),
        mutate=lambda value: value.update(focal_character_ids=[]),
        finalize=V.finalize_artifact,
        validate=V.validate_artifact,
        expected=("character-restricted shot requires at least one focal character",),
    )


def case_7() -> list[str]:
    return expect_rejected(
        number=7,
        label="first-person camera owner",
        artifact=load_generated("shots/SC-WORKSHOP-01-SH04.json"),
        mutate=lambda value: value.pop("camera_owner_character_id", None),
        finalize=V.finalize_artifact,
        validate=V.validate_artifact,
        expected=("embodied first-person shot requires a character camera owner",),
    )


def case_8() -> list[str]:
    return expect_rejected(
        number=8,
        label="first-person detached rig",
        artifact=load_generated("shots/SC-WORKSHOP-01-SH04.json"),
        mutate=lambda value: value["movement"].update(type="orbit"),
        finalize=V.finalize_artifact,
        validate=V.validate_artifact,
        expected=("embodied first-person shot uses detached or unsupported movement: orbit",),
    )


def case_9() -> list[str]:
    def mutate(value: dict) -> None:
        value["viewpoint_profile_id"] = "held-device-first-person"
        value["profile_family"] = "device-first-person"
        value["camera_ownership"] = "external_camera"
        value["movement"]["type"] = "crane"

    return expect_rejected(
        number=9,
        label="device camera ownership and movement",
        artifact=load_generated("shots/SC-WORKSHOP-01-SH04.json"),
        mutate=mutate,
        finalize=V.finalize_artifact,
        validate=V.validate_artifact,
        expected=(
            "device first-person shot requires device ownership",
            "device shot movement type is unsupported: crane",
        ),
    )


def case_10() -> list[str]:
    def mutate(value: dict) -> None:
        value["viewpoint_profile_id"] = "fixed-diegetic-observer"
        value["profile_family"] = "fixed-diegetic"
        value["camera_ownership"] = "external_camera"
        value["movement"]["type"] = "orbit"

    return expect_rejected(
        number=10,
        label="fixed in-world camera",
        artifact=load_generated("shots/SC-WORKSHOP-01-SH01.json"),
        mutate=mutate,
        finalize=V.finalize_artifact,
        validate=V.validate_artifact,
        expected=(
            "fixed diegetic shot requires fixed camera ownership",
            "fixed diegetic shot movement type is unsupported: orbit",
        ),
    )


def case_11() -> list[str]:
    plan = load_generated("scene-viewpoint-plan.json")
    findings = expect_rejected(
        number=11,
        label="duplicate shot IDs",
        artifact=plan,
        mutate=lambda value: value["shots"][1].update(shot_id=value["shots"][0]["shot_id"]),
        finalize=V.finalize_artifact,
        validate=V.validate_artifact,
        expected=("scene viewpoint plan contains duplicate shot IDs",),
    )
    findings.extend(
        expect_rejected(
            number=11,
            label="nonconsecutive shot order",
            artifact=plan,
            mutate=lambda value: value["shots"][1].update(order_index=7),
            finalize=V.finalize_artifact,
            validate=V.validate_artifact,
            expected=("shot order indices must form a consecutive sequence starting at 1",),
        )
    )
    return findings


def case_12() -> list[str]:
    return expect_rejected(
        number=12,
        label="viewpoint transition trigger",
        artifact=load_generated("transitions/VT-WORKSHOP-03.json"),
        mutate=lambda value: value.pop("trigger", None),
        finalize=V.finalize_artifact,
        validate=V.validate_artifact,
        expected=("missing required property 'trigger'",),
    )


def case_22() -> list[str]:
    def mutate(value: dict) -> None:
        value["shot_entries"][1]["prop_ownership"]["P01"] = "C01 left hand"
        for transition in value.get("transition_entries", []):
            transition["continuity_requirements"] = [
                str(item).replace("P01", "the pendant")
                for item in transition.get("continuity_requirements", [])
            ]

    return expect_rejected(
        number=22,
        label="undeclared prop ownership change",
        artifact=load_generated("shot-continuity-ledger.json"),
        mutate=mutate,
        finalize=V.finalize_artifact,
        validate=V.validate_artifact,
        expected=("prop ownership changes without a declared transition requirement: P01",),
    )


def case_23() -> list[str]:
    events = S.load_jsonl(SOURCE / "events.jsonl")
    event = next(item for item in events if item.get("event_id") == "EV-TRANSFER-P01")
    return expect_rejected(
        number=23,
        label="non-atomic multi-entity transfer",
        artifact=event,
        mutate=lambda value: value.update(atomic=False),
        finalize=S.finalize_artifact,
        validate=S.validate_artifact,
        expected=("multi-entity state-event must set atomic=true",),
    )


def case_27() -> list[str]:
    """An available future reference file cannot settle an earlier story point."""
    template = json.loads((ROOT / "protocols/shared-state/templates/state-aware-reference-binding.template.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="reference-scope-") as temp:
        source = Path(temp) / "evidence.bin"
        source.write_bytes(b"synthetic reference bytes; no media quality claim")
        template.update(binding_id="BIND-C01-FUTURE", character_id="C01",
            identity_contract_sha256="a" * 64,
            era_contract_sha256=None, appearance_variant_sha256=None, state_snapshot_sha256=None,
            effective_story_range={"from_order":20,"to_order":None},
            visibly_supported_state=["future-state-wardrobe"], unsupported_or_occluded_state=[],
            review_dimensions=["wardrobe state"], superseded_for_future_scenes=False,
            source={"kind":"supplied-file","reference_id":"c01-future","resolved_path":str(source.resolve()),
                "media_type":"application/octet-stream","sha256":__import__("hashlib").sha256(source.read_bytes()).hexdigest()})
        selection = S.select_state_references([S.finalize_artifact(template)], selection_id="SEL-FLASHBACK",
            identity_hash="a"*64, era_hash=None, appearance_hash=None, state_hash=None,
            story_order=10, required_features=["future-state-wardrobe"], limit=1)
    findings = []
    if selection.get("selected_references"):
        findings.append("case 27 flashback assets: future-state asset was selected for an earlier story order")
    if selection.get("unresolved_requirements") != ["future-state-wardrobe"]:
        findings.append("case 27 flashback assets: excluded feature was not retained as unresolved")
    return findings


def case_33() -> list[str]:
    text = (ROOT / "examples/mixed-viewpoint-workshop/result-log.md").read_text(encoding="utf-8")
    findings: list[str] = []
    if not re.search(r"Run status:\s*not run", text, re.IGNORECASE):
        findings.append("case 33 planned versus observed result: result log does not state Run status: not run")
    if re.search(r"accepted variant|returned variant|rendered successfully", text, re.IGNORECASE):
        findings.append("case 33 planned versus observed result: not-run example claims returned output")
    return findings


def case_37() -> list[str]:
    return expect_rejected(
        number=37,
        label="state hash integrity",
        artifact=load_generated("character-state-snapshot-C01.json"),
        mutate=lambda value: value["physical_state"].update(test_tamper="changed"),
        finalize=S.finalize_artifact,
        validate=S.validate_artifact,
        expected=("state_snapshot_sha256 does not match canonical artifact content",),
        reseal=False,
    )


def case_38() -> list[str]:
    return expect_rejected(
        number=38,
        label="camera hash integrity",
        artifact=load_generated("shots/SC-WORKSHOP-01-SH01.json"),
        mutate=lambda value: value.update(camera_position=value["camera_position"] + " changed"),
        finalize=V.finalize_artifact,
        validate=V.validate_artifact,
        expected=("camera_spec_sha256 does not match canonical artifact content",),
        reseal=False,
    )


def case_40() -> list[str]:
    from release_contract import validate_changelog
    with (REPO / "package-manifest.toml").open("rb") as handle:
        version = str(tomllib.load(handle)["package"]["version"])
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    return [f"case 40: {error}" for error in validate_changelog(changelog, version, style="dated")]


def case_41() -> list[str]:
    findings: list[str] = []
    excluded = {".git", "dist", "__pycache__", ".pytest_cache"}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in excluded for part in path.parts):
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".zip", ".pyc"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "\u2014" in text or "\u2013" in text:
            findings.append(f"case 41 ASCII punctuation: {path.relative_to(ROOT)} contains a Unicode dash")
    return findings


def case_42() -> list[str]:
    process = subprocess.run(
        [sys.executable, "scripts/build_example.py", "--check"],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True, encoding='utf-8',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        return [
            "case 42 deterministic example: "
            + (process.stderr.strip() or process.stdout.strip() or "build check failed")
        ]
    return []


def case_58() -> list[str]:
    base = json.loads((SOURCE / "world-state-base.json").read_text(encoding="utf-8"))
    schema = load_generated("character-state-schema-C01.json")
    original = next(
        item for item in S.load_jsonl(SOURCE / "events.jsonl")
        if item.get("event_id") == "EV-C01-INJURY"
    )
    temporary = copy.deepcopy(original)
    temporary.update(event_id="EV-TEMP-SAME-VALUE", effective_order=1)
    temporary["changes"][0].update(persistence="temporary-until-cleared", effective_until_order=3)
    temporary["preconditions"] = []
    temporary["changes"][0].pop("clear_event_id", None)
    persistent = copy.deepcopy(temporary)
    persistent.update(event_id="EV-PERSISTENT-SAME-VALUE", effective_order=2)
    persistent["changes"][0].pop("effective_until_order", None)
    persistent["changes"][0]["persistence"] = "persistent-until-superseded"
    try:
        result = S.resolve_world(
            base_state=base,
            events=[temporary, persistent],
            processes=[],
            timeline_id="main",
            story_order=3,
            story_time="story:test-3",
            snapshot_id="WORLD-TEST-3",
            scene_context_id="SC-WORKSHOP-01",
            character_state_schemas=[schema],
        )
    except Exception as exc:
        return [f"case 58 temporary expiry ownership: resolution failed: {exc}"]
    actual = result["entities"]["characters"]["C01"]["physical_state"]["left_side_injury"]
    expected = persistent["changes"][0]["value"]
    if actual != expected:
        return ["case 58 temporary expiry ownership: expiry rolled back a later persistent writer"]
    return []


def case_59() -> list[str]:
    base = json.loads((SOURCE / "world-state-base.json").read_text(encoding="utf-8"))
    schema = load_generated("character-state-schema-C01.json")
    original = next(
        item for item in S.load_jsonl(SOURCE / "events.jsonl")
        if item.get("event_id") == "EV-C01-INJURY"
    )
    mutations = (
        (
            "undeclared path",
            lambda event: event["changes"][0].update(path="/physical_state/undeclared_topology"),
            "undeclared character state path",
        ),
        (
            "wrong value type",
            lambda event: event["changes"][0].update(value="not an object"),
            "does not match declared type object",
        ),
        (
            "disallowed persistence",
            lambda event: event["changes"][0].update(persistence="era-level"),
            "is not allowed",
        ),
    )
    findings: list[str] = []
    for label, mutate, expected in mutations:
        event = copy.deepcopy(original)
        mutate(event)
        try:
            S.resolve_world(
                base_state=base,
                events=[event],
                processes=[],
                timeline_id="main",
                story_order=10,
                story_time="story:test-10",
                snapshot_id="WORLD-TEST-10",
                scene_context_id="SC-WORKSHOP-01",
            character_state_schemas=[schema],
            )
        except ValueError as exc:
            if expected not in str(exc):
                findings.append(f"case 59 {label}: wrong error: {exc}")
        else:
            findings.append(f"case 59 {label}: invalid state event was accepted")
    return findings


def case_60() -> list[str]:
    scene = load_generated("scene-viewpoint-plan.json")
    shots = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((GENERATED / "shots").glob("*.json"))
    ]
    transitions = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((GENERATED / "transitions").glob("*.json"))
    ]
    findings: list[str] = []
    foreign = copy.deepcopy(shots)
    foreign[0]["scene_id"] = "OTHER-SCENE"
    foreign[0] = V.finalize_artifact(foreign[0])
    try:
        V.build_continuity_ledger(scene, foreign, transitions)
    except ValueError as exc:
        if "different scene" not in str(exc):
            findings.append(f"case 60 cross-scene shot: wrong error: {exc}")
    else:
        findings.append("case 60 cross-scene shot: ledger builder accepted a foreign shot")
    broken = copy.deepcopy(transitions)
    broken[0]["to_shot"] = "UNKNOWN-SHOT"
    broken[0] = V.finalize_artifact(broken[0])
    try:
        V.build_continuity_ledger(scene, shots, broken)
    except ValueError as exc:
        if "unknown shot" not in str(exc):
            findings.append(f"case 60 transition reference: wrong error: {exc}")
    else:
        findings.append("case 60 transition reference: ledger builder accepted an unknown shot")
    return findings


def case_61() -> list[str]:
    findings: list[str] = []
    request = load_generated("shot-requests/SC-WORKSHOP-01-SH01.json")
    request["identity_contract_sha256_by_character"] = None
    request = V.finalize_artifact(request)
    try:
        report = V.validate_artifact(request)
    except Exception as exc:
        findings.append(f"case 61 viewpoint type error leaked an exception: {exc}")
    else:
        if report.get("ok"):
            findings.append("case 61 viewpoint type error was accepted")
    event = next(iter(S.load_jsonl(SOURCE / "events.jsonl")))
    event["changes"] = None
    try:
        report = S.validate_artifact(event)
    except Exception as exc:
        findings.append(f"case 61 state type error leaked an exception: {exc}")
    else:
        if report.get("ok"):
            findings.append("case 61 state type error was accepted")
    return findings


def case_62() -> list[str]:
    return expect_rejected(
        number=62,
        label="per-character hash value",
        artifact=load_generated("shot-requests/SC-WORKSHOP-01-SH01.json"),
        mutate=lambda value: value["identity_contract_sha256_by_character"].update(C01="not-a-sha256"),
        finalize=V.finalize_artifact,
        validate=V.validate_artifact,
        expected=("does not match pattern",),
    )


def case_63() -> list[str]:
    payload_source = GENERATED / "shot-requests" / "SC-WORKSHOP-01-SH01.json"
    with tempfile.TemporaryDirectory(prefix="scd-case-63-") as temp:
        payload = Path(temp) / "payload.json"
        original = payload_source.read_bytes()
        payload.write_bytes(original)
        command = [
            sys.executable,
            "scripts/build_interchange_envelope.py",
            "--profile", "shot-request",
            "--payload", str(payload),
            "--payload-type", "shot-request",
            "--payload-id", "CASE-63",
            "--out", str(payload),
        ]
        process = subprocess.run(command, cwd=ROOT, text=True, encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        findings: list[str] = []
        if process.returncode == 0:
            findings.append("case 63 envelope collision: payload/output collision was accepted")
        if payload.read_bytes() != original:
            findings.append("case 63 envelope collision: original payload bytes changed")
        return findings


def case_64() -> list[str]:
    capabilities = I.load_capabilities(ROOT)
    profile = I.find_interface(capabilities, "produces", "shot-request")
    if profile is None:
        return ["case 64 undeclared payload type: the shot-request profile is missing"]
    with tempfile.TemporaryDirectory(prefix="scd-case-64-") as temp:
        payload = Path(temp) / "payload.json"
        payload.write_text("{}\n", encoding="utf-8", newline="\n")
        envelope = I.finalize({
            "artifact_type": "interchange-envelope",
            "envelope_id": "IE-CASE-64",
            "contract_profile": profile["profile"],
            "profile_sha256": profile["profile_sha256"],
            "origin": {
                "capability_manifest_sha256": capabilities["manifest_sha256"],
            },
            "payload": {
                "artifact_type": "undeclared-payload-type",
                "artifact_id": "CASE-64",
                "media_type": "application/json",
                "path": payload.name,
                "sha256": __import__("hashlib").sha256(payload.read_bytes()).hexdigest(),
            },
            "required_features": list(profile["required_features"]),
            "optional_features": [],
            "extensions": {},
            "envelope_sha256": "0" * 64,
        }, "envelope_sha256")
        report = I.validate_envelope(envelope, capabilities=capabilities, direction="produces", payload_root=Path(temp))
    if report.get("ok") or not any("not declared" in str(item) for item in report.get("errors", [])):
        return [f"case 64 undeclared payload type: wrong report: {report}"]
    return []


def case_65() -> list[str]:
    with tempfile.TemporaryDirectory(prefix="scd-case-65-") as temp:
        project = Path(temp) / "project"
        init = subprocess.run(
            [sys.executable, "scripts/init_project.py", "--out", str(project), "--series-id", "CASE-65", "--title", "Case 65"],
            cwd=ROOT, text=True, encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if init.returncode != 0:
            return [f"case 65 project setup failed: {init.stderr or init.stdout}"]
        manifest_path = project / "project-manifest.json"
        original = json.loads(manifest_path.read_text(encoding="utf-8"))
        incomplete = copy.deepcopy(original)
        incomplete.pop("title")
        manifest_path.write_text(json.dumps(incomplete, indent=2) + "\n", encoding="utf-8", newline="\n")
        first = subprocess.run(
            [sys.executable, "scripts/validate_project.py", str(project)],
            cwd=ROOT, text=True, encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        manifest_path.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8", newline="\n")
        type_less = project / "state" / "snapshots" / "type-less.json"
        type_less.write_text("{}\n", encoding="utf-8", newline="\n")
        second = subprocess.run(
            [sys.executable, "scripts/validate_project.py", str(project)],
            cwd=ROOT, text=True, encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
    findings: list[str] = []
    if first.returncode == 0 or "project manifest missing fields" not in first.stdout:
        findings.append("case 65 project manifest: incomplete manifest was not rejected correctly")
    if second.returncode == 0 or "requires artifact_type" not in second.stdout:
        findings.append("case 65 project artifacts: managed type-less JSON was not rejected correctly")
    return findings


def case_66() -> list[str]:
    if not (ROOT / ".git").exists():
        # Staged and extracted releases intentionally have no Git metadata.
        # Source-tree validation exercises this case before packaging.
        return []
    fixture = ROOT / "scripts" / "scd-untracked-release-case.txt"
    if fixture.exists():
        return [f"case 66 release membership fixture already exists: {fixture}"]
    try:
        fixture.write_text("must not ship\n", encoding="utf-8", newline="\n")
        with tempfile.TemporaryDirectory(prefix="scd-case-66-") as temp:
            stage = Path(temp) / "stage"
            membership = R.copy_release_tree(ROOT, stage, R.load_manifest(ROOT))
            findings: list[str] = []
            if (stage / "scripts" / fixture.name).exists():
                findings.append("case 66 release membership: untracked file was copied")
            if f"scripts/{fixture.name}" not in membership.get("excluded_local_files", []):
                findings.append("case 66 release membership: excluded file was not reported")
            return findings
    finally:
        fixture.unlink(missing_ok=True)


def case_67() -> list[str]:
    with (REPO / "package-manifest.toml").open("rb") as handle:
        version = str(tomllib.load(handle)["package"]["version"])
    capabilities = I.load_capabilities(ROOT)
    findings: list[str] = []
    for relative in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        value = json.loads((REPO / relative).read_text(encoding="utf-8"))
        if value.get("version") != version:
            findings.append(f"case 67 version alignment: {relative} differs")
    return findings


def case_68() -> list[str]:
    report = VI.self_test(I.load_capabilities(ROOT))
    if not report.get("ok"):
        return [f"case 68 real integration branches: {report.get('errors', [])}"]
    return []


def case_69() -> list[str]:
    wrong_identity = GENERATED / "shots" / "SC-WORKSHOP-01-SH01.json"
    with tempfile.TemporaryDirectory(prefix="scd-case-69-") as temp:
        bindings = Path(temp) / "bindings.json"
        output = Path(temp) / "selection.json"
        bindings.write_text("[]\n", encoding="utf-8", newline="\n")
        process = subprocess.run(
            [
                sys.executable, "scripts/select_state_references.py",
                "--bindings", str(bindings),
                "--selection-id", "CASE-69",
                "--identity-contract", str(wrong_identity),
                "--story-order", "1",
                "--out", str(output),
            ],
            cwd=ROOT, text=True, encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
    if process.returncode == 0 or "expected artifact_type" not in process.stdout:
        return [f"case 69 CLI artifact type: wrong result: {process.stdout or process.stderr}"]
    return []


def case_70() -> list[str]:
    # Workflow sources are repository controls, not release members, so they sit
    # above this suite rather than inside it. An extracted release has neither.
    workflow_path = next(
        (candidate / ".github" / "workflows" / "release.yml"
         for candidate in (ROOT, *ROOT.parents)
         if (candidate / ".github" / "workflows" / "release.yml").is_file()),
        None,
    )
    if workflow_path is None:
        return []
    workflow = workflow_path.read_text(encoding="utf-8")
    findings: list[str] = []
    if "os: [ubuntu-latest, windows-latest]" not in workflow:
        findings.append("case 70 release gate: release workflow lacks the cross-OS matrix")
    if not re.search(r"(?ms)^  publish:\s+needs: package-consistency\s*$", workflow):
        findings.append("case 70 release gate: publish does not require package consistency")
    return findings


DIRECT_CASES = (
    CaseSpec(2, "External camera position", "direct", case_2),
    CaseSpec(3, "Character-restricted focalization", "direct", case_3),
    CaseSpec(7, "First-person camera owner", "direct", case_7),
    CaseSpec(8, "First-person detached rig", "direct", case_8),
    CaseSpec(9, "Device camera optics", "direct", case_9),
    CaseSpec(10, "Fixed in-world camera", "direct", case_10),
    CaseSpec(11, "Scene shot order", "direct", case_11),
    CaseSpec(12, "Viewpoint transition trigger", "direct", case_12),
    CaseSpec(22, "Prop ownership", "direct", case_22),
    CaseSpec(23, "Atomic transfer", "direct", case_23),
    CaseSpec(27, "Flashback assets", "direct", case_27),
    CaseSpec(33, "Planned versus observed result", "direct", case_33),
    CaseSpec(37, "State hash integrity", "direct", case_37),
    CaseSpec(38, "Camera hash integrity", "direct", case_38),
    CaseSpec(40, "Dated product release history", "direct", case_40),
    CaseSpec(41, "ASCII punctuation", "direct", case_41),
    CaseSpec(58, "Temporary expiry ownership", "direct", case_58),
    CaseSpec(59, "Character state schema enforcement", "direct", case_59),
    CaseSpec(60, "Scene-consistent continuity ledger", "direct", case_60),
    CaseSpec(61, "Structured type errors", "direct", case_61),
    CaseSpec(62, "Per-character hash values", "direct", case_62),
    CaseSpec(63, "Interchange path collision", "direct", case_63),
    CaseSpec(64, "Declared payload artifact type", "direct", case_64),
    CaseSpec(65, "Project artifact boundary", "direct", case_65),
    CaseSpec(66, "Tracked release membership", "direct", case_66),
    CaseSpec(67, "Release version alignment", "direct", case_67),
    CaseSpec(68, "Real integration branches", "direct", case_68),
    CaseSpec(69, "CLI artifact type validation", "direct", case_69),
    CaseSpec(70, "Cross-OS release publication gate", "direct", case_70),
)

DELEGATED_CASES = (
    CaseSpec(42, "Deterministic example", "delegated", delegated_to="scripts/validate_skill.py"),
    CaseSpec(39, "Canonical package identity", "delegated", delegated_to="scripts/validate_skill.py"),
    CaseSpec(43, "Canonical reference structure", "delegated", delegated_to="scripts/validate_skill.py"),
    CaseSpec(44, "Canonical project state layout", "delegated", delegated_to="scripts/validate_skill.py"),
    CaseSpec(45, "Project-template documentation conformance", "delegated", delegated_to="scripts/validate_skill.py"),
    CaseSpec(46, "Installed-suite immutability and redaction", "delegated", delegated_to="scripts/validate_knowledge_integrity.py"),
    CaseSpec(47, "Video and audio asset records", "delegated", delegated_to="scripts/validate_knowledge_integrity.py"),
    CaseSpec(48, "First-person technique library", "delegated", delegated_to="scripts/validate_knowledge_integrity.py"),
    CaseSpec(49, "Scoped lexicon and negative syntax", "delegated", delegated_to="scripts/validate_knowledge_integrity.py"),
    CaseSpec(50, "Dialogue quality and template fatigue", "delegated", delegated_to="scripts/validate_knowledge_integrity.py"),
    CaseSpec(51, "Segment roles, narration, and spare time", "delegated", delegated_to="scripts/validate_knowledge_integrity.py"),
    CaseSpec(52, "Operational distinction examples", "delegated", delegated_to="scripts/validate_knowledge_integrity.py"),
    CaseSpec(53, "Generated-transition record and beat continuity", "delegated", delegated_to="scripts/validate_knowledge_integrity.py"),
    CaseSpec(54, "Canonical production templates and full checklist", "delegated", delegated_to="scripts/validate_knowledge_integrity.py"),
    CaseSpec(55, "Consolidated post-production structure", "delegated", delegated_to="scripts/validate_knowledge_integrity.py"),
    CaseSpec(56, "Capability-based verification and human authority", "delegated", delegated_to="scripts/validate_knowledge_integrity.py"),
    CaseSpec(57, "Persistent and nonpersistent state handling", "delegated", delegated_to="scripts/validate_knowledge_integrity.py"),
    CaseSpec(71, "Narrative contract", "delegated", delegated_to="scripts/narrative_smoke_test.py"),
    CaseSpec(72, "Story time anchoring", "delegated", delegated_to="scripts/narrative_smoke_test.py"),
    CaseSpec(73, "Persona phases and character span", "delegated", delegated_to="scripts/narrative_smoke_test.py"),
    CaseSpec(74, "Scene plot contract", "delegated", delegated_to="scripts/scene_plot_smoke_test.py"),
    CaseSpec(75, "Declared structure profile", "delegated", delegated_to="scripts/scene_plot_smoke_test.py"),
    CaseSpec(76, "Realization per medium", "delegated", delegated_to="scripts/narrative_smoke_test.py"),
    CaseSpec(77, "Narrative coverage", "delegated", delegated_to="scripts/narrative_smoke_test.py"),
    CaseSpec(78, "Approval chain across a change", "delegated", delegated_to="scripts/submission_gate_smoke_test.py"),
    CaseSpec(79, "Narrative entity references", "delegated", delegated_to="scripts/narrative_index_smoke_test.py"),
    CaseSpec(80, "Character prohibitions in model-facing text", "delegated", delegated_to="scripts/submission_gate_smoke_test.py"),
)

# These require narrative or visual judgment and are intentionally not automated.
EDITORIAL_CASE_NUMBERS = frozenset(
    {
        1, 4, 5, 6, 13, 14, 15, 16, 17, 18, 19, 20, 21,
        24, 25, 26, 28, 29, 30, 31, 32, 34, 35, 36,
    }
)
CASES = (*DIRECT_CASES, *DELEGATED_CASES)
# How many numbered cases the catalog carries. Declared once, so a case added
# to the catalog and to no disposition is an error rather than a silent gap.
CATALOG_CASES = 80
EXECUTED_CASE_NUMBERS = frozenset(case.number for case in CASES)


def markdown_dispositions() -> tuple[dict[int, str], list[str]]:
    text = (ROOT / "examples/test-cases.md").read_text(encoding="utf-8")
    headings = list(re.finditer(r"(?m)^##\s+(\d+)\.\s+.+$", text))
    dispositions: dict[int, str] = {}
    errors: list[str] = []
    for index, match in enumerate(headings):
        number = int(match.group(1))
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[match.end():end]
        markers = re.findall(r"(?m)^Enforcement:\s*(executed|editorial review)\s*$", body)
        if len(markers) != 1:
            errors.append(f"case {number}: expected exactly one Enforcement marker, found {markers!r}")
            continue
        dispositions[number] = markers[0]
    return dispositions, errors


def main() -> int:
    errors: list[str] = []
    results: list[dict[str, object]] = []

    dispositions, marker_errors = markdown_dispositions()
    errors.extend(marker_errors)
    # The catalog decides how many cases there are, and this decides that every
    # one of them carries a disposition. A number written here instead would be
    # a second count to keep in step with the first.
    expected_numbers = set(range(1, CATALOG_CASES + 1))
    if set(dispositions) != expected_numbers:
        errors.append(
            f"test-case disposition markers must cover cases 1 through {CATALOG_CASES} "
            "exactly; "
            f"missing={sorted(expected_numbers - set(dispositions))} extra={sorted(set(dispositions) - expected_numbers)}"
        )
    declared_executed = {number for number, mode in dispositions.items() if mode == "executed"}
    declared_editorial = {number for number, mode in dispositions.items() if mode == "editorial review"}
    if declared_executed != set(EXECUTED_CASE_NUMBERS):
        errors.append(
            "executed case markers differ from runner/delegation map; "
            f"missing={sorted(set(EXECUTED_CASE_NUMBERS) - declared_executed)} "
            f"extra={sorted(declared_executed - set(EXECUTED_CASE_NUMBERS))}"
        )
    if declared_editorial != set(EDITORIAL_CASE_NUMBERS):
        errors.append(
            "editorial case markers differ from the explicit review set; "
            f"missing={sorted(set(EDITORIAL_CASE_NUMBERS) - declared_editorial)} "
            f"extra={sorted(declared_editorial - set(EDITORIAL_CASE_NUMBERS))}"
        )
    if set(EXECUTED_CASE_NUMBERS) & set(EDITORIAL_CASE_NUMBERS):
        errors.append("case classification overlap between executed and editorial sets")
    if set(EXECUTED_CASE_NUMBERS) | set(EDITORIAL_CASE_NUMBERS) != expected_numbers:
        errors.append(f"case classification does not cover cases 1 through {CATALOG_CASES}")

    for case in DIRECT_CASES:
        case_errors = case.runner() if case.runner else [f"case {case.number}: missing runner"]
        results.append(
            {
                "number": case.number,
                "label": case.label,
                "mode": case.mode,
                "ok": not case_errors,
                "errors": case_errors,
            }
        )
        errors.extend(case_errors)

    for case in DELEGATED_CASES:
        results.append(
            {
                "number": case.number,
                "label": case.label,
                "mode": case.mode,
                "delegated_to": case.delegated_to,
                "ok": True,
                "errors": [],
            }
        )

    report = {
        "ok": not errors,
        "errors": errors,
        "stats": {
            "catalog_cases": CATALOG_CASES,
            "direct_executed": len(DIRECT_CASES),
            "delegated_executed": len(DELEGATED_CASES),
            "editorial_review": len(EDITORIAL_CASE_NUMBERS),
            "classified": len(EXECUTED_CASE_NUMBERS | EDITORIAL_CASE_NUMBERS),
        },
        "results": results,
        "editorial_case_numbers": sorted(EDITORIAL_CASE_NUMBERS),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
