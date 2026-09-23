#!/usr/bin/env python3
"""Read explicitly selected generation-service configuration.

The service record is selected through --profiles, SERVICE_PROFILES_PATH or an
explicit resource configuration. There is no service implied by another
installation. Observation dates are reported from the supplied data, not refreshed
or inferred here. The independent project setup template supplies no credentials
and no claim about current provider capabilities.

A service record names its transport, the module that speaks to that service:
`"transport": "<name>"` selects `scripts/transport_<name>.py`, which implements
`scripts/transport_contract.py`. Several records may name one transport.

The operator owns the network deadline. A service record may declare
`http_timeout_seconds`, the seconds each network wait may take for that service.
The PRODUCTION_HTTP_TIMEOUT_SECONDS environment variable takes precedence over it.
A send, poll or download with neither configured is refused before it starts.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from io_budget import environment_seconds, optional_seconds  # noqa: E402
from resource_files import resolve_resource  # noqa: E402

RESOURCE = "service-profiles"
TIMEOUT_FIELD = "http_timeout_seconds"
TIMEOUT_VARIABLE = "PRODUCTION_HTTP_TIMEOUT_SECONDS"
# Plain http reaches only these hosts, so a local test server needs no certificate.
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


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
        raise ValueError(
            "service profiles not found: pass --profiles, set SERVICE_PROFILES_PATH, "
            "or declare service-profiles in the SERIES_RESOURCES configuration"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("services"), dict):
        raise ValueError(f"{path}: not a service-profiles record")
    record = data["services"].get(service)
    if not isinstance(record, dict):
        raise ValueError(f"{path}: no service {service!r}; it records {sorted(data['services'])}")
    return record, path


def http_timeout(service: dict) -> tuple[float, str]:
    """Return the configured network deadline in seconds and where it came from."""
    seconds = environment_seconds(TIMEOUT_VARIABLE)
    if seconds is not None:
        return seconds, TIMEOUT_VARIABLE
    if service.get(TIMEOUT_FIELD) is not None:
        return optional_seconds(service[TIMEOUT_FIELD], TIMEOUT_FIELD), TIMEOUT_FIELD
    raise ValueError(
        f"no network deadline is configured. Set {TIMEOUT_FIELD} in the service record "
        f"or the {TIMEOUT_VARIABLE} environment variable to a positive number of seconds"
    )


def describe_timeout(service: dict) -> str:
    try:
        seconds, source = http_timeout(service)
    except ValueError as exc:
        return "not configured: " + str(exc)
    return f"{seconds:g} s per network wait, from {source}"


def transport_module(service: dict) -> str:
    """The transport module a record names, as scripts/transport_<name>.py."""
    import transport_contract
    return f"scripts/{transport_contract.module_name(service)}.py"


def describe_transport(service: dict) -> str:
    try:
        module = transport_module(service)
        return f"{service['transport']} ({module})"
    except ValueError as exc:
        return "not declared: " + str(exc)


def is_loopback(url: str) -> bool:
    return (urlsplit(url).hostname or "").lower() in LOOPBACK_HOSTS


def require_network_url(url: object, label: str, *, allow_loopback: bool = True) -> str:
    """Accept https anywhere, and plain http only for an explicit loopback host."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError(f"{label} is missing")
    parts = urlsplit(url)
    loopback = (parts.hostname or "").lower() in LOOPBACK_HOSTS
    if not parts.hostname or parts.scheme not in {"https", "http"}:
        raise ValueError(f"{label} must be an https URL with a host")
    if loopback and not allow_loopback:
        raise ValueError(f"{label} may not move a remote exchange to a loopback host")
    if parts.scheme == "http" and not loopback:
        raise ValueError(f"{label} must use https; plain http is accepted only for "
                         + ", ".join(sorted(LOOPBACK_HOSTS)))
    return url


def endpoint_url(service: dict) -> str:
    return require_network_url(((service.get("endpoint") or {}).get("base_url") or "").strip(),
                               "the service record's endpoint.base_url")


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve a service profile")
    parser.add_argument("service")
    parser.add_argument("--profiles", help="Path to a service-profiles JSON file")
    parser.add_argument("--json", action="store_true", help="Print the record as JSON")
    args = parser.parse_args()
    try:
        record, path = load_service(args.service, args.profiles)
    except (ValueError, OSError) as exc:
        print(f"service_profile: {exc}", file=sys.stderr)
        return 1
    oldest = record.get("observed_at") or oldest_observation(record)
    try:
        seconds, source = http_timeout(record)
        deadline = {"seconds": seconds, "source": source}
    except ValueError:
        deadline = None
    try:
        module = transport_module(record)
    except ValueError:
        module = None
    if args.json:
        print(json.dumps({"service": args.service, "path": str(path), "oldest_observed_at": oldest,
                          "transport": module, "http_timeout": deadline, "record": record},
                         ensure_ascii=False, indent=2))
        return 0
    endpoint = record.get("endpoint") or {}
    auth = record.get("auth") or {}
    print(f"{args.service}: {record.get('label', '')}  source {path}")
    print(f"  transport  {describe_transport(record)}")
    print(f"  endpoint   {endpoint.get('method', 'POST')} {endpoint.get('base_url')}")
    print(f"  auth       {auth.get('scheme')} in header {auth.get('header')} from {auth.get('env_var')}")
    print(f"  deadline   {describe_timeout(record)}")
    print(f"  operations {', '.join(sorted(record.get('operations') or {}))}")
    for name, delivery in (record.get("delivery") or {}).items():
        print(f"  delivery   {name}: {delivery.get('mode')}; {delivery.get('poll')}; terminal when {delivery.get('terminal')}")
    print(f"  observed {oldest}  ({record.get('source', '')})")
    return 0


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
