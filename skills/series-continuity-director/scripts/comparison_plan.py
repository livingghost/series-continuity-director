#!/usr/bin/env python3
"""Validate comparison conditions and emit an evaluation-evidence study input."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any
import execution_contract as c
from protocol_contract import validate_against_schema
from operation_log import operation
ROOT=Path(__file__).resolve().parents[1]

def check(root:Path,plan:Any)->dict[str,Any]:
    schema=c.load(ROOT/'schemas/authoring/comparison-plan.schema.json');errors=validate_against_schema(plan,schema)
    if errors:raise ValueError('comparison plan: '+'; '.join(errors))
    cases={x['id'] for x in plan['cases']};conditions={x['id'] for x in plan['conditions']};trial_ids=set();runs=set();findings=[];evidence=[]
    for t in plan['trials']:
        if t['id'] in trial_ids:raise ValueError('duplicate comparison trial id')
        trial_ids.add(t['id'])
        if t['case'] not in cases or t['condition'] not in conditions:findings.append({'trial':t['id'],'code':'COMPARISON_REFERENCE_UNKNOWN'})
        if t['run'] is not None:
            if t['run'] in runs:findings.append({'trial':t['id'],'code':'COMPARISON_RUN_REUSED'})
            runs.add(t['run'])
        elif t['candidate'] is not None or t['measurements'] is not None:
            findings.append({'trial':t['id'],'code':'NOT_RUN_TRIAL_HAS_RESULT'})
        cost=t['cost']
        if cost['status'] in {'exact','bounded'} and (cost['amount'] is None or not cost['currency']):findings.append({'trial':t['id'],'code':'COST_VALUE_REQUIRED'})
        if cost['status'] in {'unknown','not-applicable'} and (cost['amount'] is not None or cost['currency'] is not None):findings.append({'trial':t['id'],'code':'COST_VALUE_NOT_APPLICABLE'})
        for role in ('temporal_evidence','audio_evidence','delivery_evidence'):
            for item in t[role]:
                p=c.local(root,item['path']);raw=c.read(p);actual=c.digest(raw);ok=actual==item['sha256'];evidence.append({'trial':t['id'],'role':role,'path':item['path'],'sha256':actual,'ok':ok})
                if not ok:findings.append({'trial':t['id'],'code':'COMPARISON_EVIDENCE_CHANGED','path':item['path']})
    return {'status':'pass' if not findings else 'fail','strategy':plan['strategy'],'findings':findings,'evidence':evidence,
            'scope':'Comparison planning only. Recorded Production reviews remain the judgment evidence and candidates from one run are not independent repeated trials.'}

def build_study(root:Path,plan:Any,out:Path)->dict[str,Any]:
    report=check(root,plan)
    if report['status']!='pass':raise ValueError('comparison plan does not pass validation')
    if out.exists():raise ValueError('comparison study output already exists')
    study={'purpose':plan['purpose'],'cases':plan['cases'],'conditions':plan['conditions'],'trials':[{k:t[k] for k in ('id','case','condition','run','candidate','measurements')} for t in plan['trials']]}
    raw=c.encoded(study);c.atomic(out,raw)
    return {'status':'pass','study':out.relative_to(root).as_posix(),'study_sha256':c.digest(raw),'strategy':plan['strategy'],'evidence':report['evidence']}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('check');q.add_argument('--root',type=Path,required=True);q.add_argument('--plan',required=True)
    q=sub.add_parser('build-study');q.add_argument('--root',type=Path,required=True);q.add_argument('--plan',required=True);q.add_argument('--out',required=True)
    a=p.parse_args();root=a.root.absolute()
    try:
        with operation('comparison_plan.'+a.command,root=root,arguments=vars(a)) as log:
            plan=c.load(c.local(root,a.plan));result=check(root,plan) if a.command=='check' else build_study(root,plan,c.local(root,a.out,exists=False));log.event('comparison_plan_completed',status=result['status']);print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['status']=='pass' else 1
    except c.EXPECTED_ERRORS as exc:print(json.dumps(c.failure(exc),ensure_ascii=False));return 1
if __name__=='__main__':
    import stdio_utf8;stdio_utf8.configure();raise SystemExit(main())
