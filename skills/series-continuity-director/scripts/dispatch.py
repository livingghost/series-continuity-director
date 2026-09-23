"""Send an approved submission to a service and record what came back.

The gate says what may be sent. This puts it on the wire and writes the evidence,
for any medium and any service. The service record (endpoint, auth, the
operations a service has, and the transport that speaks to it) is the
`service-profiles` resource. Its `"transport": "<name>"` selects the module
`transport_<name>.py` beside this file, which implements the interface in
`transport_contract.py`. Everything durable comes from the project records and
explicitly configured service data. The per-model request keys and constraints
are the target profile's offering.

Usage:
  python scripts/dispatch.py <spec.json>                 show the request, send nothing
  python scripts/dispatch.py <spec.json> --send --production-run <id> --authorization <receipt>
      --actor <actor> --outputs <n> --cost-bound <decimal> --currency <currency>
  python scripts/dispatch.py <spec.json> --send --poll   also wait for a pending task

Options:
  --service-profiles FILE  explicitly selected service declarations
  --profiles DIR   target profiles (default: this skill's own)
  --root DIR       root for relative paths (default: the spec's directory)

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
A send also needs a network deadline: `http_timeout_seconds` in the service
record or PRODUCTION_HTTP_TIMEOUT_SECONDS. Without one it stops before the claim.
Recovery is `production_dispatch.py --root <project> --run <run>`; it never resubmits.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import service_profile  # noqa: E402
import submission_gate  # noqa: E402
import transport_contract  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILES = ROOT / "protocols" / "target" / "profiles"


def api_key(service: dict[str, Any]) -> str:
    variable = ((service.get("auth") or {}).get("env_var") or "").strip()
    if not variable:
        raise ValueError("the service record names no auth.env_var")
    key = os.environ.get(variable, "").strip()
    if not key:
        raise ValueError(f"the credential is not in the environment. Set {variable} and run again.")
    return key


def gate_submission(spec: dict[str, Any]) -> dict[str, Any]:
    """Hand the gate the submission the spec declares, not a subset of it.

    Every field below is one `submission_gate.gate` reads. A field dropped here
    is decided as though the spec had left it out, and the gate then refuses on
    the omission rather than on the request: dropping `kind` refused every
    dispatch before anything else was looked at.
    """
    submission: dict[str, Any] = {
        "route_reading": spec.get("route_reading"),
        "visual_continuity": spec.get("visual_continuity"),
        "visual_continuity_sha256": spec.get("visual_continuity_sha256"),
        "output_kind": spec.get("output_kind"),
        "submission_id": spec.get("submission_id"),
        "kind": spec.get("kind"),
        "target": spec.get("target"),
        "service": spec.get("service"),
        "text": spec.get("text"),
        "text_form": spec.get("text_form"),
        "negative_text": spec.get("negative_text"),
        "inputs": [
            {"role": item.get("role"), "request_key": item.get("request_key"), "path": item.get("path"),
             **({"mode": item["mode"]} if "mode" in item else {})}
            for item in spec.get("inputs") or []
        ],
        "parameters": spec.get("parameters") or {},
        "obligations": spec.get("obligations") or {},
    }
    # A shot, a page or a passage carries these and an asset carries none of them,
    # so they travel only where the spec declares them. The gate refuses an asset
    # that names a scene, and writing the key in here would be this script
    # deciding that instead.
    for name in ("dialogue", "narrative", "scene_plot", "scene_id", "shot_id", "page_id", "panel",
                 "passage_id", "characters"):
        if name in spec:
            submission[name] = spec[name]
    return submission


def offering_for(spec: dict[str, Any], profiles: Path) -> dict[str, Any]:
    profile = submission_gate.load_profile(str(spec.get("target") or ""), profiles)
    if profile is None:
        raise ValueError('the selected target profile is absent')
    matches = [offering for offering in profile.get('offerings', [])
               if offering.get('service') == spec.get('service')
               and offering.get('model_identifier') == spec.get('model')]
    if len(matches) != 1:
        raise ValueError('select one exact service and model identifier from the target profile')
    return matches[0]


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
    parser.add_argument('--production-run',help='Prepared production run required for a send')
    parser.add_argument('--authorization',help='Recorded submit authorization')
    parser.add_argument('--actor',help='Actor named in that authorization')
    parser.add_argument('--preview-out', type=Path, help='New local file for the sealed preview; preview only.')
    parser.add_argument('--decision-out', type=Path, help='New actor-assessment draft for the exact request; preview only.')
    parser.add_argument('--request-decision',type=Path,help='Explicit final-request review and authority assessment.')
    parser.add_argument('--outputs',type=int,help='Explicit maximum and requested output count')
    parser.add_argument('--cost-bound',help='Decimal upper bound for this request')
    parser.add_argument('--currency',help='Currency of that bound, or none for zero-cost work')
    args = parser.parse_args(argv)
    try:
        return run(args)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as exc:
        print(f"dispatch: {exc}", file=sys.stderr)
        root = claimed_root(args) if args.send and args.production_run else None
        if root is not None:
            print("The submission claim is recorded, so do not send it again. Recover it with "
                  f"production_dispatch.py --root {root} --run {args.production_run}", file=sys.stderr)
        return 1


def claimed_root(args: argparse.Namespace) -> Path | None:
    """The project root when the run already holds a submission claim."""
    import production_workflow
    try:
        root = (args.root or args.spec.resolve().parent).resolve()
        rows = production_workflow.load_run(root, args.production_run)[3]
    except (ValueError, OSError, KeyError, TypeError, UnicodeError):
        return None
    return root if any(row['event'] == 'dispatch-claim' for row in rows) else None


def run(args: argparse.Namespace) -> int:
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    root = (args.root or args.spec.resolve().parent).resolve()

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
        raise ValueError("the spec names no service, and the target profile does not supply one")
    service, service_path = service_profile.load_service(service_id, args.service_profiles)
    transport = transport_contract.load(service)

    import production_dispatch
    import production_workflow
    import execution_contract as c
    consumer = None
    if args.production_run is not None:
        consumer = production_workflow.assert_current(root, args.production_run)[2]
    offering = offering_for(spec, args.profiles)
    built, report, validation = production_dispatch.render(root, spec, service, offering, transport, args.profiles, consumer=consumer)
    rendered = built['rendered']
    print(json.dumps({'request': rendered['request'], 'request_sha256': rendered['request_sha256'],
                     'request_trace': rendered['request_trace'], 'validation': validation,
                     'review_requirements': built['review_requirements']}, ensure_ascii=False, indent=2))
    observed = service.get("observed_at")
    print(f"service {service_id} through transport {service.get('transport')} at {(service.get('endpoint') or {}).get('base_url')} "
          f"(record observed {observed}, read from {service_path})")
    print(f"network deadline {service_profile.describe_timeout(service)}")
    if args.send and (args.preview_out or args.decision_out):
        raise ValueError('save preview and assessment files before selecting --send')
    destinations = [path.absolute() for path in (args.preview_out, args.decision_out) if path is not None]
    if len(set(destinations)) != len(destinations):
        raise ValueError('preview and assessment need distinct new files')
    for path in destinations:
        if path.exists():
            raise FileExistsError('preview destination already exists: ' + str(path))
    decision = None
    if args.decision_out:
        if not args.production_run or not args.authorization:
            raise ValueError('--decision-out requires the prepared run and selected submit authorization')
        import production_request
        directory, prepared, _, rows = production_workflow.load_run(root, args.production_run)
        grant = production_workflow.find(rows, 'authorization', args.authorization)['data']['authorization']
        decision = production_request.draft_decision(rendered, actor=args.actor, conditions=grant['stop_conditions'])
    if args.preview_out:
        c.atomic(args.preview_out, c.encoded({'request_contract': rendered, 'validation': validation,
            'review_requirements': built['review_requirements'], 'execution_ready': False,
            'external_effect': False, 'budget_effect': 'none'}))
    if args.decision_out:
        c.atomic(args.decision_out, c.encoded(decision))
    if not args.send:
        print('Preview recorded. Use the existing delegated scope or obtain the missing explicit authority before --send.')
        return 0

    if not all((args.production_run,args.authorization,args.actor,args.cost_bound,args.currency,args.request_decision)) or not args.outputs:
        raise ValueError('--send requires a prepared run, submit authorization, actor, request decision, output count, cost bound and currency')
    if args.poll_seconds<0 or args.poll_limit<0:raise ValueError('poll limits must be nonnegative')
    production_dispatch.preflight(service, transport)
    key = api_key(service)
    # External target profiles must also have been included as pinned task sources.
    directory,prepared,_,_=production_workflow.assert_current(root,args.production_run)
    if args.profiles.resolve()!=DEFAULT_PROFILES.resolve():
        for profile_file in args.profiles.rglob('*.json'):
            production_dispatch.pinned(root,directory,prepared,profile_file)
    result=production_dispatch.execute(root,args.production_run,args.spec.resolve(),spec,service_path,
        service,offering,report,transport,key,authorization=args.authorization,actor=args.actor,
        outputs=args.outputs,cost=args.cost_bound,currency=args.currency,profiles=args.profiles,decision=c.load(args.request_decision),rendered=rendered,poll=args.poll,
        poll_seconds=args.poll_seconds,poll_limit=args.poll_limit)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
