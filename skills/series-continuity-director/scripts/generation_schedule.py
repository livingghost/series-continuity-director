#!/usr/bin/env python3
"""Check pre-generation lane, duration, reference and edit feasibility.

This module proves structural compatibility only. It does not claim that a
planned performance will be produced or that a request is authorized.
"""
from __future__ import annotations
import argparse, json
from fractions import Fraction
from pathlib import Path
from typing import Any
import execution_contract as c
from protocol_contract import validate_against_schema
from operation_log import operation

ROOT = Path(__file__).resolve().parents[1]


def _q(value: Any, label: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(label + ': finite number required')
    return Fraction(str(value))


def _edit_seconds(value: Any, clock: dict[str, Any]) -> Fraction:
    q = _q(value, 'edit coordinate')
    if clock['unit'] == 'seconds':
        return q
    rate = Fraction(clock['rate']['numerator'], clock['rate']['denominator'])
    if q.denominator != 1:
        raise ValueError('frame coordinates must be integers')
    return q / rate


def _duration_allowed(seconds: Fraction, rule: dict[str, Any]) -> bool:
    if rule['kind'] == 'not-applicable':
        return seconds == 0
    if rule['kind'] == 'discrete':
        return any(seconds == _q(v, 'duration') for v in rule['values'])
    lo = _q(rule['minimum'], 'minimum duration')
    hi = _q(rule['maximum'], 'maximum duration')
    step = _q(rule['step'], 'duration step')
    return lo <= seconds <= hi and ((seconds - lo) / step).denominator == 1


def validate(plan: Any) -> dict[str, Any]:
    schema = c.load(ROOT / 'schemas/authoring/generation-schedule.schema.json')
    errors = validate_against_schema(plan, schema)
    if errors:
        raise ValueError('generation schedule: ' + '; '.join(errors))
    clock = plan['edit_clock']
    if clock['unit'] == 'frames' and clock['rate'] is None:
        raise ValueError('frame edit clock requires an explicit rational rate')
    if clock['unit'] == 'seconds' and clock['rate'] is not None:
        raise ValueError('seconds edit clock does not take a frame rate')
    target_start = _edit_seconds(plan['target_edit_span']['start'], clock)
    target_end = _edit_seconds(plan['target_edit_span']['end'], clock)
    if not 0 <= target_start < target_end:
        raise ValueError('target edit span must be nonnegative and half-open [start,end)')
    ids=set(); findings=[]; unresolved=list(plan['unresolved'])
    contract = plan['reference_contract']
    allowed_roles=set(contract['roles'])
    exclusive=[set(x) for x in contract['exclusive_role_sets']]
    intervals=[]
    for unit in plan['units']:
        if unit['id'] in ids: raise ValueError('duplicate generation unit id')
        ids.add(unit['id'])
        start=_edit_seconds(unit['edit']['start'],clock); end=_edit_seconds(unit['edit']['end'],clock)
        if not target_start <= start < end <= target_end:
            findings.append({'unit':unit['id'],'code':'EDIT_SPAN_OUTSIDE_TARGET'})
        intervals.append((start,end,unit['id']))
        rate=_q(unit['playback_rate'],'playback rate')
        if rate <= 0: findings.append({'unit':unit['id'],'code':'PLAYBACK_RATE_INVALID'})
        roles=unit['reference_roles']
        if len(roles)>contract['maximum']:
            findings.append({'unit':unit['id'],'code':'REFERENCE_LIMIT_EXCEEDED'})
        unknown=set(roles)-allowed_roles
        if unknown: findings.append({'unit':unit['id'],'code':'REFERENCE_ROLE_UNSUPPORTED','roles':sorted(unknown)})
        for group in exclusive:
            used=group & set(roles)
            if len(used)>1: findings.append({'unit':unit['id'],'code':'REFERENCE_MODE_CONFLICT','roles':sorted(used)})
        if plan['lane']=='edit-existing-media':
            if unit['generation_seconds'] is not None:
                findings.append({'unit':unit['id'],'code':'GENERATION_NOT_APPLICABLE'})
        else:
            if unit['generation_seconds'] is None:
                findings.append({'unit':unit['id'],'code':'GENERATION_DURATION_REQUIRED'})
            else:
                gs=_q(unit['generation_seconds'],'generation duration')
                if not _duration_allowed(gs,plan['generation_duration']):
                    findings.append({'unit':unit['id'],'code':'GENERATION_DURATION_UNSUPPORTED','seconds':float(gs)})
                if unit['source_use'] is not None:
                    ss=_q(unit['source_use']['start'],'source use start'); se=_q(unit['source_use']['end'],'source use end')
                    if not 0 <= ss < se:
                        findings.append({'unit':unit['id'],'code':'SOURCE_USE_INVALID'})
                    else:
                        edit_len=end-start
                        if (se-ss)/rate != edit_len:
                            findings.append({'unit':unit['id'],'code':'SOURCE_EDIT_DURATION_MISMATCH'})
                        required = se + _q(unit['post_handle'],'post handle')
                        if ss < _q(unit['pre_handle'],'pre handle'):
                            findings.append({'unit':unit['id'],'code':'PRE_HANDLE_UNAVAILABLE'})
                        if gs < required:
                            findings.append({'unit':unit['id'],'code':'POST_HANDLE_UNAVAILABLE'})
                elif unit['cues']:
                    unresolved.append(f"{unit['id']}: actual source span is needed to establish cue coverage")
    # Only independent shots may overlap by default. Other lanes need an explicit editing decision.
    for (a,b,aid),(x,y,xid) in zip(sorted(intervals), sorted(intervals)[1:]):
        if x < b and plan['lane'] in {'endpoint-conditioned-chain','single-generated-sequence'}:
            findings.append({'unit':xid,'code':'GENERATION_LANE_UNSATISFIED','detail':f'overlaps {aid}'})
    blocking=[x for x in findings if x['code'] not in set()]
    if blocking:
        status='blocked-contract'
    elif unresolved:
        status='needs-media'
    elif plan['assumptions']:
        status='needs-decision'
    else:
        status='structurally-feasible'
    generation_total=sum((_q(x['generation_seconds'],'generation duration') for x in plan['units'] if x['generation_seconds'] is not None),Fraction(0))
    return {
        'status':status,
        'lane':plan['lane'],
        'edit_seconds':float(target_end-target_start),
        'planned_generation_seconds':float(generation_total),
        'findings':findings,
        'assumptions':plan['assumptions'],
        'unresolved':unresolved,
        'scope':'Structural feasibility only; actual performance, media quality, authority and provider execution remain unobserved.'
    }


def main()->int:
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    for name in ('check','explain'):
        q=sub.add_parser(name); q.add_argument('--root',type=Path,required=True); q.add_argument('--plan',required=True)
    a=p.parse_args(); root=a.root.absolute()
    try:
        with operation('generation_schedule.'+a.command,root=root,arguments=vars(a)) as log:
            result=validate(c.load(c.local(root,a.plan)))
            log.event('schedule_checked',status=result['status'],findings=len(result['findings']))
            print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result['status']!='blocked-contract' else 1
    except c.EXPECTED_ERRORS as exc:
        print(json.dumps(c.failure(exc),ensure_ascii=False)); return 1
if __name__=='__main__':
    import stdio_utf8; stdio_utf8.configure(); raise SystemExit(main())
