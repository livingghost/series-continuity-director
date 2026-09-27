#!/usr/bin/env python3
"""Verify and extract a boundary from an actually accepted media artifact."""
from __future__ import annotations
import argparse,json,tempfile
from pathlib import Path
from typing import Any
import execution_contract as c
import asset_registry, media_evidence, timed_sequence
from protocol_contract import validate_against_schema
from operation_log import operation
ROOT=Path(__file__).resolve().parents[1]

def check(root:Path, plan:Any)->dict[str,Any]:
    schema=c.load(ROOT/'schemas/authoring/boundary-conform.schema.json');errors=validate_against_schema(plan,schema)
    if errors:raise ValueError('boundary conform: '+'; '.join(errors))
    registry_path=c.local(root,plan['registry']);records=asset_registry.parse(c.read(registry_path).decode('utf-8'))
    matches=[r for r in records if r['id']==plan['asset_id']]
    if len(matches)!=1:raise ValueError('boundary asset id is not unique in the registry')
    record=matches[0]
    if record['fields'].get('status')!='accepted':raise ValueError('boundary source must be an accepted registry asset')
    source=c.local(root,plan['source']['path']);raw=c.read(source);sha=c.digest(raw)
    if sha!=plan['source']['sha256']:raise ValueError('boundary source content changed')
    if not asset_registry.binds(record,plan['source']['path'],sha):raise ValueError('accepted registry record does not bind the declared source bytes')
    media=media_evidence.inspect(source,raw)
    if media.get('kind')!='video':raise ValueError('boundary extraction requires actual video')
    duration=media.get('duration')
    if duration is None:raise ValueError('boundary source duration is unmeasured')
    t=float(plan['time_seconds']);w=float(plan['window_seconds'])
    if not 0<=t<duration:raise ValueError('boundary time lies outside the accepted source')
    return {'status':'pass','asset_id':plan['asset_id'],'source_sha256':sha,'media':media,'time_seconds':t,
            'window':{'start':max(0.0,t-w),'end':min(duration,t+w)},'limitations':plan['limitations'],
            'scope':'The accepted bytes and extraction position are verified; action continuity and performance quality require observation.'}

def extract(root:Path,plan:Any,out:str)->dict[str,Any]:
    report=check(root,plan);target=c.local(root,out,exists=False)
    receipt=timed_sequence.extract(root,plan['source']['path'],plan['source']['sha256'],out,start=plan['time_seconds'])
    return {'status':'pass','boundary':report,'extraction':receipt}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('check');q.add_argument('--root',type=Path,required=True);q.add_argument('--plan',required=True)
    q=sub.add_parser('extract');q.add_argument('--root',type=Path,required=True);q.add_argument('--plan',required=True);q.add_argument('--out',required=True)
    a=p.parse_args();root=a.root.absolute()
    try:
        with operation('boundary_conform.'+a.command,root=root,arguments=vars(a)) as log:
            plan=c.load(c.local(root,a.plan));result=check(root,plan) if a.command=='check' else extract(root,plan,a.out)
            log.event('boundary_checked',status='pass',asset_id=plan['asset_id']);print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except c.EXPECTED_ERRORS as exc:print(json.dumps(c.failure(exc),ensure_ascii=False));return 1
if __name__=='__main__':
    import stdio_utf8;stdio_utf8.configure();raise SystemExit(main())
