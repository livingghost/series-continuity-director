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

`kind` is "shot", "page", "passage" or "asset", and the gate refuses any
other. A shot, page or passage also carries the approved `scene_plot` it was
written from, its unit, the `narrative` above that plot, and the `characters`
in it; an asset belongs to no scene and carries none of those. `model` and
`operation` select the offering and the service operation, and
`production_workflow.py build-inputs` adds `request_validation` and
`input_snapshots`. Everything the gate reads
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
    """Validate the complete declaration, including its pinned execution choices."""
    import copy
    return copy.deepcopy(spec)


def service_models(spec: dict[str, Any], profiles: Path) -> list[str]:
    """The model identifiers the target's offerings record for the spec's service."""
    profile = submission_gate.load_profile(str(spec.get("target") or ""), profiles)
    return [str(offering.get('model_identifier')) for offering in (profile or {}).get('offerings', [])
            if offering.get('service') == spec.get('service')]


def dispatch_fields(spec: dict[str, Any], service: dict[str, Any], profiles: Path) -> None:
    """Name each field a dispatch reads beyond the submission, with what fills it."""
    problems = []
    if spec.get('model') is None:
        models = service_models(spec, profiles)
        problems.append('"model", the model_identifier of the offering: '
                        + (' or '.join(map(repr, models)) or f'no offering of {spec.get("target")!r} '
                           f'on {spec.get("service")!r} records one'))
    if spec.get('operation') is None:
        operations = list(service.get('operations') or {})
        problems.append('"operation", one the service record declares: '
                        + (', '.join(map(repr, operations)) or 'it declares none'))
    lacking = [name for name in ('request_validation', 'input_snapshots') if name not in spec]
    if lacking:
        problems.append(' and '.join(lacking) + ', which production_workflow.py build-inputs writes '
                        'from the validation choices (examples/input-assembly/README.md)')
    if problems:
        raise ValueError('the spec lacks what a dispatch reads beyond the submission: ' + '; '.join(problems))


def offering_for(spec: dict[str, Any], profiles: Path) -> dict[str, Any]:
    profile = submission_gate.load_profile(str(spec.get("target") or ""), profiles)
    if profile is None:
        raise ValueError('the selected target profile is absent')
    matches = [offering for offering in profile.get('offerings', [])
               if offering.get('service') == spec.get('service')
               and offering.get('model_identifier') == spec.get('model')]
    if len(matches) != 1:
        models = service_models(spec, profiles)
        raise ValueError(f'the spec names model {spec.get("model")!r} on service {spec.get("service")!r}; '
                         f'the profile {profile.get("target_id")} records '
                         + (' or '.join(map(repr, models)) or 'no offering on that service'))
    return matches[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send an approved submission and record the run.")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--send", action="store_true", help="Actually send. Without it nothing leaves the machine.")
    parser.add_argument("--poll", action="store_true", help="Wait for a task the service accepted but has not finished.")
    parser.add_argument("--poll-seconds", type=int, default=20)
    parser.add_argument("--poll-limit", type=int, default=60)
    parser.add_argument("--profiles", type=Path, action="append", default=[], help="Profile directory in priority order; repeatable.")
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
    from target_protocol import profile_directories, selected_profile
    args.profiles = profile_directories(args.profiles) + [DEFAULT_PROFILES]
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
    import runtime_evidence
    import copy
    reader = runtime_evidence.reader(root, snapshots=copy.deepcopy(spec.get('input_snapshots', {})))
    if not isinstance(spec.get('execution_choices'), dict):
        raise ValueError('build-inputs must resolve execution choices before dispatch')
    service_ref = spec['execution_choices']['selection']['service_profiles']
    selected_data = reader.json(service_ref)
    service_path = reader.resolve(service_ref['path'])
    service = selected_data['services'][service_id]
    if args.service_profiles:
        supplied, _ = service_profile.load_service(service_id, args.service_profiles, flag='--service-profiles')
        if supplied != service:
            raise ValueError('service override differs from the pinned selection')
    transport = transport_contract.load(service)
    dispatch_fields(spec, service, args.profiles)

    import production_dispatch
    import production_workflow
    import execution_contract as c
    consumer = None
    if args.production_run is not None:
        consumer = production_workflow.assert_current(root, args.production_run)[2]
    selected = selected_profile(spec, args.profiles, root)
    if selected is None:
        raise ValueError('selected model definition is missing')
    offering = next(x for x in selected[1]['offerings'] if x['service'] == spec['service'] and x['model_identifier'] == spec['model'])
    built, report, validation = production_dispatch.render(root, spec, service, offering, transport, args.profiles, consumer=consumer)
    rendered = built['rendered']
    print(json.dumps({'request': rendered['request'], 'request_sha256': rendered['request_sha256'],
                     'request_trace': rendered['request_trace'], 'validation': validation,
                     'review_requirements': built['review_requirements'], 'target_info': built['target_info'],
                     'setting_choices': built['setting_choices']}, ensure_ascii=False, indent=2))
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
            'review_requirements': built['review_requirements'], 'target_info': built['target_info'],
            'setting_choices': built['setting_choices'], 'execution_ready': False,
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
    from target_protocol import selected_profile
    selected_path, _ = selected_profile(spec, args.profiles, root)
    if not selected_path.is_relative_to(ROOT):
        production_dispatch.pinned(root, directory, prepared, selected_path)
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
