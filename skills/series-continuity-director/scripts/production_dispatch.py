"""One bounded submission per prepared run, with durable no-resend recovery.

Called by dispatch.py after its normal gate. The spec, selected primary text,
service record and every uploaded file must be pinned prepared inputs. A send
reserves authority before any upload. Recovery only polls or retrieves the
already accepted result, never uploads or resubmits. No credential is recorded.
"""
from __future__ import annotations
from io_budget import environment_seconds

import argparse
import copy
import json
import re
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

import execution_contract as c
import production_workflow as w


def relative(root: Path, path: Path) -> str:
    try:
        result=path.absolute().relative_to(root.absolute()).as_posix()
    except ValueError as exc:
        raise ValueError('submission dependencies and outputs must belong to the project') from exc
    c.local(root,result)
    return result


def pinned(root: Path, directory: Path, prepared: dict, path: Path) -> tuple[str,bytes]:
    rel=relative(root,path)
    matches=[d for d in prepared['dependencies'] if d['space']=='project' and d['path']==rel]
    if len(matches)!=1:
        raise ValueError(f'submission dependency is not a prepared source: {rel}')
    raw=c.read(c.local(root,rel))
    if c.digest(raw)!=matches[0]['sha256'] or c.object_read(directory,matches[0]['sha256'])!=raw:
        raise ValueError('submission dependency changed')
    return rel,raw


def safe_output(root: Path, spec: dict) -> tuple[str,str,str]:
    out=spec.get('output') or {}
    directory=out.get('dir','outputs')
    base=out.get('basename') or spec['submission_id'];suffix=out.get('suffix','.png')
    if not isinstance(directory,str) or directory in ('','.'):raise ValueError('declare an output directory')
    c.local(root,directory,exists=False)
    if not isinstance(base,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}',base):
        raise ValueError('output basename must be a single safe component')
    if not isinstance(suffix,str) or not re.fullmatch(r'\.[A-Za-z0-9]{1,12}',suffix):
        raise ValueError('output suffix must be an extension')
    return directory,base,suffix


def append_trace(root: Path, run: str, claim: str, name: str, value: Any) -> dict:
    """Commit external evidence into the run chain as well as its readable journal."""
    with c.lock(root):
        directory,p,_,rows=w.load_run(root,run)
        target=directory/'dispatch'/claim/name
        raw=c.encoded(value)
        if target.exists():
            if c.read(target)!=raw:raise ValueError('durable dispatch evidence differs')
        else:c.atomic(target,raw)
        f=w.file_record(root,directory,target.relative_to(root).as_posix())
        return w.append_record(directory,p,rows,'dispatch-trace',{'claim':claim,'stage':name,'files':[f]})


def render(root: Path, spec: dict, service: dict, offering: dict, transport: Any,
           profiles: Path, *, consumer: dict | None = None) -> tuple[dict, dict, dict]:
    """Run the ordinary gate and assemble one exact request without an external effect."""
    import submission_gate
    import request_renderer
    import production_request
    report = submission_gate.gate(spec, profiles, root)
    if report['status'] != 'admitted':
        raise ValueError('submission gate: ' + '; '.join(item['code'] + ': ' + item['message'] for item in report['errors']))
    profile = submission_gate.load_profile(str(spec['target']), profiles)
    if profile is None:
        raise ValueError('model execution requires the explicitly selected target profile')
    import target_protocol
    profile_report = target_protocol.validate_profile(profile)
    if not profile_report['ok'] or profile['target_id'] != spec['target']:
        raise ValueError('selected target profile is invalid or names another target')
    candidates = [item for item in profile.get('offerings', [])
                  if item.get('service') == spec['service'] and item.get('model_identifier') == spec['model']]
    if len(candidates) != 1 or candidates[0] != offering:
        raise ValueError('select one exact offering from the declared target profile')
    built = request_renderer.submission(spec, profile, offering, service, transport, root=root, consumer=consumer)
    validation = production_request.validate_request(spec, built['rendered'], live_root=root)
    return built, report, validation


