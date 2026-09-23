"""One bounded submission per prepared run, with durable no-resend recovery.

Called by dispatch.py after its normal gate. The spec, selected primary text,
service record and every uploaded file must be pinned prepared inputs. A send
reserves authority before any upload. Recovery only polls or retrieves the
already accepted result, never uploads or resubmits. No credential is recorded.

Recovery rebuilds the outputs from every recorded response in order: the answer
and each poll response. A result URL uses https, or plain http on a loopback
host, and every redirect it follows keeps to the same rule. Each output streams
to disk under the operator's network deadline, and its digest and size are recorded.
Each send and each recovery rewrites the project's run gallery from the records.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
import re
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

import execution_contract as c
import production_workflow as w
import service_profile
import transport_contract


def preflight(service: dict, transport: Any) -> None:
    """Refuse a send whose transport, endpoint or deadline would fail after its claim."""
    transport_contract.check(transport)
    service_profile.endpoint_url(service)
    service_profile.http_timeout(service)


def refresh_gallery(root: Path, *, quiet: bool = False) -> None:
    """Rewrite the project's run gallery from the records; `quiet` keeps an earlier error first."""
    import run_gallery
    try:
        run_gallery.write(root)
    except (OSError, ValueError):
        if not quiet:
            raise


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


def require_declared_shape(offering: dict, layout: dict) -> None:
    """Refuse a request whose fields differ from the shape the gate checked for this offering."""
    from request_contract import path_parts
    shape = offering.get('request_shape')
    if not isinstance(shape, dict):
        raise ValueError('the offering declares no request_shape, so the gate did not check this request')
    for key, slot in (('model_key', 'model'), ('text_key', 'primary_text'), ('negative_text_key', 'negative_text')):
        if key in shape and layout[slot] is not None and layout[slot] != path_parts(shape[key]):
            raise ValueError(f"the transport writes {slot} at {'.'.join(map(str, layout[slot]))}, "
                             f"but the offering's request_shape declares {shape[key]}")


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
    require_declared_shape(offering, built['rendered']['layout'])
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


