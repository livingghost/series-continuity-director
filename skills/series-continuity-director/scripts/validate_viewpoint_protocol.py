#!/usr/bin/env python3
"""Validate Series Viewpoint Protocol and its canonical example."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "protocols" / "viewpoint"
SCHEMAS = PROTOCOL / "schemas"
TEMPLATES = PROTOCOL / "templates"
PROFILES = PROTOCOL / "profiles"
EXAMPLE = ROOT / "examples" / "mixed-viewpoint-workshop"
GENERATED = EXAMPLE / "generated"

sys.path.insert(0, str(ROOT / "scripts"))
from viewpoint_protocol import finalize_artifact, load_json, validate_artifact  # noqa: E402


def main() -> int:
    errors: list[str] = []
    manifest = load_json(PROTOCOL / "protocol-manifest.json")
    from protocol_exchange import check_installed
    try:
        check_installed()
    except (ValueError, OSError) as exc:
        errors.append(str(exc))

    artifact_types = manifest.get("artifact_types", [])
    expected_schemas = {f"{name}.schema.json" for name in artifact_types}
    actual_schemas = {path.name for path in SCHEMAS.glob("*.schema.json")}
    if expected_schemas != actual_schemas:
        errors.append(f"viewpoint schema set differs: missing={sorted(expected_schemas-actual_schemas)} extra={sorted(actual_schemas-expected_schemas)}")

    profile_files = manifest.get("profile_files", [])
    actual_profile_files = {f"profiles/{path.name}" for path in PROFILES.glob("*.json")}
    if set(profile_files) != actual_profile_files:
        errors.append("viewpoint profile file set differs from manifest")

    families = set()
    profile_count = 0
    for path in sorted(PROFILES.glob("*.json")):
        profile_count += 1
        value = load_json(path)
        families.add(value.get("profile_family"))
        report = validate_artifact(value)
        if not report.get("ok"):
            errors.extend(f"{path.relative_to(ROOT)}: {message}" for message in report.get("errors", []))
    required_families = {"external", "embodied-first-person", "device-first-person", "fixed-diegetic"}
    if not required_families.issubset(families):
        errors.append(f"viewpoint profile families missing: {sorted(required_families-families)}")

    template_count = 0
    for path in sorted(TEMPLATES.glob("*.json")):
        template_count += 1
        value = load_json(path)
        report = validate_artifact(value, allow_placeholder_hashes=True)
        if not report.get("ok"):
            errors.extend(f"{path.relative_to(ROOT)}: {message}" for message in report.get("errors", []))

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
        errors.append("canonical example build check failed: " + (process.stderr.strip() or process.stdout.strip()))

    viewpoint_artifacts = 0
    profiles_used = set()
    for path in sorted(GENERATED.rglob("*.json")):
        try:
            value = load_json(path)
        except Exception:
            continue
        if not value.get("artifact_type") or not (SCHEMAS / f"{value['artifact_type']}.schema.json").is_file():
            continue
        viewpoint_artifacts += 1
        if value.get("artifact_type") == "shot-camera-spec":
            profiles_used.add(value.get("viewpoint_profile_id"))
        report = validate_artifact(value)
        if not report.get("ok"):
            errors.extend(f"{path.relative_to(ROOT)}: {message}" for message in report.get("errors", []))

    for required in {"external-character-aligned-third-person", "over-the-shoulder", "embodied-first-person"}:
        if required not in profiles_used:
            errors.append(f"canonical example does not use required profile: {required}")

    ledger = load_json(GENERATED / "shot-continuity-ledger.json")
    if ledger.get("unresolved_continuity"):
        errors.append(f"canonical example has unresolved continuity: {ledger['unresolved_continuity']}")
    if len(ledger.get("shot_entries", [])) != 6 or len(ledger.get("transition_entries", [])) != 5:
        errors.append("canonical example must contain six shots and five transitions")

    plan = load_json(GENERATED / "scene-viewpoint-plan.json")
    if plan.get("default_viewpoint_profile_id") != "external-character-aligned-third-person":
        errors.append("canonical scene does not use the required third-person default")

    # Negative cases. Re-seal structural mutations before validation so the
    # expected rule, not a stale artifact hash, is what rejects the case.
    def require_error(report: dict, expected: str, label: str) -> None:
        messages = [str(item) for item in report.get("errors", [])]
        if report.get("ok"):
            errors.append(f"{label} was accepted")
        elif not any(expected in message for message in messages):
            errors.append(f"{label} failed for the wrong reason: {messages}")
        elif any("does not match canonical artifact content" in message for message in messages):
            errors.append(f"{label} was short-circuited by a stale artifact hash: {messages}")

    first_person = load_json(GENERATED / "shots" / "SC-WORKSHOP-01-SH04.json")
    bad_move = json.loads(json.dumps(first_person))
    bad_move["movement"]["type"] = "orbit"
    bad_move = finalize_artifact(bad_move)
    require_error(
        validate_artifact(bad_move),
        "embodied first-person shot uses detached or unsupported movement: orbit",
        "embodied first-person detached orbit mutation",
    )

    external = load_json(GENERATED / "shots" / "SC-WORKSHOP-01-SH01.json")
    bad_external = json.loads(json.dumps(external))
    bad_external.pop("camera_position", None)
    bad_external = finalize_artifact(bad_external)
    require_error(
        validate_artifact(bad_external),
        "missing required property 'camera_position'",
        "external shot missing camera position mutation",
    )

    transition = load_json(GENERATED / "transitions" / "VT-WORKSHOP-03.json")
    bad_transition = json.loads(json.dumps(transition))
    bad_transition.pop("trigger", None)
    bad_transition = finalize_artifact(bad_transition)
    require_error(
        validate_artifact(bad_transition),
        "missing required property 'trigger'",
        "viewpoint transition missing trigger mutation",
    )

    report = {
        "ok": not errors,
        "protocol": "viewpoint",
        "stats": {
            "schemas": len(actual_schemas),
            "templates": template_count,
            "profiles": profile_count,
            "generated_viewpoint_artifacts": viewpoint_artifacts,
            "profiles_used_in_example": sorted(profiles_used),
            "shots": len(ledger.get("shot_entries", [])),
            "transitions": len(ledger.get("transition_entries", [])),
        },
        "errors": errors,
        "generated_media_quality": "not evaluated",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