def begin(root: Path, run: str, spec_path: Path, spec: dict, service_path: Path,
          service: dict, offering: dict, report: dict, *, authorization: str, actor: str,
          outputs: int, cost: str, currency: str, profiles: Path, transport: Any,
          rendered: dict, decision: dict) -> tuple[dict, dict]:
    if type(outputs) is not int or outputs < 1:
        raise ValueError('a submission must reserve a positive output count')
    safe_output(root, spec)
    import request_contract as rc
    import production_request
    import production_authority
    with c.lock(root):
        directory, p, consumer, rows = w.assert_current(root, run)
        if any(r['event'] == 'dispatch-claim' for r in rows):
            raise ValueError('this run already has a submission claim; recover it, never resend')
        if w.find(rows, 'handoff')['data']['method'] != 'dispatcher':
            raise ValueError('submission needs a dispatcher handoff')
        spec_rel, raw = pinned(root, directory, p, spec_path)
        if c.decode(raw) != spec:
            raise ValueError('submission changed after the gate')
        if spec.get('text') != consumer['instructions']:
            raise ValueError('submission primary text differs from the prepared rendition')
        service_rel, service_raw = pinned(root, directory, p, service_path)
        import service_profile
        actual, _ = service_profile.load_service(str(spec['service']), str(service_path))
        if actual != service:
            raise ValueError('service differs from the prepared record')
        # Imported profiles are project sources. Built-in profiles are captured
        # in the prepared skill dependencies by the ordinary preparation path.
        if profiles.resolve() != (w.ROOT / 'protocols/target/profiles').resolve():
            for file in profiles.glob('*.json'):
                value = c.load(file)
                if value.get('target_id') == spec['target']:
                    pinned(root, directory, p, file)
        current, fresh_report, _ = render(root, spec, service, offering, transport, profiles, consumer=consumer)
        if rc.receipt_projection(current['rendered']) != rc.receipt_projection(rendered):
            raise ValueError('request changed after preview and before its claim')
        if rendered['output_count'] != outputs:
            raise ValueError('rendered output count differs from the authorized bound')
        grant = w.find(rows, 'authorization', authorization)['data']['authorization']
        _, permission = production_authority.select_permission(grant, 'submit',
            ['submission:' + str(spec['submission_id'])], currency)
        assessment, sources = production_request.check(root, p, spec, rendered, decision, grant, permission, actor=actor)
        media = []
        if len(rendered['media']) != len(spec['inputs']):
            raise ValueError('rendered media count differs from the declared inputs')
        for index, item in enumerate(spec['inputs']):
            rel, raw = pinned(root, directory, p, root / item['path'])
            expected = rendered['media'][index]
            if c.digest(raw) != expected['sha256'] or len(raw) != expected['size']:
                raise ValueError('prepared media differ from the final request')
            media.append({'spec_path': item['path'], 'path': rel, 'sha256': c.digest(raw), 'size': len(raw)})
        manifest = {'spec': spec, 'spec_path': spec_rel, 'service': service, 'service_path': service_rel,
            'offering': offering, 'gate': fresh_report, 'media': media, 'outputs': outputs,
            'request_sha256': rendered['request_sha256'], 'rendered': rc.receipt_projection(rendered),
            'request_decision': copy.deepcopy(decision), 'request_assessment': assessment}
        evidence = [w.file_record(root, directory, item['path']) for item in sources]
        reserved = w._reserve(directory, p, rows, authorization=authorization, actor=actor, operation='submit',
            scopes=['submission:' + str(spec['submission_id'])], outputs=outputs, cost=cost, currency=currency,
            request_sha256=rendered['request_sha256'])
        rows = w.load_run(root, run)[3]
        claim = w.append_record(directory, p, rows, 'dispatch-claim', {'reservation': reserved['sha256'],
            'manifest': manifest, 'manifest_sha256': c.content_id(manifest), 'evidence': evidence})
        return claim, manifest


def verify_trace(root: Path, run: str, claim: str) -> tuple[Path,dict,list[dict]]:
    directory,p,_,rows=w.load_run(root,run)
    wanted=w.find(rows,'dispatch-claim',claim)
    if c.content_id(wanted['data']['manifest'])!=wanted['data']['manifest_sha256']:
        raise ValueError('dispatch manifest mismatch')
    import request_contract as rc
    manifest = wanted['data']['manifest']
    rc.validate_seal(manifest['rendered'])
    if manifest['request_sha256'] != manifest['rendered']['request_sha256']:
        raise ValueError('dispatch request hash mismatch')
    reserved = w.find(rows, 'reservation', wanted['data']['reservation'])
    if reserved['data']['request_sha256'] != manifest['request_sha256']:
        raise ValueError('dispatch request differs from its reservation')
    for row in rows:
        if row['event']=='dispatch-trace' and row['data']['claim']==claim:
            for f in row['data']['files']:
                if c.read(c.local(root,f['path']))!=c.object_read(directory,f['sha256']):
                    raise ValueError('dispatch trace was modified')
    recorded = {row['data']['stage']: c.decode(c.object_read(directory, row['data']['files'][0]['sha256']))
                for row in rows if row['event'] == 'dispatch-trace' and row['data']['claim'] == claim}
    if 'request-contract.json' in recorded:
        exact = recorded['request-contract.json']
        rc.validate_seal(exact)
        if rc.receipt_projection(exact) != manifest['rendered']:
            raise ValueError('recorded request contract differs from the reserved request')
        uploads = {}
        for index, media in enumerate(exact['media']):
            item = recorded.get(f'upload-{index + 1:03d}.json')
            if item is not None:
                if item.get('index') != index or item.get('source_sha256') != media['sha256']:
                    raise ValueError('recorded upload belongs to another input')
                uploads[index] = c.text(item.get('provider_id'), 'provider input ID')
        if 'request.json' in recorded:
            rc.validate_wire(exact, recorded['request.json'], uploads)
    elif 'request.json' in recorded:
        raise ValueError('recorded send has no sealed request contract')
    return directory,manifest,rows


