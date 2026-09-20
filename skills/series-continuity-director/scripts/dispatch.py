"""Send an approved submission to a service and record what came back.

The gate says what may be sent. This puts it on the wire and writes the evidence,
for any medium and any service: the service-specific half lives in a
`transport_<service>.py` module beside this file, and everything durable comes
from the project records and explicitly configured service data. The service record (endpoint, auth, the
operations a service has) is the `service-profiles` resource; the
per-model request keys and constraints are the target profile's offering.

Usage:
  python scripts/dispatch.py <spec.json>                 show the request, send nothing
  python scripts/dispatch.py <spec.json> --send --production-run <id> --authorization <receipt>
      --actor <actor> --outputs <n> --cost-bound <decimal> --currency <currency>
  python scripts/dispatch.py <spec.json> --send --poll   also wait for a pending task

Options:
  --service-profiles FILE  explicitly selected service declarations
  --profiles DIR   target profiles (default: this skill's own)
  --root DIR       root for relative paths (default: the spec's directory)
  --runs DIR       where the run record is written (default: <root>/runs)

Spec:
  {"submission_id", "kind", "target", "service", "operation", "model",
   "text", "text_form", "negative_text", "dialogue",
   "narrative", "scene_plot", "scene_id", "shot_id", "characters",
   "inputs": [{"role", "path", "request_key" (optional)}],
   "parameters": {request key: value},
   "obligations": {"locks": [], "permanent_features": []},
   "output": {"dir", "basename", "suffix"}}

`kind` is "shot" or "asset", and the gate refuses a submission that declares
neither. A shot also carries the approved `scene_plot` it was written from, its
own `shot_id`, the `narrative` above that plot, and the `characters` in it; an
asset belongs to no scene and carries none of those. Everything the gate reads
is passed to it unchanged, so the run is refused or admitted on what the spec
actually declares.

The dry run is what section 6.1 asks for: it prints the exact request, so the
user approves the thing that would be sent rather than a description of it. No
byte leaves the machine without `--send` and a bounded production authorization.
Recovery is `production_dispatch.py --root <project> --run <run>`; it never resubmits.
"""
from __future__ import annotations
from io_budget import environment_seconds

import argparse
import hashlib
import importlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_gallery  # noqa: E402
import service_profile  # noqa: E402
import submission_gate  # noqa: E402


