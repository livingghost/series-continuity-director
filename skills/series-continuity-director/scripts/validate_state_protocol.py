#!/usr/bin/env python3
"""Validate Shared State Protocol and the canonical example."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "protocols" / "shared-state"
SCHEMAS = PROTOCOL / "schemas"
TEMPLATES = PROTOCOL / "templates"
EXAMPLE = ROOT / "examples" / "mixed-viewpoint-workshop"
GENERATED = EXAMPLE / "generated"

sys.path.insert(0, str(ROOT / "scripts"))
from state_protocol import artifact_hash, load_json, load_jsonl, validate_artifact  # noqa: E402


def walk_refs(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref" and isinstance(child, str):
                yield child
            else:
                yield from walk_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_refs(child)


def main() -> int:
    errors: list[str] = []
    stats: dict[str, Any] = {}

    try:
        manifest = load_json(PROTOCOL / "protocol-manifest.json")
    except Exception as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 1
    from protocol_exchange import check_installed
    try:
        check_installed()
    except (ValueError, OSError) as exc:
        errors.append(str(exc))

    artifact_types = manifest.get("artifact_types", [])
    supporting = manifest.get("supporting_schemas", [])
    expected = {f"{name}.schema.json" for name in artifact_types} | set(supporting)
    actual = {path.name for path in SCHEMAS.glob("*.schema.json")}
    if expected != actual:
        errors.append(f"shared state schema set differs: missing={sorted(expected-actual)} extra={sorted(actual-expected)}")

    for path in sorted(SCHEMAS.glob("*.schema.json")):
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
            continue
        from protocol_contract import _resolve_ref
        for ref in walk_refs(schema):
            try:
                _resolve_ref(ref, schema)
            except (ValueError, OSError) as exc:
                errors.append(f"{path.relative_to(ROOT)}: {exc}")

    template_count = 0
    validated_templates = 0
    for path in sorted(TEMPLATES.glob("*.json")):
        template_count += 1
        try:
            value = load_json(path)
        except Exception as exc:
            errors.append(f"{path.relative_to(ROOT)}: invalid template: {exc}")
            continue
        if value.get("artifact_type"):
            validated_templates += 1
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

    state_artifacts = 0
    for path in sorted(GENERATED.rglob("*.json")):
        try:
            value = load_json(path)
        except Exception:
            continue
        kind = value.get("artifact_type")
        if not kind or not (SCHEMAS / f"{kind}.schema.json").is_file():
            continue
        state_artifacts += 1
        report = validate_artifact(value)
        if not report.get("ok"):
            errors.extend(f"{path.relative_to(ROOT)}: {message}" for message in report.get("errors", []))

    events = load_jsonl(EXAMPLE / "source" / "events.jsonl")
    if not any(event.get("canon_status") == "approved" for event in events):
        errors.append("canonical example must contain an approved state event")
    if not any(event.get("canon_status") == "proposed" for event in events):
        errors.append("canonical example must preserve a proposed non-canon event")

    index = load_json(GENERATED / "example-index.json")
    if index.get("run_status") != "not run":
        errors.append("canonical example must remain not run")

    # Negative cases: tampered hash and non-atomic multi-entity event must fail.
    snapshot = load_json(GENERATED / "character-state-snapshot-C01.json")
    tampered = json.loads(json.dumps(snapshot))
    tampered["physical_state"]["left_side_injury"]["status"] = "tampered"
    tampered_report = validate_artifact(tampered)
    tampered_errors = [str(item) for item in tampered_report.get("errors", [])]
    if tampered_report.get("ok"):
        errors.append("tampered state snapshot was not rejected")
    elif not any("state_snapshot_sha256 does not match canonical artifact content" in item for item in tampered_errors):
        errors.append(f"tampered state snapshot failed for the wrong reason: {tampered_errors}")

    proposed = next(event for event in events if event.get("event_id") == "EV-TRANSFER-P01")
    invalid_event = json.loads(json.dumps(proposed))
    invalid_event["atomic"] = False
    invalid_report = validate_artifact(invalid_event)
    invalid_errors = [str(item) for item in invalid_report.get("errors", [])]
    if invalid_report.get("ok"):
        errors.append("non-atomic multi-entity transfer was not rejected")
    elif not any("multi-entity state-event must set atomic=true" in item for item in invalid_errors):
        errors.append(f"non-atomic multi-entity transfer failed for the wrong reason: {invalid_errors}")

    stats.update({
        "schemas": len(actual),
        "templates": template_count,
        "validated_templates": validated_templates,
        "generated_state_artifacts": state_artifacts,
        "events": len(events),
    })
    report = {"ok": not errors, "protocol": "shared-state", "stats": stats, "errors": errors, "generated_media_quality": "not evaluated"}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
