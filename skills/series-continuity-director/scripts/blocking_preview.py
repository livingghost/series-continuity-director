#!/usr/bin/env python3
"""Build a bounded 2D blocking proxy from declared geometry only."""
from __future__ import annotations
import argparse,html,json
from pathlib import Path
from typing import Any
import execution_contract as c
from protocol_contract import validate_against_schema
from operation_log import operation
ROOT=Path(__file__).resolve().parents[1]
def check(plan:Any)->dict[str,Any]:
    schema=c.load(ROOT/'schemas/authoring/blocking-preview.schema.json');errors=validate_against_schema(plan,schema)
    if errors:raise ValueError('blocking preview: '+'; '.join(errors))
    ids=set();findings=[]
    for o in plan['objects']:
        if o['id'] in ids:raise ValueError('duplicate blocking object id')
        ids.add(o['id'])
        if o['x']<0 or o['y']<0 or o['x']+o['width']>plan['width'] or o['y']+o['height']>plan['height']:
            findings.append({'object':o['id'],'code':'BLOCKING_OBJECT_OUTSIDE_FRAME'})
    return {'status':'pass' if not findings else 'fail','findings':findings,'unknown':[o['id'] for o in plan['objects'] if o['knowledge']=='unknown'],'assumed':[o['id'] for o in plan['objects'] if o['knowledge']=='assumed'],'limitations':plan['limitations']}
def build(plan:Any,out:Path)->dict[str,Any]:
    report=check(plan)
    if report['status']!='pass':raise ValueError('blocking preview does not pass validation')
    if out.exists():raise ValueError('blocking output already exists')
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{plan["width"]}" height="{plan["height"]}" viewBox="0 0 {plan["width"]} {plan["height"]}">','<rect width="100%" height="100%" fill="white"/>']
    for o in plan['objects']:
        shape='rect' if o['shape']=='rect' else 'ellipse';label=html.escape(o['label']);dash=' stroke-dasharray="6 4"' if o['knowledge']!='declared' else ''
        if shape=='rect':parts.append(f'<rect x="{o["x"]}" y="{o["y"]}" width="{o["width"]}" height="{o["height"]}" fill="none" stroke="black"{dash}/>')
        else:parts.append(f'<ellipse cx="{o["x"]+o["width"]/2}" cy="{o["y"]+o["height"]/2}" rx="{o["width"]/2}" ry="{o["height"]/2}" fill="none" stroke="black"{dash}/>')
        parts.append(f'<text x="{o["x"]}" y="{max(12,o["y"]-3)}" font-size="12">{label} [{o["knowledge"]}]</text>')
    parts.append(f'<text x="8" y="{plan["height"]-8}" font-size="11">camera: {html.escape(plan["camera"]["label"])}</text>');parts.append('</svg>')
    raw=('\n'.join(parts)+'\n').encode();c.atomic(out,raw);return {'status':'pass','sha256':c.digest(raw),'unknown':report['unknown'],'assumed':report['assumed'],'scope':'A geometry proxy only; it does not establish unobserved anatomy, performance or canon.'}
def main()->int:
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('check');q.add_argument('--root',type=Path,required=True);q.add_argument('--plan',required=True)
    q=sub.add_parser('build-svg');q.add_argument('--root',type=Path,required=True);q.add_argument('--plan',required=True);q.add_argument('--out',required=True)
    a=p.parse_args();root=a.root.absolute()
    try:
        with operation('blocking_preview.'+a.command,root=root,arguments=vars(a)) as log:
            plan=c.load(c.local(root,a.plan));result=check(plan) if a.command=='check' else build(plan,c.local(root,a.out,exists=False));log.event('blocking_completed',status=result['status']);print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['status']=='pass' else 1
    except c.EXPECTED_ERRORS as exc:print(json.dumps(c.failure(exc),ensure_ascii=False));return 1
if __name__=='__main__':
    import stdio_utf8;stdio_utf8.configure();raise SystemExit(main())
