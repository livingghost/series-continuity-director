#!/usr/bin/env python3
"""A reviewed, scoped change creates a new production run, not inherited success."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import execution_contract as c
import production_workflow as w


def assert_context(root: Path, run: str) -> tuple:
    loaded=w.load_run(root,run)
    directory,prepared,_,rows=loaded
    for dependency in prepared['dependencies']:
        if dependency['space']=='skill' and c.digest(c.read(c.local(w.ROOT,dependency['path'])))!=dependency['sha256']:
            raise ValueError('implementation changed; prepare from current contracts')
    for row in rows:
        for item in row['data'].get('files',[])+row['data'].get('evidence',[]):
            if c.read(c.local(root,item['path']))!=c.object_read(directory,item['sha256']):
                raise ValueError('recorded approval, candidate or review changed')
    return loaded


def latest_review(rows: list[dict], candidate: str) -> dict:
    matches=[r for r in rows if r['event']=='review' and r['data']['candidate']==candidate]
    if not matches:raise ValueError('the candidate has no review')
    return matches[-1]


def changed_scopes(before: dict, after: dict, old_blobs: dict[str,bytes], new_blobs: dict[str,bytes]) -> list[str]:
    old,new=before['task'],after['task'];scopes=set()
    old_deps={d['path']:d['sha256'] for d in before['dependencies'] if d['space']=='project'}
    new_deps={d['path']:d['sha256'] for d in after['dependencies'] if d['space']=='project'}
    if old['delivery']!=new['delivery'] or old_deps[old['delivery']['path']]!=new_deps[new['delivery']['path']]:scopes.add('delivery')
    for field,prefix in (('sources','source:'),('criteria','criterion:')):
        a={x['id']:x for x in old[field]};b={x['id']:x for x in new[field]}
        for key in a.keys()|b.keys():
            if a.get(key)!=b.get(key) or (field=='sources' and key in a and key in b and old_deps[a[key]['path']]!=new_deps[b[key]['path']]):
                scopes.add(prefix+key)
    a={x['id']:x for x in old['direction']['decisions']};b={x['id']:x for x in new['direction']['decisions']}
    scopes.update('decision:'+key for key in a.keys()|b.keys() if a.get(key)!=b.get(key))
    if {k:v for k,v in old['direction'].items() if k!='decisions'}!={k:v for k,v in new['direction'].items() if k!='decisions'}:scopes.add('purpose')
    if any(old[k]!=new[k] for k in ('route','features')):scopes.add('execution')
    first,last=old['sequence_plan'],new['sequence_plan']
    if first is None or last is None:
        if first!=last:scopes.add('sequence')
    else:
        a=c.decode(old_blobs[old_deps[first]]);b=c.decode(new_blobs[new_deps[last]])
        for key in a.keys()|b.keys():
            if a.get(key)==b.get(key):continue
            if key in {'assets','cues','placements','clocks'}:
                aa={x['id']:x for x in a[key]};bb={x['id']:x for x in b[key]}
                prefix={'assets':'asset','cues':'cue','placements':'placement','clocks':'clock'}[key]
                scopes.update(prefix+':'+ident for ident in aa.keys()|bb.keys() if aa.get(ident)!=bb.get(ident))
            else:scopes.add('sequence:'+key)
    return sorted(scopes)


def revision_intent(root: Path, run: str, task: str, candidate: str, repair_index: int) -> dict:
    directory,prepared,_,rows=assert_context(root,run)
    w.find(rows,'candidate',candidate);reviewed=latest_review(rows,candidate)
    repairs=reviewed['data']['review']['repairs']
    if type(repair_index) is not int or not 0<=repair_index<len(repairs):
        raise ValueError('repair index must select an actual proposal in the latest review')
    revised,_,_,blobs=w.snapshot(root,task)
    if revised['task']['task_id']!=prepared['task']['task_id']:
        raise ValueError('a revision cannot move to another work task')
    old_blobs={d['sha256']:c.object_read(directory,d['sha256']) for d in prepared['dependencies']}
    scopes=changed_scopes(prepared,revised,old_blobs,blobs)
    if not scopes:raise ValueError('no production inputs changed')
    if set(scopes)-set(repairs[repair_index]['targets']):
        raise ValueError('revision exceeds the reviewed repair targets: '+', '.join(scopes))
    return {'parent_run':run,'candidate':candidate,'review':reviewed['sha256'],'repair_index':repair_index,
            'targets':scopes,'prepared_sha256':revised['input_sha256']}


def revise(root: Path, run: str, task: str, candidate: str, repair_index: int,
           authorization: str, actor: str) -> dict:
    with c.lock(root):
        directory,prepared,_,rows=assert_context(root,run);w.require_mutable(rows)
        intent=revision_intent(root,run,task,candidate,repair_index)
        grant=w.find(rows,'authorization',authorization)['data']['authorization']
        if {'source:'+x for x in grant['preserve_sources']}&set(intent['targets']):
            raise ValueError('revision changes a protected source; obtain specific new authority')
        reserved=w._reserve(directory,prepared,rows,authorization=authorization,actor=actor,operation='edit',
                            scopes=intent['targets'],request_sha256=c.content_id(intent),outputs=0)
        rows=w.load_run(root,run)[3]
        previous=[r for r in rows if r['event']=='revision' and r['data']['reservation']==reserved['sha256']]
        if previous:
            record=previous[-1]
            if record['data']['intent']!=intent:raise ValueError('reservation already belongs to another revision')
        else:
            record=w.append_record(directory,prepared,rows,'revision',
                                   {'intent':intent,'reservation':reserved['sha256'],'child':c.new_run_id()})
        parent={**intent,'reservation':reserved['sha256'],'revision':record['sha256']}
        return w._prepare(root,task,parent=parent,identity=record['data']['child'])
