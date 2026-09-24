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

    errors.extend(mode_errors(data))
    return {"ok": not errors, "errors": errors}


def mode_errors(data: dict[str, Any]) -> list[str]:
    """Modes are named once, at the model, and every offering and exclusion uses those names."""

    errors: list[str] = []
    modes = [mode.get("mode") for mode in data.get("input_modes") or [] if isinstance(mode, dict)]
    if len(modes) != len(set(modes)):
        errors.append("an input mode is named twice")
    for mode in data.get("input_modes") or []:
        if not isinstance(mode, dict):
            continue
        for excluded in mode.get("excludes") or []:
            if excluded not in modes:
                errors.append(f"input mode {mode.get('mode')!r} excludes {excluded!r}, which is not an input mode")
    services: list[str] = []
    for offering in data.get("offerings") or []:
        if not isinstance(offering, dict):
            continue
        service = offering.get("service")
        if service in services:
            errors.append(f"two offerings name the service {service!r}")
        services.append(service)
        keys = offering.get("request_keys") or {}
        for mode in keys:
            if mode not in modes:
                errors.append(f"the offering on {service!r} maps {mode!r}, which is not an input mode")
        declared = {key for values in keys.values() if isinstance(values, list) for key in values}
        shape = offering.get("request_shape") or {}
        for key in shape.get("single_value_keys") or []:
            if key not in declared:
                errors.append(f"the offering on {service!r} names single-value key {key!r}, which no mode maps")
    return errors


def load_profiles() -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    if not PROFILE_DIR.is_dir():
        return profiles
    for path in sorted(PROFILE_DIR.glob("*.json")):
        data = read_json(path)
        profiles[str(data.get("target_id"))] = data
    return profiles


def validate_catalog() -> dict[str, Any]:
    errors: list[str] = []
    manifest = read_json(MANIFEST)
    listed = set(manifest.get("profile_files") or [])
    found = {f"profiles/{path.name}" for path in PROFILE_DIR.glob("*.json")}
    for missing in sorted(listed - found):
        errors.append(f"manifest lists a profile that is not present: {missing}")
    for unlisted in sorted(found - listed):
        errors.append(f"profile present but not listed in the manifest: {unlisted}")

    # A target is unique by its id. A service's identifier for a model is unique
    # within that service, and two services may use the same identifier.
    seen_ids: set[str] = set()
    seen_models: set[tuple[str, str]] = set()
    for path in sorted(PROFILE_DIR.glob("*.json")):
        data = read_json(path)
        report = validate_profile(data)
        for message in report["errors"]:
            errors.append(f"{path.name}: {message}")
        target_id = str(data.get("target_id") or "")
        if target_id in seen_ids:
            errors.append(f"{path.name}: duplicate target_id {target_id}")
        seen_ids.add(target_id)
        for offering in data.get("offerings") or []:
            pair = (str(offering.get("service") or ""), str(offering.get("model_identifier") or ""))
            if pair in seen_models:
                errors.append(f"{path.name}: service {pair[0]} already names model {pair[1]} in another profile")
            seen_models.add(pair)

    return {"ok": not errors, "profiles": len(seen_ids), "errors": errors}


def profile_directories(profiles) -> list[Path]:
    paths = [profiles] if isinstance(profiles, (str, Path)) else list(profiles)
    return list(dict.fromkeys(Path(path).absolute() for path in paths))


def resolve_profile(target: str, profiles) -> tuple[Path, dict] | None:
    """Resolve ordered sources; duplicate target IDs in one source are ambiguous."""
    for directory in profile_directories(profiles):
        matches = []
        for path in sorted(directory.glob('*.json')):
            value = read_json(path)
            if isinstance(value, dict) and value.get('target_id') == target:
                if path.is_symlink():
                    raise ValueError('target definition must be a regular file')
                matches.append((path, value))
        if len(matches) > 1:
            raise ValueError('ambiguous target ID in one profile source: ' + target)
        if matches:
            return matches[0]
    return None