class _ResultRedirect(urllib.request.HTTPRedirectHandler):
    """Follow a result redirect only to a URL that the download rule accepts."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            service_profile.require_network_url(newurl, 'redirected result URL',
                                                allow_loopback=service_profile.is_loopback(req.full_url))
        except ValueError:
            fp.close()
            raise
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_result(url: str, seconds: float):
    """Open one provider result URL; the deadline bounds each network wait."""
    handlers: list[Any] = [_ResultRedirect]
    if service_profile.is_loopback(url):
        handlers.append(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener(*handlers).open(url, timeout=seconds)


def download(url: str, path: Path, seconds: float) -> tuple[str, int]:
    """Stream one result into a new file and return its SHA-256 and size."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    staged = Path(temporary)
    try:
        digest = hashlib.sha256()
        size = 0
        with os.fdopen(handle, 'wb') as stream, open_result(url, seconds) as response:
            while chunk := response.read(io.DEFAULT_BUFFER_SIZE):
                stream.write(chunk)
                digest.update(chunk)
                size += len(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        if not size:
            raise ValueError('empty provider output')
        identity = {'bytes': size, 'sha256': digest.hexdigest()}
        if path.exists():
            from io_budget import file_identity
            if file_identity(path) != identity:
                raise ValueError('refusing to overwrite an existing output')
        else:
            os.link(staged, path)
            c.fsync_dir(path.parent)
        return identity['sha256'], size
    finally:
        staged.unlink(missing_ok=True)


def merge_results(entries: list[dict], revised: list[dict]) -> list[dict]:
    """Apply one poll response to the known outputs and keep every completed one."""
    replaced = {e.get('id') for e in revised}
    retained = [e for e in entries if not e.get('pending') or e.get('id') not in replaced]
    # A task may produce several artifacts. Its task ID alone is not an
    # artifact identity: retain distinct URLs and replace only pending rows.
    by_artifact = {(e.get('id'), e.get('url')): e for e in retained}
    for e in revised:
        by_artifact[(e.get('id'), e.get('url'))] = e
    return list(by_artifact.values())


def recorded_responses(directory: Path, rows: list[dict], claim: str) -> tuple[Any, list[Any]]:
    """Return the recorded answer and every recorded poll response, in recorded order."""
    answer, polls, seen = None, [], set()
    for row in rows:
        if row['event'] != 'dispatch-trace' or row['data']['claim'] != claim:
            continue
        stage = row['data']['stage']
        if stage in seen or not (stage == 'answer.json' or stage.startswith('poll-')):
            continue
        seen.add(stage)
        value = c.decode(c.object_read(directory, row['data']['files'][0]['sha256']))
        if stage == 'answer.json':
            answer = value
        else:
            polls.append(value)
    return answer, polls


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
    answer,polls=recorded_responses(directory,rows,claim)
    if answer is None:
        raise ValueError('no recorded response; reconcile the uncertain request with the provider, do not resend')
    if transport.rejections(answer):raise ValueError('provider refused the recorded request')
    entries=transport.results(answer)
    if not entries:
        raise ValueError('the recorded answer names no task or output, so the outcome is unknown; '
                         'reconcile the recorded request with the provider and do not resend it')
    # Rebuild from every recorded response, so an interrupted merge loses no completed output.
    for response in polls:
        if transport.rejections(response):raise ValueError('provider refused the existing task while polling')
        entries=merge_results(entries,transport.results(response))
    if len(entries)>manifest['outputs']:raise ValueError('provider returned more outputs than the reserved bound')
    poll_index=len(polls);journal=directory/'dispatch'/claim
    for _ in range(poll_limit if poll else 0):
        pending=list(dict.fromkeys(e['id'] for e in entries if e.get('pending') and e.get('id')))
        if not pending:break
        if not callable(getattr(transport,'poll',None)):
            raise ValueError('the transport cannot poll the pending tasks; retrieve them from the provider by hand')
        time.sleep(poll_seconds)
        response=transport.poll(pending,manifest['service'],key)
        poll_index+=1
        # A poll file that an interrupted run wrote without its record keeps its name.
        while (journal/f'poll-{poll_index:06d}.json').exists():poll_index+=1
        append_trace(root,run,claim,f'poll-{poll_index:06d}.json',response)
        if transport.rejections(response):raise ValueError('provider refused the existing task while polling')
        entries=merge_results(entries,transport.results(response))
        if len(entries)>manifest['outputs']:
            raise ValueError('provider returned more outputs than the reserved bound')
    if len(entries)!=manifest['outputs'] or any(e.get('pending') or not e.get('url') for e in entries):
        raise ValueError('not every reserved output is available; recover the recorded tasks without resending')
    # URLs are provider data, not arbitrary new code or credentials.
    urls=[service_profile.require_network_url(e['url'],'provider result URL') for e in entries]
    seconds,_=service_profile.http_timeout(manifest['service'])
    target,base,suffix=safe_output(root,manifest['spec']);files=[]
    for index,(entry,url) in enumerate(zip(entries,urls)):
        rel=f'{target}/{base}-{index+1:03d}{suffix}'
        sha256,size=download(url,c.local(root,rel,exists=False),seconds)
        append_trace(root,run,claim,f'download-{index+1:03d}.json',
                     {'path':rel,'sha256':sha256,'size':size,'result':entry})
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
    preflight(service, transport)
    _, _, consumer, _ = w.assert_current(root, run)
    built, fresh_report, _ = render(root, spec, service, offering, transport, profiles, consumer=consumer)
    if rendered is not None:
        if rc.receipt_projection(rendered) != rc.receipt_projection(built['rendered']):
            raise ValueError('current request differs from its supplied preview')
    else:
        rendered = built['rendered']
    claim, manifest = begin(root, run, spec_path, spec, service_path, service, offering, fresh_report,
        profiles=profiles, transport=transport, rendered=rendered, decision=decision, **options)
    try:
        result = _submit(root, run, claim, manifest, rendered, service, transport, key,
                         poll=poll, poll_seconds=poll_seconds, poll_limit=poll_limit)
    except BaseException:
        refresh_gallery(root, quiet=True)
        raise
    refresh_gallery(root)
    return result


def _submit(root: Path, run: str, claim: dict, manifest: dict, rendered: dict, service: dict, transport: Any,
            key: str, *, poll: bool, poll_seconds: float, poll_limit: int) -> dict:
    import request_contract as rc
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
    outcome = transport.observation_outcome(answer)
    if outcome not in transport_contract.OUTCOMES:
        outcome = transport_contract.UNKNOWN
    append_trace(root, run, claim_id, 'transport-outcome.json',
        {'outcome': outcome, 'response_sha256': c.digest(c.encoded(answer))})
    return obtain(root, run, claim_id, transport, key, poll=poll, poll_seconds=poll_seconds, poll_limit=poll_limit)


def recover(root: Path, run: str, *, poll: bool=False,poll_seconds: float=20,poll_limit: int=60) -> dict:
    import dispatch
    _,_,_,rows=w.load_run(root,run);claim=w.find(rows,'dispatch-claim')
    manifest=claim['data']['manifest'];service=manifest['service']
    transport=transport_contract.load(service)
    try:
        result=obtain(root,run,claim['sha256'],transport,dispatch.api_key(service) if poll else '',
                      poll=poll,poll_seconds=poll_seconds,poll_limit=poll_limit)
    except BaseException:
        refresh_gallery(root,quiet=True)
        raise
    refresh_gallery(root)
    return result


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--run',required=True)
    parser.add_argument('--poll',action='store_true');parser.add_argument('--poll-seconds',type=float,default=20)
    parser.add_argument('--poll-limit',type=int,default=60);args=parser.parse_args()
    try:
        if args.poll_seconds<0 or args.poll_limit<0:raise ValueError('poll limits must be nonnegative')
        result=recover(args.root.absolute(),args.run,poll=args.poll,poll_seconds=args.poll_seconds,poll_limit=args.poll_limit)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,KeyError,TypeError,UnicodeError) as exc:
        print(json.dumps({'ok':False,'error':str(exc),'resubmitted':False},ensure_ascii=False));return 1

if __name__=='__main__':
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