def stamp() -> str:
    """When a run happened, in UTC, so the run records order themselves."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILES = ROOT / "protocols" / "target" / "profiles"


def load_transport(service_id: str):
    try:
        return importlib.import_module(f"transport_{service_id.replace('-', '_')}")
    except ModuleNotFoundError:
        raise SystemExit(
            f"no transport for the service {service_id!r}. Write scripts/transport_{service_id}.py "
            "against the contract in transport_runware.py, or send this submission by hand."
        )


def api_key(service: dict[str, Any]) -> str:
    variable = ((service.get("auth") or {}).get("env_var") or "").strip()
    if not variable:
        raise SystemExit("the service record names no auth.env_var")
    key = os.environ.get(variable, "").strip()
    if not key:
        raise SystemExit(f"the credential is not in the environment. Set {variable} and run again.")
    return key


def gate_submission(spec: dict[str, Any]) -> dict[str, Any]:
    """Hand the gate the submission the spec declares, not a subset of it.

    Every field below is one `submission_gate.gate` reads. A field dropped here
    is decided as though the spec had left it out, and the gate then refuses on
    the omission rather than on the request: dropping `kind` refused every
    dispatch before anything else was looked at.
    """
    submission: dict[str, Any] = {
        "submission_id": spec.get("submission_id"),
        "kind": spec.get("kind"),
        "target": spec.get("target"),
        "service": spec.get("service"),
        "text": spec.get("text"),
        "text_form": spec.get("text_form"),
        "negative_text": spec.get("negative_text"),
        "inputs": [
            {"role": item.get("role"), "request_key": item.get("request_key"), "path": item.get("path")}
            for item in spec.get("inputs") or []
        ],
        "parameters": spec.get("parameters") or {},
        "obligations": spec.get("obligations") or {},
    }
    # A shot carries these and an asset carries none of them, so they travel only
    # where the spec declares them. The gate refuses an asset that names a scene,
    # and writing the key in here would be this script deciding that instead.
    for name in ("dialogue", "narrative", "scene_plot", "scene_id", "shot_id", "characters"):
        if name in spec:
            submission[name] = spec[name]
    return submission


def offering_for(spec: dict[str, Any], profiles: Path) -> dict[str, Any]:
    profile = submission_gate.load_profile(str(spec.get("target") or ""), profiles)
    if profile is None:
        return {}
    for offering in profile.get("offerings") or []:
        if not spec.get("service") or offering.get("service") == spec.get("service"):
            return offering
    return {}


def save(url: str, destination: Path) -> str:
    with urllib.request.urlopen(url, timeout=environment_seconds("PRODUCTION_HTTP_TIMEOUT_SECONDS")) as response:
        data = response.read()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send an approved submission and record the run.")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--send", action="store_true", help="Actually send. Without it nothing leaves the machine.")
    parser.add_argument("--poll", action="store_true", help="Wait for a task the service accepted but has not finished.")
    parser.add_argument("--poll-seconds", type=int, default=20)
    parser.add_argument("--poll-limit", type=int, default=60)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--service-profiles", help="Explicit service-profile data file")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--runs", type=Path, default=None)
    parser.add_argument('--production-run',help='Prepared production run required for a send')
    parser.add_argument('--authorization',help='Recorded submit authorization')
    parser.add_argument('--actor',help='Actor named in that authorization')
    parser.add_argument('--outputs',type=int,help='Explicit maximum and requested output count')
    parser.add_argument('--cost-bound',help='Decimal upper bound for this request')
    parser.add_argument('--currency',help='Currency of that bound, or none for zero-cost work')
    args = parser.parse_args(argv)

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    root = (args.root or args.spec.resolve().parent).resolve()
    runs = args.runs or (root / "runs")

    report = submission_gate.gate(gate_submission(spec), args.profiles, root)
    print(f"gate {report['status']}: {report['submission_id']} -> {report['target']}")
    for item in report["errors"]:
        print(f"  refused  {item['code']}: {item['message']}")
    for item in report["unmeasured"]:
        print(f"  unmeasured  {item}")
    if report["status"] == "refused":
        print("Nothing was sent.")
        return 1

    service_id = str(spec.get("service") or report.get("service") or "")
    if not service_id:
        raise SystemExit("the spec names no service, and the target profile does not supply one")
    service, service_path = service_profile.load_service(service_id, args.service_profiles)
    transport = load_transport(service_id)

    paths = [str((root / p).resolve()) if not Path(p).is_absolute() else p
             for p in transport.media_paths(spec, offering_for(spec, args.profiles))]
    offering = offering_for(spec, args.profiles)
    preview = transport.build(spec, offering, service, {})
    print(json.dumps(preview, ensure_ascii=False, indent=2))
    for path in paths:
        print(f"  file  {path}")
    observed = service.get("observed_at")
    print(f"service {service_id} at {(service.get('endpoint') or {}).get('base_url')} (record observed {observed}, read from {service_path})")
    if not args.send:
        print("Dry run. Nothing was sent. Add --send once the user has approved this exact request.")
        return 0

    if not all((args.production_run,args.authorization,args.actor,args.cost_bound,args.currency)) or not args.outputs:
        raise SystemExit('--send requires a prepared run, submit authorization, actor, output count, cost bound and currency')
    if args.poll_seconds<0 or args.poll_limit<0:raise SystemExit('poll limits must be nonnegative')
    # External target profiles must also have been included as pinned task sources.
    import production_dispatch
    import production_workflow
    import execution_contract
    directory,prepared,_,_=production_workflow.assert_current(root,args.production_run)
    if args.profiles.resolve()!=DEFAULT_PROFILES.resolve():
        for profile_file in args.profiles.rglob('*.json'):
            production_dispatch.pinned(root,directory,prepared,profile_file)
    result=production_dispatch.execute(root,args.production_run,args.spec.resolve(),spec,service_path,
        service,offering,report,transport,api_key(service),authorization=args.authorization,actor=args.actor,
        outputs=args.outputs,cost=args.cost_bound,currency=args.currency,poll=args.poll,
        poll_seconds=args.poll_seconds,poll_limit=args.poll_limit)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
