#!/usr/bin/env python3
"""Retain and publish the exact output of an already reserved operation.

Recovery writes only content-addressed bytes that were produced before the
interruption. It never rerenders, resubmits, grants permission or adopts assets.
"""
from __future__ import annotations
from pathlib import Path
import execution_contract as c
import production_authority as authority
import production_workflow as w


def _authorized(root: Path, prepared: dict, rows: list[dict], reservation: str) -> dict:
    saved=w.find(rows,'reservation',reservation)['data']
    request={k:v for k,v in saved.items() if k not in {'permission','authority_key'}}
    checked=authority.reservation(prepared,rows,history=w.permission_history(root,prepared),**request)
    if checked!=saved:raise ValueError('retained execution no longer matches its authority')
    if saved['operation'] not in {'edit','submit'} or saved['outputs']<1:
        raise ValueError('reservation permits no artifact')
    return saved


def retain(root: Path, run: str, reservation: str, contents: dict[str,bytes], primary: str,
           note: str, limitations: list[str]) -> dict:
    """Called by the producing operation under its own already acquired grant."""
    with c.lock(root):
        directory,prepared,_,rows=w.assert_current(root,run)
        _authorized(root,prepared,rows,reservation)
        if primary not in contents:raise ValueError('primary output is missing')
        pinned={d['path'] for d in prepared['dependencies'] if d['space']=='project'}
        pinned.update(f['path'] for row in rows for f in row['data'].get('files',[])+row['data'].get('evidence',[]))
        outputs=[]
        for relative,raw in contents.items():
            target=c.local(root,relative,exists=False)
            if relative in pinned or target.exists() or not raw or any(part.startswith('.') for part in Path(relative).parts) or Path(relative).parts[0]=='production':
                raise ValueError('retained outputs need new paths outside inputs and internal records')
            outputs.append({'path':relative,'sha256':c.object_store(directory,raw),'size':len(raw)})
        data={'reservation':reservation,'outputs':outputs,'primary':primary,'note':c.text(note,'provenance'),'limitations':limitations}
        existing=[r for r in rows if r['event']=='action-output' and r['data']['reservation']==reservation]
        if existing and existing[-1]['data']!=data:raise ValueError('reservation already retained different output')
        return w.append_record(directory,prepared,rows,'action-output',data)


def recover(root: Path, run: str, reservation: str) -> dict:
    with c.lock(root):
        directory,prepared,_,rows=w.assert_current(root,run)
        _authorized(root,prepared,rows,reservation)
        matches=[r for r in rows if r['event']=='action-output' and r['data']['reservation']==reservation]
        if len(matches)!=1:raise ValueError('no retained output; inspect the uncertain execution, do not rerun automatically')
        data=matches[0]['data']
        # Preflight every destination before publishing any of them.
        pending=[]
        for item in data['outputs']:
            target=c.local(root,item['path'],exists=False);raw=c.object_read(directory,item['sha256'])
            if len(raw)!=item['size']:raise ValueError('retained output size mismatch')
            if target.exists():
                if c.read(target)!=raw:raise ValueError('existing destination conflicts with retained output')
            else:pending.append((target,raw))
        for target,raw in pending:c.atomic(target,raw)
    return w.action_result(root,run,reservation,data['primary'],data['note'],
                           evidence=[f['path'] for f in data['outputs'] if f['path']!=data['primary']],
                           limitations=data['limitations'])
