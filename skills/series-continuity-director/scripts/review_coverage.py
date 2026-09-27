#!/usr/bin/env python3
"""Check what temporal evidence was actually reviewed without inventing quality."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any
import execution_contract as c
import media_evidence
from protocol_contract import validate_against_schema
from operation_log import operation
ROOT=Path(__file__).resolve().parents[1]

def check(root:Path, plan:Any)->dict[str,Any]:
    schema=c.load(ROOT/'schemas/authoring/review-coverage.schema.json');errors=validate_against_schema(plan,schema)
    if errors:raise ValueError('review coverage: '+'; '.join(errors))
    path=c.local(root,plan['artifact']['path']);raw=c.read(path)
    if c.digest(raw)!=plan['artifact']['sha256']:raise ValueError('review artifact changed')
    media=media_evidence.inspect(path,raw);duration=media.get('duration');findings=[];coverage=[]
    ids=set()
    for o in plan['observations']:
        if o['id'] in ids:raise ValueError('duplicate observation id')
        ids.add(o['id'])
        if not 0<=o['start']<=o['end']:raise ValueError('observation interval is invalid')
        if duration is not None and o['end']>duration+1e-6:findings.append({'code':'OBSERVATION_OUTSIDE_MEDIA','observation':o['id']})
    for req in plan['requirements']:
        if not 0<=req['start']<=req['end']:raise ValueError('review requirement interval is invalid')
        if duration is not None and req['end']>duration+1e-6:findings.append({'code':'REVIEW_REQUIREMENT_OUTSIDE_MEDIA','requirement':req['id']})
        matches=[o for o in plan['observations'] if o['result'] not in {'not-assessed'} and o['start']<=req['start'] and o['end']>=req['end']]
        if req['kind']=='full-playback':
            matches=[o for o in matches if o['method'] in {'full-playback','human-observation','agent-observation'}]
        covered=bool(matches);coverage.append({'requirement':req['id'],'covered':covered,'observations':[o['id'] for o in matches]})
        if not covered:findings.append({'code':'REVIEW_COVERAGE_INCOMPLETE','requirement':req['id']})
    return {'status':'pass' if not findings else 'incomplete','artifact_media':media,'coverage':coverage,'findings':findings,'limitations':plan['limitations'],
            'scope':'Coverage reports observed intervals and methods; unobserved time is not certified by sampling.'}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['check']);p.add_argument('--root',type=Path,required=True);p.add_argument('--plan',required=True);a=p.parse_args();root=a.root.absolute()
    try:
        with operation('review_coverage.check',root=root,arguments=vars(a)) as log:
            result=check(root,c.load(c.local(root,a.plan)));log.event('coverage_checked',status=result['status'])
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['status']=='pass' else 1
    except c.EXPECTED_ERRORS as exc:print(json.dumps(c.failure(exc),ensure_ascii=False));return 1
if __name__=='__main__':
    import stdio_utf8;stdio_utf8.configure();raise SystemExit(main())