def obtain(root: Path, run: str, claim: str, transport: Any, key: str, *, poll: bool,
           poll_seconds: float, poll_limit: int) -> dict:
    directory,manifest,rows=verify_trace(root,run,claim)
    if any(r['event']=='dispatch-results' and r['data']['claim']==claim for r in rows):
        # Integrity still matters when bookkeeping is repeated.
        row=w.find(rows,'dispatch-results')
        for f in row['data']['files']:
            if c.read(c.local(root,f['path']))!=c.object_read(directory,f['sha256']):
                raise ValueError('acquired output was modified')
        for f in row['data']['files']:w.capture_dispatch_result(root,run,f['path'])
        return row
    trace=[r for r in rows if r['event']=='dispatch-trace' and r['data']['claim']==claim]
    responses=[r for r in trace if r['data']['stage'].startswith(('answer','poll-'))]
    if not responses:
        raise ValueError('no recorded response; reconcile the uncertain request with the provider, do not resend')
    f=responses[-1]['data']['files'][0];answer=c.decode(c.object_read(directory,f['sha256']))
    merged=responses[-1]['data']['stage'].startswith('answer-merged-')
    entries=answer['entries'] if merged else transport.results(answer)
    if not merged and transport.rejections(answer):raise ValueError('provider refused the recorded request')
    if len(entries)>manifest['outputs']:raise ValueError('provider returned more outputs than the reserved bound')
    poll_index=sum(r['data']['stage'].startswith('poll-') for r in trace)
    for _ in range(poll_limit if poll else 0):
        pending=list(dict.fromkeys(e['id'] for e in entries if e.get('pending') and e.get('id')))
        if not pending:break
        time.sleep(poll_seconds)
        answer=transport.poll(pending,manifest['service'],key)
        poll_index+=1;append_trace(root,run,claim,f'poll-{poll_index:06d}.json',answer)
        if transport.rejections(answer):raise ValueError('provider refused the existing task while polling')
        # Keep completed entries from earlier responses when polling only pending IDs.
        revised=transport.results(answer)
        replaced={e.get('id') for e in revised}
        retained=[e for e in entries if not e.get('pending') or e.get('id') not in replaced]
        # A task may produce several artifacts. Its task ID alone is not an
        # artifact identity: retain distinct URLs and replace only pending rows.
        by_artifact={(e.get('id'),e.get('url')):e for e in retained}
        for e in revised:by_artifact[(e.get('id'),e.get('url'))]=e
        entries=list(by_artifact.values())
        if len(entries)>manifest['outputs']:
            raise ValueError('provider returned more outputs than the reserved bound')
        append_trace(root,run,claim,f'answer-merged-{poll_index:06d}.json',{'entries':entries,'merge_of_recorded_responses':True})
    if len(entries)!=manifest['outputs'] or any(e.get('pending') or not e.get('url') for e in entries):
        raise ValueError('not every reserved output is available; recover the recorded tasks without resending')
    target,base,suffix=safe_output(root,manifest['spec']);files=[]
    for index,entry in enumerate(entries):
        # URLs are provider data, not arbitrary new code or credentials.
        url=entry['url']
        if not isinstance(url,str) or not url.startswith(('https://','http://')):
            raise ValueError('unsupported result URL')
        with urllib.request.urlopen(url,timeout=environment_seconds("PRODUCTION_HTTP_TIMEOUT_SECONDS")) as response:
            raw=response.read()
        if not raw:raise ValueError('empty provider output')
        rel=f'{target}/{base}-{index+1:03d}{suffix}';path=c.local(root,rel,exists=False)
        if path.exists():
            if c.read(path)!=raw:raise ValueError('refusing to overwrite an existing output')
        else:c.atomic(path,raw)
        append_trace(root,run,claim,f'download-{index+1:03d}.json',
                     {'path':rel,'sha256':c.digest(raw),'size':len(raw),'result':entry})
        files.append(rel)
    with c.lock(root):
        directory,p,_,rows=w.load_run(root,run)
        evidence=[f for r in rows if r['event']=='dispatch-trace' and r['data']['claim']==claim for f in r['data']['files']]
        result=w.append_record(directory,p,rows,'dispatch-results',{'claim':claim,
          'files':[w.file_record(root,directory,f) for f in files],'evidence':evidence,'expected_count':manifest['outputs']})
    # Candidate registration uses the same workflow as manually observed outputs.
    for path in files:w.capture_dispatch_result(root,run,path)
    return result


