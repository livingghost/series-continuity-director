#!/usr/bin/env python3
"""Read explicitly selected generation-service configuration.

The service record is selected through --profiles, SERVICE_PROFILES_PATH or an
explicit resource configuration. There is no service implied by another
installation. Observation dates are reported from the supplied data, not refreshed
or inferred here. The independent project setup template supplies no credentials
and no claim about current provider capabilities.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resource_files import resolve_resource  # noqa: E402

RESOURCE = "service-profiles"


def resolve_path(explicit: str | None) -> Path | None:
    return resolve_resource(RESOURCE, explicit, "SERVICE_PROFILES_PATH")


def oldest_observation(value) -> str | None:
    dates: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get("observed_at"), str):
                dates.append(node["observed_at"])
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return min(dates) if dates else None


def load_service(service: str, explicit: str | None = None) -> tuple[dict, Path]:
    path = resolve_path(explicit)
    if path is None or not path.is_file():
        raise SystemExit(
            "service profiles not found: pass --profiles, set SERVICE_PROFILES_PATH, "
            "or declare service-profiles in the SERIES_RESOURCES configuration"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("services"), dict):
        raise SystemExit(f"{path}: not a service-profiles record")
    record = (data.get("services") or {}).get(service)
    if record is None:
        raise SystemExit(f"{path}: no service {service!r}; it records {sorted(data.get('services') or {})}")
    return record, path


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve a service profile")
    parser.add_argument("service")
    parser.add_argument("--profiles", help="Path to a service-profiles JSON file")
    parser.add_argument("--json", action="store_true", help="Print the record as JSON")
    args = parser.parse_args()
    record, path = load_service(args.service, args.profiles)
    oldest = record.get("observed_at") or oldest_observation(record)
    if args.json:
        print(json.dumps({"service": args.service, "path": str(path), "oldest_observed_at": oldest, "record": record}, ensure_ascii=False, indent=2))
        return 0
    print(f"{args.service}: {record.get('label', '')}  source {path}")
    print(f"  endpoint   {record['endpoint'].get('method', 'POST')} {record['endpoint'].get('base_url')}")
    print(f"  auth       {record['auth'].get('scheme')} in header {record['auth'].get('header')} from {record['auth'].get('env_var')}")
    print(f"  operations {', '.join(sorted(record.get('operations') or {}))}")
    for name, delivery in (record.get("delivery") or {}).items():
        print(f"  delivery   {name}: {delivery.get('mode')}; {delivery.get('poll')}; terminal when {delivery.get('terminal')}")
    print(f"  observed {oldest}  ({record.get('source', '')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
