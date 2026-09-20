"""Load, seal, and validate target profiles: durable per-model surface facts."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from integration_contract import canonical_json
from schema_engine import validate_against_schema as _validate_against_schema

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_DIR = ROOT / "protocols" / "target"
SCHEMA_DIR = PROTOCOL_DIR / "schemas"
PROFILE_DIR = PROTOCOL_DIR / "profiles"
MANIFEST = PROTOCOL_DIR / "protocol-manifest.json"

SELF_HASH_FIELD = "profile_sha256"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def artifact_hash(data: dict[str, Any]) -> str:
    value = copy.deepcopy(data)
    value.pop(SELF_HASH_FIELD, None)
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def finalize_profile(data: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(data)
    value[SELF_HASH_FIELD] = artifact_hash(value)
    return value


def schema() -> dict[str, Any]:
    return read_json(SCHEMA_DIR / "target-profile.schema.json")


def _resolve_ref(ref: str) -> dict[str, Any]:
    if ref.startswith("http://") or ref.startswith("https://"):
        raise ValueError(f"HTTP(S) schema references are not retrieved: {ref}")
    path = (SCHEMA_DIR / ref).resolve()
    if SCHEMA_DIR.resolve() not in path.parents and path != SCHEMA_DIR.resolve():
        raise ValueError(f"schema reference escapes schema directory: {ref}")
    return read_json(path)


def validate_profile(data: dict[str, Any]) -> dict[str, Any]:
    errors = list(_validate_against_schema(data, schema(), resolve_ref=_resolve_ref, canonical_json=canonical_json))
    if data.get("artifact_type") != "target-profile":
        errors.append("artifact_type must be target-profile")
    stored = str(data.get(SELF_HASH_FIELD) or "")
    if stored and stored != artifact_hash(data):
        errors.append(f"{SELF_HASH_FIELD} does not match canonical profile content")

    camera = data.get("camera_control") or {}
    if camera.get("mode") in {"named-commands", "named-commands-preferred"} and not camera.get("commands"):
        errors.append("a named-command camera mode requires the command vocabulary")

    multi = data.get("multi_shot_control") or {}
    if multi.get("supported") and not multi.get("syntax"):
        errors.append("multi-shot support requires the syntax that expresses it")

    return {"ok": not errors, "errors": errors}


def load_profiles() -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    if not PROFILE_DIR.is_dir():
        return profiles
    for path in sorted(PROFILE_DIR.glob("*.json")):
        data = read_json(path)
        profiles[str(data.get("target_id"))] = data
    return profiles


def profile_for(model_identifier: str) -> dict[str, Any] | None:
    for data in load_profiles().values():
        if data.get("model_identifier") == model_identifier:
            return data
    return None


def validate_catalog() -> dict[str, Any]:
    errors: list[str] = []
    manifest = read_json(MANIFEST)
    listed = set(manifest.get("profile_files") or [])
    found = {f"profiles/{path.name}" for path in PROFILE_DIR.glob("*.json")}
    for missing in sorted(listed - found):
        errors.append(f"manifest lists a profile that is not present: {missing}")
    for unlisted in sorted(found - listed):
        errors.append(f"profile present but not listed in the manifest: {unlisted}")

    seen_ids: set[str] = set()
    seen_models: set[str] = set()
    for path in sorted(PROFILE_DIR.glob("*.json")):
        data = read_json(path)
        report = validate_profile(data)
        for message in report["errors"]:
            errors.append(f"{path.name}: {message}")
        target_id = str(data.get("target_id") or "")
        model = str(data.get("model_identifier") or "")
        if target_id in seen_ids:
            errors.append(f"{path.name}: duplicate target_id {target_id}")
        if model in seen_models:
            errors.append(f"{path.name}: duplicate model_identifier {model}")
        seen_ids.add(target_id)
        seen_models.add(model)

    return {"ok": not errors, "profiles": len(seen_ids), "errors": errors}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Series Target Protocol support tool")
    sub = parser.add_subparsers(dest="command")

    p_validate = sub.add_parser("validate", help="Validate one target profile")
    p_validate.add_argument("path")

    p_seal = sub.add_parser("seal", help="Reseal one target profile with its canonical hash")
    p_seal.add_argument("path")
    p_seal.add_argument("--out")

    sub.add_parser("validate-catalog", help="Validate every profile the manifest lists")

    args = parser.parse_args(argv)
    if args.command == "validate":
        report = validate_profile(read_json(Path(args.path)))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 1
    if args.command == "seal":
        value = finalize_profile(read_json(Path(args.path)))
        target = Path(args.out) if args.out else Path(args.path)
        write_json(target, value)
        report = validate_profile(value)
        print(json.dumps(
            {
                "ok": report["ok"],
                "path": str(target),
                "profile_sha256": value[SELF_HASH_FIELD],
                "errors": report["errors"],
            },
            ensure_ascii=False,
            indent=2,
        ))
        return 0 if report["ok"] else 1
    report = validate_catalog()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