def execute(root: Path, run: str, spec_path: Path, spec: dict, service_path: Path, service: dict,
            offering: dict, report: dict, transport: Any, key: str, *, profiles: Path,
            decision: dict, rendered: dict | None = None, **options: Any) -> dict:
    poll = bool(options.pop('poll', False)); poll_seconds = options.pop('poll_seconds', 20); poll_limit = options.pop('poll_limit', 60)
    import request_contract as rc
    _, _, consumer, _ = w.assert_current(root, run)
    built, fresh_report, _ = render(root, spec, service, offering, transport, profiles, consumer=consumer)
    if rendered is not None:
        if rc.receipt_projection(rendered) != rc.receipt_projection(built['rendered']):
            raise ValueError('current request differs from its supplied preview')
    else:
        rendered = built['rendered']
    claim, manifest = begin(root, run, spec_path, spec, service_path, service, offering, fresh_report,
        profiles=profiles, transport=transport, rendered=rendered, decision=decision, **options)
    claim_id = claim['sha256']; directory = w.run_dir(root, run)
    append_trace(root, run, claim_id, 'manifest.json', manifest)
    append_trace(root, run, claim_id, 'request-contract.json', rendered)
    media_ids = {}
    for index, source in enumerate(manifest['media']):
        raw = c.object_read(directory, source['sha256'])
        item = rendered['media'][index]
        if c.digest(raw) != item['sha256'] or len(raw) != item['size']:
            raise ValueError('upload byte snapshot differs from the sealed request')
        w.lifecycle.begin_step(root, run, claim['data']['reservation'], claim=claim_id, step=f'upload:{index}', operation='upload')
        media_ids[index] = transport.upload_bytes(raw, item['media_type'], service, key)
        append_trace(root, run, claim_id, f'upload-{index+1:03d}.json',
            {'index': index, 'source': source, 'source_sha256': item['sha256'], 'provider_id': media_ids[index]})
    request = rc.materialize(rendered, media_ids)
    rc.validate_wire(rendered, request, media_ids)
    append_trace(root, run, claim_id, 'request.json', request)
    w.lifecycle.begin_step(root, run, claim['data']['reservation'], claim=claim_id, step='send', operation='send')
    answer = transport.send(request, service, key)
    append_trace(root, run, claim_id, 'answer.json', answer)
    append_trace(root, run, claim_id, 'transport-outcome.json',
        {'outcome': transport.observation_outcome(answer), 'response_sha256': c.digest(c.encoded(answer))})
    return obtain(root, run, claim_id, transport, key, poll=poll, poll_seconds=poll_seconds, poll_limit=poll_limit)


def recover(root: Path, run: str, *, poll: bool=False,poll_seconds: float=20,poll_limit: int=60) -> dict:
    import dispatch
    _,_,_,rows=w.load_run(root,run);claim=w.find(rows,'dispatch-claim')
    manifest=claim['data']['manifest'];service=manifest['service']
    transport=dispatch.load_transport(manifest['spec']['service'])
    return obtain(root,run,claim['sha256'],transport,dispatch.api_key(service) if poll else '',
                  poll=poll,poll_seconds=poll_seconds,poll_limit=poll_limit)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--run',required=True)
    parser.add_argument('--poll',action='store_true');parser.add_argument('--poll-seconds',type=float,default=20)
    parser.add_argument('--poll-limit',type=int,default=60);args=parser.parse_args()
    try:
        if args.poll_seconds<0 or args.poll_limit<0:raise ValueError('poll limits must be nonnegative')
        result=recover(args.root.absolute(),args.run,poll=args.poll,poll_seconds=args.poll_seconds,poll_limit=args.poll_limit)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,KeyError) as exc:
        print(json.dumps({'ok':False,'error':str(exc),'resubmitted':False},ensure_ascii=False));return 1

if __name__=='__main__':raise SystemExit(main())
