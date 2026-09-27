#!/usr/bin/env python3
"""Validate and build deterministic planning/model/delivery boards."""
from __future__ import annotations
import argparse,json,html
from pathlib import Path
from typing import Any
import execution_contract as c
from protocol_contract import validate_against_schema
from operation_log import operation
ROOT=Path(__file__).resolve().parents[1]
def check(root:Path,plan:Any)->dict[str,Any]:
    schema=c.load(ROOT/'schemas/authoring/board-plan.schema.json');errors=validate_against_schema(plan,schema)
    if errors:raise ValueError('board plan: '+'; '.join(errors))
    ids=set();findings=[];sources=[]
    for u in plan['units']:
        if u['id'] in ids:raise ValueError('duplicate board unit id')
        ids.add(u['id']);b=u['bounds']
        if b['x']+b['width']>plan['width'] or b['y']+b['height']>plan['height']:findings.append({'unit':u['id'],'code':'BOARD_UNIT_OUTSIDE_CANVAS'})
        if plan['purpose']=='model-facing' and u['label'] and not u['include_annotation_in_model_input']:
            findings.append({'unit':u['id'],'code':'MODEL_ANNOTATION_SCOPE_CONFLICT'})
        if u['source'] is None:sources.append({'unit':u['id'],'state':'planned-not-observed'})
        else:
            p=c.local(root,u['source']['path']);raw=c.read(p)
            if c.digest(raw)!=u['source']['sha256']:findings.append({'unit':u['id'],'code':'BOARD_SOURCE_CHANGED'})
            sources.append({'unit':u['id'],'state':'observed','path':u['source']['path'],'sha256':c.digest(raw)})
    return {'status':'pass' if not findings else 'fail','purpose':plan['purpose'],'sources':sources,'findings':findings,'limitations':plan['limitations']}
def build_svg(root:Path,plan:Any,out:Path)->dict[str,Any]:
    report=check(root,plan)
    if report['status']!='pass':raise ValueError('board plan does not pass validation')
    if out.exists():raise ValueError('board output already exists')
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{plan["width"]}" height="{plan["height"]}" viewBox="0 0 {plan["width"]} {plan["height"]}">',f'<rect width="100%" height="100%" fill="{plan["background"]}"/>']
    for u in plan['units']:
        b=u['bounds'];parts.append(f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["width"]}" height="{b["height"]}" fill="none" stroke="black"/>')
        # SVG is a planning/delivery carrier, not proof that a linked raster was consumed by a model.
        if u['source'] is not None:
            href=html.escape(u['source']['path'],quote=True);parts.append(f'<image href="{href}" x="{b["x"]}" y="{b["y"]}" width="{b["width"]}" height="{b["height"]}" preserveAspectRatio="xMidYMid meet"/>')
        if u['label'] is not None and (plan['purpose']!='model-facing' or u['include_annotation_in_model_input']):
            label=html.escape(u['label']);parts.append(f'<text x="{b["x"]+6}" y="{b["y"]+18}" font-size="14">{label}</text>')
    parts.append('</svg>');raw=('\n'.join(parts)+'\n').encode('utf-8');c.atomic(out,raw)
    return {'status':'pass','path':out.relative_to(root).as_posix(),'sha256':c.digest(raw),'purpose':plan['purpose'],'sources':report['sources']}
def main()->int:
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('check');q.add_argument('--root',type=Path,required=True);q.add_argument('--plan',required=True)
    q=sub.add_parser('build-svg');q.add_argument('--root',type=Path,required=True);q.add_argument('--plan',required=True);q.add_argument('--out',required=True)
    a=p.parse_args();root=a.root.absolute()
    try:
        with operation('board_layout.'+a.command,root=root,arguments=vars(a)) as log:
            plan=c.load(c.local(root,a.plan));result=check(root,plan) if a.command=='check' else build_svg(root,plan,c.local(root,a.out,exists=False));log.event('board_completed',status=result['status']);print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['status']=='pass' else 1
    except c.EXPECTED_ERRORS as exc:print(json.dumps(c.failure(exc),ensure_ascii=False));return 1
if __name__=='__main__':
    import stdio_utf8;stdio_utf8.configure();raise SystemExit(main())
