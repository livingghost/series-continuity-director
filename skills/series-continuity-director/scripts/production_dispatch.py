"""One bounded submission per prepared run, with durable no-resend recovery.

Called by dispatch.py after its normal gate. The spec, selected primary text,
service record and every uploaded file must be pinned prepared inputs. A send
reserves authority before any upload. Recovery only polls or retrieves the
already accepted result, never uploads or resubmits. No credential is recorded.
"""
from __future__ import annotations
from io_budget import environment_seconds

import argparse
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


def begin(root: Path, run: str, spec_path: Path, spec: dict, service_path: Path,
          service: dict, offering: dict, report: dict, *, authorization: str, actor: str,
          outputs: int, cost: str, currency: str) -> tuple[dict,dict]:
    if isinstance(outputs,bool) or not isinstance(outputs,int) or outputs<1:
        raise ValueError('a submission must reserve a positive output count')
    safe_output(root,spec)
    with c.lock(root):
        directory,p,consumer,rows=w.assert_current(root,run)
        if any(r['event']=='dispatch-claim' for r in rows):
            raise ValueError('this run already has a submission claim; recover it, never resend')
        if w.find(rows,'handoff')['data']['method']!='dispatcher':
            raise ValueError('submission needs a dispatcher handoff')
        spec_rel,raw=pinned(root,directory,p,spec_path)
        if c.decode(raw)!=spec:raise ValueError('submission changed after the gate')
        if spec.get('text')!=consumer['instructions']:
            raise ValueError('submission primary text differs from the prepared rendition')
        service_rel,service_raw=pinned(root,directory,p,service_path)
        import service_profile
        actual,_=service_profile.load_service(str(spec['service']),str(service_path))
        if actual!=service:raise ValueError('service differs from the prepared record')
        media=[]
        for item in spec.get('inputs') or []:
            path=item.get('path')
            if not isinstance(path,str) or not path:raise ValueError('submission input needs a path')
            rel,raw=pinned(root,directory,p,root/path)
            media.append({'spec_path':path,'path':rel,'sha256':c.digest(raw),'size':len(raw)})
        manifest={'spec':spec,'spec_path':spec_rel,'service':service,'service_path':service_rel,
                  'offering':offering,'gate':report,'media':media,'outputs':outputs}
        reserved=w._reserve(directory,p,rows,authorization=authorization,actor=actor,operation='submit',
                            scopes=['submission:'+str(spec['submission_id'])],outputs=outputs,
                            cost=cost,currency=currency,request_sha256=c.content_id(manifest))
        rows=w.load_run(root,run)[3]
        claim=w.append_record(directory,p,rows,'dispatch-claim',{'reservation':reserved['sha256'],
                         'manifest':manifest,'manifest_sha256':c.content_id(manifest)})
        return claim,manifest


def verify_trace(root: Path, run: str, claim: str) -> tuple[Path,dict,list[dict]]:
    directory,p,_,rows=w.load_run(root,run)
    wanted=w.find(rows,'dispatch-claim',claim)
    if c.content_id(wanted['data']['manifest'])!=wanted['data']['manifest_sha256']:
        raise ValueError('dispatch manifest mismatch')
    for row in rows:
        if row['event']=='dispatch-trace' and row['data']['claim']==claim:
            for f in row['data']['files']:
                if c.read(c.local(root,f['path']))!=c.object_read(directory,f['sha256']):
                    raise ValueError('dispatch trace was modified')
    return directory,wanted['data']['manifest'],rows


def obtain(root: Path, run: str, claim: str, transport: Any, key: str, *, poll: bool,
           poll_seconds: float, poll_limit: int) -> dict:
    directory,manifest,rows=verify_trace(root,run,claim)
    if any(r['event']=='dispatch-results' and r['data']['claim']==claim for r in rows):
        # Integrity still matters when bookkeeping is repeated.
        row=w.find(rows,'dispatch-results')
        for f in row['data']['files']:
            if c.read(c.local(root,f['path']))!=c.object_read(directory,f['sha256']):
                raise ValueError('acquired output was modified')
        for f in row['data']['files']:w.capture(root,run,f['path'],'Acquired from the recorded bounded submission; artistic review pending.')
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
    for path in files:w.capture(root,run,path,'Acquired from the recorded bounded submission; artistic review pending.')
    return result


def execute(root: Path, run: str, spec_path: Path, spec: dict, service_path: Path, service: dict,
            offering: dict, report: dict, transport: Any, key: str, **options: Any) -> dict:
    poll=bool(options.pop('poll',False));poll_seconds=options.pop('poll_seconds',20);poll_limit=options.pop('poll_limit',60)
    if not hasattr(transport,'describe_request'):
        raise ValueError('transport must describe actual primary text and explicit output count')
    preview=transport.build(spec,offering,service,{})
    meaning=transport.describe_request(preview,spec)
    if meaning!={'primary_text':spec.get('text'),'output_count':options.get('outputs')}:
        raise ValueError('actual request text or output count differs from the prepared bound')
    paths=transport.media_paths(spec,offering)
    if paths!=[x.get('path') for x in spec.get('inputs') or []]:
        raise ValueError('transport media set differs from the declared and prepared inputs')
    claim,manifest=begin(root,run,spec_path,spec,service_path,service,offering,report,**options)
    claim_id=claim['sha256'];directory=w.run_dir(root,run)
    append_trace(root,run,claim_id,'manifest.json',manifest)
    # All network-side files are private copies of the authorized snapshot, not mutable paths.
    with tempfile.TemporaryDirectory(prefix='submission-input-') as tmp:
        media_ids={}
        for i,source in enumerate(manifest['media']):
            path=Path(tmp)/(str(i)+Path(source['path']).suffix)
            path.write_bytes(c.object_read(directory,source['sha256']))
            media_ids[source['spec_path']]=transport.upload(str(path),service,key)
            append_trace(root,run,claim_id,f'upload-{i+1:03d}.json',{'source':source,'provider_id':media_ids[source['spec_path']]})
        request=transport.build(spec,offering,service,media_ids)
        if transport.describe_request(request,spec)!=meaning:raise ValueError('request changed during upload')
        append_trace(root,run,claim_id,'request.json',request)
        answer=transport.send(request,service,key)
        append_trace(root,run,claim_id,'answer.json',answer)
    return obtain(root,run,claim_id,transport,key,poll=poll,poll_seconds=poll_seconds,poll_limit=poll_limit)


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
