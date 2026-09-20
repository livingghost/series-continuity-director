#!/usr/bin/env python3
"""Store a service's parameter schema for one offering, so the gate can read it.

Usage: python scripts/observe_schema.py <target-id> <service-id> <schema.json> [--source "<where it came from>"]

The schema file is what the service returned for the model (its schema endpoint,
its documentation, or a tool that exposes it). It is stored as observed, with the
date and the source, under protocols/target/observed-schemas/<target>.<service>.json,
and the offering in the target profile is pointed at it. Re-run to refresh; the
date moves with the file.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import integration_contract  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Store an observed parameter schema for an offering")
    parser.add_argument("target")
    parser.add_argument("service")
    parser.add_argument("schema_file")
    parser.add_argument("--source", default="the service's model schema endpoint",
                        help="Where the schema came from, as a name and not a story")
    parser.add_argument("--added", nargs="*", default=[],
                        help="Top-level string keys added beyond what the source lists, such as the task envelope keys")
    args = parser.parse_args()
    profile_path = ROOT / "protocols/target/profiles" / f"{args.target}.json"
    if not profile_path.is_file():
        raise SystemExit(f"no target profile {profile_path}")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    offerings = [o for o in profile.get("offerings") or [] if o.get("service") == args.service]
    if not offerings:
        raise SystemExit(f"{args.target} records no offering on {args.service}")
    schema = json.loads(Path(args.schema_file).read_text(encoding="utf-8"))
    if isinstance(schema, dict) and "schema" in schema and "properties" not in schema:
        schema = schema["schema"]
    rel = f"protocols/target/observed-schemas/{args.target}.{args.service}.json"
    out = ROOT / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    for key in args.added:
        schema.setdefault("properties", {})[key] = {"type": "string"}
    wrapper = {
        "artifact_type": "observed-parameter-schema",
        "target_id": args.target,
        "service": args.service,
        "model_identifier": offerings[0].get("model_identifier"),
        "observed_at": date.today().isoformat(),
        "source": args.source,
        "added": list(args.added),
        "schema": schema,
    }
    out.write_text(json.dumps(wrapper, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    offerings[0]["schema_snapshot"] = rel
    offerings[0]["observed_at"] = wrapper["observed_at"]
    profile["profile_sha256"] = ""
    profile = integration_contract.finalize(profile, "profile_sha256")
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"ok": True, "snapshot": rel, "observed_at": wrapper["observed_at"], "profile": str(profile_path.relative_to(ROOT))}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
