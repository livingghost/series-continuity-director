"""Derive reservation state from immutable receipts and fence external effects."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import execution_contract as c

EVENTS = {'reservation-start','reservation-release','external-step'}
TOKEN_FIELD = 'reservation_sha256'
RESERVATION_EVENT = 'reservation'


def selector(run: str, token: str) -> dict:
    c.sha(token)
    return {'run':run, TOKEN_FIELD:token}


def token_of(value: Any, run: str) -> str:
    c.exact(value, {'run',TOKEN_FIELD}, 'reservation selector')
    if value['run'] != run: raise ValueError('reservation belongs to another run')
    return c.sha(value[TOKEN_FIELD])


def original(data: dict, prepared: dict, previous: dict) -> dict:
    from production_authority import money,count
    authorization=previous.get(c.sha(data['authorization']))
    if authorization is None or authorization['event']!='authorization':raise ValueError('reservation has no preceding authorization')
    grant=authorization['data']['authorization'];index=data['permission']
    if type(index) is not int or not 0<=index<len(grant['permissions']):raise ValueError('reservation names an absent permission')
    permission=grant['permissions'][index]
    if data['actor']!=grant['actor'] or data['operation']!=permission['operation'] or data['authority_key']!=authorization['data']['authority_key']:
        raise ValueError('reservation identity differs from its authorization')
    count(data['outputs'],'reserved outputs');money(data['cost']);c.sha(data['request_sha256'])
    return {'actor':data['actor'],'operation':data['operation'],'request_sha256':data['request_sha256'],
        'release_actors':sorted({grant['principal'],grant['actor']}),
        'accounting_identity':{'task_id':prepared['task']['task_id'],'authority_key':data['authority_key'],'permission':index},
        'amounts':{'calls':1,'outputs':data['outputs'],'cost':data['cost'],'currency':data['currency']}}


def claim_owns(record: dict, token: str) -> bool:
    return record['event']=='dispatch-claim' and record['data']['reservation']==token


def used_by(record: dict, previous: dict) -> list[str]:
    event,data=record['event'],record['data']
    if event in {'selection','choice','action-result','revision','action-output'}:
        token=data.get('reservation')
        return [token] if token is not None else []
    if event=='dispatch-results':
        claim=previous.get(data.get('claim'))
        if claim is None:raise ValueError('effect names no preceding dispatch claim')
        return [claim['data']['reservation']]
    return []


def accounting(root: Path, prepared: dict) -> list[dict]:
    import production_workflow as w
    history=w.permission_history(root,prepared)
    released={r['data']['reservation']['reservation_sha256'] for r in history if r['event']=='reservation-release'}
    return [r['data'] for r in history if r['event']=='reservation' and r['sha256'] not in released]



def derive(records: list[dict], prepared: dict, run: str) -> dict[str,dict]:
    """Validate transitions and compute amounts from the original reservation."""
    states = {}; by_hash = {}
    for record in records:
        event, data = record['event'], record['data']
        if event == RESERVATION_EVENT:
            attributes = original(data, prepared, by_hash)
            states[record['sha256']] = {**attributes, 'reservation':selector(run,record['sha256']),
                'original_sha256':record['sha256'], 'status':'reserved', 'start':None, 'release':None, 'steps':[]}
        elif event in EVENTS:
            token = token_of(data['reservation'],run)
            state = states.get(token)
            if state is None: raise ValueError('reservation event precedes its original receipt')
            if event == 'reservation-start':
                c.exact(data,{'reservation','claim','operation','effect','request_sha256'},'reservation start')
                if state['status'] != 'reserved': raise ValueError('reservation may start exactly once before release')
                if data['operation'] != state['operation'] or data['request_sha256'] != state['request_sha256']:
                    raise ValueError('start differs from the reserved operation or request')
                if data['effect'] not in {'external-io','external-handoff','local-action'}: raise ValueError('unknown start effect')
                if data['claim'] is not None:
                    claim=by_hash.get(c.sha(data['claim']))
                    if claim is None or not claim_owns(claim,token): raise ValueError('start claim does not own this reservation')
                state.update(status='started',start=record['sha256'])
            elif event == 'reservation-release':
                c.exact(data,{'reservation','request','original_sha256','amounts','files'},'reservation release')
                if state['status'] != 'reserved': raise ValueError('only an unstarted reservation can be released')
                if data['original_sha256'] != token or data['amounts'] != state['amounts']:
                    raise ValueError('release amount or original reservation differs')
                request=data['request'];validate_release_request(request)
                if request['reservation'] != data['reservation'] or request['actor'] not in state['release_actors']:
                    raise ValueError('release request does not identify this reservation and authorized actor')
                if not any(f['path']==request['evidence']['path'] and f['sha256']==request['evidence']['sha256'] for f in data['files']):
                    raise ValueError('release evidence is not stored in the receipt')
                state.update(status='released',release=record['sha256'])
            else:
                c.exact(data,{'reservation','start','claim','step','operation','request_sha256'},'external step')
                if state['status'] != 'started' or data['start'] != state['start']: raise ValueError('external step needs the live start boundary')
                if data['claim'] != by_hash[state['start']]['data']['claim']: raise ValueError('external step changes its claim')
                if data['request_sha256'] != state['request_sha256']: raise ValueError('external step changes its reserved request')
                if data['operation'] not in {'upload','send'}: raise ValueError('unknown external step operation')
                c.text(data['step'],'external step ID')
                if any(x['step']==data['step'] for x in state['steps']): raise ValueError('external step was already begun')
                state['steps'].append(data)
        else:
            for token in used_by(record,by_hash):
                if token not in states or states[token]['status'] != 'started':
                    raise ValueError('effect receipt requires a started, unreleased reservation')
        by_hash[record['sha256']]=record
    return states


def require_active(records: list[dict], prepared: dict, run: str, token: str) -> dict:
    state=derive(records,prepared,run).get(c.sha(token))
    if state is None: raise ValueError('unknown reservation receipt')
    if state['status']=='released': raise ValueError('reservation was released; prepare a new run for another execution')
    return state


def begin(root: Path, run: str, token: str, *, effect: str, claim: str | None = None) -> dict:
    """Commit the boundary before returning permission to the current call only."""
    import production_workflow as w
    with c.lock(root):
        directory,p,_,rows=w.load_run(root,run)
        state=require_active(rows,p,run,token)
        if state['status']!='reserved': raise ValueError('operation already started; recover existing evidence instead of repeating it')
        data={'reservation':selector(run,token),'claim':claim,'operation':state['operation'],
              'effect':effect,'request_sha256':state['request_sha256']}
        return w.append_record(directory,p,rows,'reservation-start',data)


def begin_step(root: Path, run: str, token: str, *, claim: str, step: str, operation: str) -> dict:
    """Serialize release against the first upload or send and fence each step."""
    import production_workflow as w
    with c.lock(root):
        directory,p,_,rows=w.assert_current(root,run)
        state=require_active(rows,p,run,token)
        reserved=w.find(rows,'reservation',token)['data']
        import production_authority
        production_authority.reservation(p,rows,history=w.permission_history(root,p),
            **{k:reserved[k] for k in ('authorization','actor','operation','scopes','request_sha256','outputs','cost','currency')})
        if state['status']=='reserved':
            begin(root,run,token,effect='external-io',claim=claim)
            directory,p,_,rows=w.load_run(root,run);state=require_active(rows,p,run,token)
        if any(x['step']==step for x in state['steps']): raise ValueError('external step already started; automatic resubmission is forbidden')
        data={'reservation':selector(run,token),'start':state['start'],'claim':claim,'step':step,
              'operation':operation,'request_sha256':state['request_sha256']}
        return w.append_record(directory,p,rows,'external-step',data)


def validate_release_request(request: Any) -> None:
    c.exact(request,{'reservation','actor','evidence','reason'},'release request')
    c.text(request['actor'],'release actor');c.text(request['reason'],'release reason')
    c.exact(request['evidence'],{'path','sha256','locator'},'release evidence')
    c.text(request['evidence']['path'],'release evidence path');c.text(request['evidence']['locator'],'release evidence locator');c.sha(request['evidence']['sha256'])


def release(root: Path, run: str, request_file: str) -> dict:
    """Cancel an unused reservation without reviving expired or revoked authority."""
    import production_workflow as w
    with c.lock(root):
        directory,p,_,rows=w.load_run(root,run)
        request=c.load(c.local(root,request_file));validate_release_request(request)
        token=token_of(request['reservation'],run);states=derive(rows,p,run)
        state=states.get(token)
        if state is None: raise ValueError('release names no reservation in this run')
        if request['actor'] not in state['release_actors']: raise ValueError('actor cannot release this reservation')
        if state['status']=='released':
            record=next(r for r in rows if r['sha256']==state['release'])
            return {'released':True,'receipt':record,'reservations':accounting(root,p)}
        if state['status']!='reserved': raise ValueError('reservation crossed its start boundary and cannot be released')
        evidence=request['evidence'];raw=c.read(c.local(root,evidence['path']))
        if c.digest(raw)!=evidence['sha256']:raise ValueError('release evidence bytes changed')
        files=[w.file_record(root,directory,request_file),w.file_record(root,directory,evidence['path'])]
        data={'reservation':request['reservation'],'request':request,'original_sha256':token,
              'amounts':state['amounts'],'files':files}
        record=w.append_record(directory,p,rows,'reservation-release',data)
        return {'released':True,'receipt':record,'reservations':accounting(root,p)}


def draft_release(root: Path, run: str, token: str) -> dict:
    import production_workflow as w
    _,p,_,rows=w.load_run(root,run);states=derive(rows,p,run)
    state=states.get(c.sha(token))
    if state is None:raise ValueError('unknown reservation')
    return {'state':'draft','request':{'reservation':selector(run,token),'actor':'',
        'evidence':{'path':'','sha256':'','locator':''},'reason':''},
        'release_eligible':state['status']=='reserved','amounts':state['amounts'],
        'execution_state':state['status'],'boundary_receipt':state['start'],
        'unresolved':['actor','evidence','reason']}


def completion_tail(records: list[dict], prepared: dict, run: str) -> None:
    derive(records,prepared,run)
    completions=[r for r in records if r['event']=='completion']
    if not completions:return
    if len(completions)!=1:raise ValueError('completion is not unique')
    after=[r for r in records if r['sequence']>completions[0]['sequence']]
    if any(r['event']!='reservation-release' for r in after):raise ValueError('only an unused reservation release may follow completion')


def commit_effect(root: Path, run: str, event: str, data: dict, tokens: list[str], *, effect: str) -> dict:
    """Start each selected authorization before publishing an effect receipt."""
    import production_workflow as w
    with c.lock(root):
        directory,p,_,rows=w.load_run(root,run)
        previous=[r for r in rows if r['event']==event and r['data']==data]
        if previous:
            for token in tokens:require_active(rows,p,run,token)
            return previous[-1]
        for token in tokens:
            begin(root,run,token,effect=effect)
        directory,p,_,rows=w.load_run(root,run)
        return w.append_record(directory,p,rows,event,data)
