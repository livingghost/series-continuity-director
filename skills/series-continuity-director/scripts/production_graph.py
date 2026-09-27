#!/usr/bin/env python3
"""Validate a typed production dependency graph without creating another run ledger."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any
import execution_contract as c
from protocol_contract import validate_against_schema
from operation_log import operation
ROOT=Path(__file__).resolve().parents[1]

def check(plan:Any)->dict[str,Any]:
    schema=c.load(ROOT/'schemas/authoring/production-graph.schema.json');errors=validate_against_schema(plan,schema)
    if errors:raise ValueError('production graph: '+'; '.join(errors))
    nodes={};findings=[]
    for n in plan['nodes']:
        if n['id'] in nodes:raise ValueError('duplicate production graph node id')
        nodes[n['id']]=n
        if n['effect']=='external-write' and not n['authority_scopes']:
            findings.append({'node':n['id'],'code':'AUTHORITY_SCOPE_REQUIRED'})
        cost=n['cost']
        if cost['status'] in {'exact','bounded'} and (cost['amount'] is None or not cost['currency']):
            findings.append({'node':n['id'],'code':'COST_VALUE_REQUIRED'})
        if cost['status'] in {'unknown','not-applicable'} and (cost['amount'] is not None or cost['currency'] is not None):
            findings.append({'node':n['id'],'code':'COST_VALUE_NOT_APPLICABLE'})
    for n in nodes.values():
        unknown=set(n['depends_on'])-set(nodes)
        if unknown:findings.append({'node':n['id'],'code':'UNKNOWN_DEPENDENCY','dependencies':sorted(unknown)})
    visiting=set();done=set()
    def visit(key):
        if key in done:return
        if key in visiting:raise ValueError('production graph contains a dependency cycle')
        visiting.add(key)
        for dep in nodes[key]['depends_on']:
            if dep in nodes:visit(dep)
        visiting.remove(key);done.add(key)
    for key in nodes:visit(key)
    ready=[]
    for n in nodes.values():
        if n['state'] in {'complete','blocked'}:continue
        if all(nodes[d]['state']=='complete' for d in n['depends_on'] if d in nodes):ready.append(n['id'])
    return {'status':'pass' if not findings else 'blocked','ready_nodes':ready,'findings':findings,'limitations':plan['limitations'],
            'scope':'The graph plans dependencies only. Execution, authority, reservations, candidates and canon remain in the existing Production records.'}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['check']);p.add_argument('--root',type=Path,required=True);p.add_argument('--plan',required=True);a=p.parse_args();root=a.root.absolute()
    try:
        with operation('production_graph.check',root=root,arguments=vars(a)) as log:
            result=check(c.load(c.local(root,a.plan)));log.event('graph_checked',status=result['status'],ready=result['ready_nodes']);print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['status']=='pass' else 1
    except c.EXPECTED_ERRORS as exc:print(json.dumps(c.failure(exc),ensure_ascii=False));return 1
if __name__=='__main__':
    import stdio_utf8;stdio_utf8.configure();raise SystemExit(main())