def selected_profile(spec: dict, profiles, root: Path | None) -> tuple[Path, dict] | None:
    """A completed submission uses its pinned choice, not another catalog search."""
    if isinstance(spec.get('execution_choices'), dict):
        import execution_contract as c
        import runtime_evidence
        value = spec['execution_choices']
        if spec.get('execution_choices_sha256') != c.content_id(value):
            raise ValueError('selected execution choices changed')
        reader = runtime_evidence.reader(root, snapshots=copy.deepcopy(spec['input_snapshots']))
        ref = value['selection']['profile']
        profile = reader.json(ref)
        if profile.get('target_id') != spec.get('target'):
            raise ValueError('pinned target definition names another target')
        return reader.resolve(ref['path']), profile
    return resolve_profile(str(spec.get('target') or ''), profiles)


def describe(target: str, profiles, *, service=None, operation=None, context=None, guidance_paths=None) -> dict:
    import execution_contract as c
    import target_guidance
    found = resolve_profile(target, profiles)
    if found is None:
        raise ValueError('target profile is absent: ' + target)
    path, profile = found
    result = validate_profile(profile)
    if not result['ok']:
        raise ValueError('target definition: ' + '; '.join(result['errors']))
    source = {'path': str(path), 'sha256': c.digest(c.read(path))}
    documents = target_guidance.resources(guidance_paths)
    report = {'definition': source, 'search_order': [str(p) for p in profile_directories(profiles)],
              'profile': profile, 'guidance_status': 'context-required', 'guidance': []}
    if service is None or operation is None or context is None:
        report['guidance'] = [{'source': ref, 'guidance': g} for ref, doc in documents
                              for g in target_guidance.records(doc) if g['applies_to']['target_id'] == target]
        report['next'] = 'Select service, operation and use context to resolve applicability.'
        return report
    offerings = [x for x in profile.get('offerings', []) if x.get('service') == service]
    if len(offerings) != 1:
        raise ValueError('select one offering for the requested service')
    return {**report, **target_guidance.display(profile,
            {'service': service, 'model_identifier': offerings[0]['model_identifier'], 'operation': operation},
            context, documents, source=source)}


def add_selection_arguments(parser, *, target_required=False):
    parser.add_argument('--target', required=target_required, help='Explicit target profile ID for advice display.')
    parser.add_argument('--profiles', type=Path, action='append', default=[], help='Profile directory, in priority order; repeatable.')
    parser.add_argument('--guidance', type=Path, action='append', default=[], help='Explicit target-guidance data file; repeatable.')
    parser.add_argument('--service', help='Exact offering service.')
    parser.add_argument('--operation', help='Exact service operation.')
    parser.add_argument('--output-kind', help='Output kind for recommendation applicability.')
    parser.add_argument('--purpose', help='Use purpose for recommendation applicability.')
    parser.add_argument('--input-mode', action='append', default=[], help='Selected input mode; repeatable.')
    parser.add_argument('--visual-language', action='append', default=[], help='Declared visual treatment selector; repeatable.')


def description_from_args(args):
    context = None
    if args.output_kind and args.purpose:
        context = {'output_kind': args.output_kind, 'purpose': args.purpose,
                   'input_modes': args.input_mode, 'visual_language': args.visual_language}
    return describe(args.target, [*args.profiles, PROFILE_DIR], service=args.service,
                    operation=args.operation, context=context, guidance_paths=args.guidance)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Series Target Protocol support tool")
    sub = parser.add_subparsers(dest="command")

    p_validate = sub.add_parser("validate", help="Validate one target profile")
    p_validate.add_argument("path")

    p_seal = sub.add_parser("seal", help="Reseal one target profile with its canonical hash")
    p_seal.add_argument("path")
    p_seal.add_argument("--out")

    sub.add_parser("validate-catalog", help="Validate every profile the manifest lists")
    p_inspect = sub.add_parser("inspect", help="Show selected definition and applicable advice")
    add_selection_arguments(p_inspect, target_required=True)
    p_guidance = sub.add_parser("validate-guidance", help="Validate explicit target advice data")
    p_guidance.add_argument("path", type=Path)

    args = parser.parse_args(argv)
    if args.command == "inspect":
        print(json.dumps(description_from_args(args), ensure_ascii=False, indent=2))
        return 0
    if args.command == "validate-guidance":
        import target_guidance
        values = target_guidance.records(read_json(args.path))
        print(json.dumps({"ok": True, "guidance_records": len(values)}))
        return 0
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
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
