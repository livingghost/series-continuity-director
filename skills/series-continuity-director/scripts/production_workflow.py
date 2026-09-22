#!/usr/bin/env python3
"""Bind preparation, handoff, exact artifacts, review, selection and completion.

This is a local evidence workflow, not an autonomous artistic evaluator. It
never invents an observation, approval or remote result. Run each command with
--help; examples/production-execution/run_example.py is a synthetic CLI example.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

import execution_contract as c
import reservation_lifecycle as lifecycle
import execution_routes
import production_direction
import production_authority
import media_evidence
from execution_contract import new_run_id as generate_uuid7

ROOT = Path(__file__).resolve().parents[1]
TASK_FIELDS = {'route_reading','task_id','route','features','sources','delivery','criteria','sequence_plan','direction'}


def run_dir(root: Path, run: str, *, exists: bool = True) -> Path:
    try:
        identifier = uuid.UUID(run)
    except (ValueError,AttributeError) as exc:
        raise ValueError('run must be a UUIDv7') from exc
    if identifier.version != 7 or str(identifier) != run:
        raise ValueError('run must be a canonical UUIDv7')
    return c.local(root,'production/'+run,exists=exists)


def schema_check(value: Any, name: str) -> None:
    if name=='review' and isinstance(value,dict) and isinstance(value.get('checks'),list):
        if any(isinstance(x,dict) and x.get('verdict')=='fail' for x in value['checks']) and value.get('repairs')==[] and value.get('unresolved')==[]:
            raise ValueError('a failed review needs a concrete repair or unresolved issue')
    from state_protocol import validate_against_schema
    schema=c.load(ROOT/f'schemas/authoring/production-{name}.schema.json')
    errors=validate_against_schema(value,schema)
    if errors: raise ValueError('production '+name+': '+'; '.join(errors))


def validate_task(task: Any) -> dict[str, Any]:
    schema_check(task,'task'); c.exact(task,TASK_FIELDS | ({'scene_materials'} & task.keys()),'task')
    route=execution_routes.resolve(task['route'],task['features'])
    if bool(task.get('scene_materials', [])) != ('scene-persona' in route['features']):
        raise ValueError('scene-persona requires explicit scene_materials selectors and vice versa')
    ids=set(); roles=set()
    for source in task['sources']:
        c.exact(source,{'id','path','role','disposition','locator','reason'},'source')
        for name in ('id','path','role','locator','reason'): c.text(source[name],name)
        if source['id'] in ids: raise ValueError('duplicate source id')
        ids.add(source['id'])
        if source['disposition']=='applied': roles.add(source['role'])
    if set(route['source_roles'])-roles: raise ValueError('missing applied source roles')
    criteria=set()
    for item in task['criteria']:
        if item['id'] in criteria: raise ValueError('duplicate criterion id')
        criteria.add(item['id'])
    if task['route']=='timed-sequence' and task['sequence_plan'] is None:
        raise ValueError('timed-sequence route needs an explicit sequence plan')
    production_direction.validate(task['direction'],task['sources'],task['criteria'])
    return route


def snapshot(root: Path, task_path: str) -> tuple[dict[str,Any],dict[str,Any],list[dict[str,Any]],dict[str,bytes]]:
    task_bytes=c.read(c.local(root,task_path))
    task=c.decode(task_bytes); route=validate_task(task)
    dependencies={}; blobs={}
    def add(base: Path, path: str, space: str) -> bytes:
        raw=c.read(c.local(base,path)); key=c.digest(raw)
        dependencies[(space,path)]={'space':space,'path':path,'sha256':key,'size':len(raw)}
        blobs[key]=raw; return raw
    if add(root,task_path,'project')!=task_bytes: raise ValueError('task changed during preparation')
    import route_reading
    reading=c.decode(add(root,task['route_reading'],'project'))
    issuance=route_reading.require_route_reading(reading,project=root,routes={task['route']},features=task['features'])
    for source in task['sources']:
        raw=add(root,source['path'],'project')
        if source['disposition']!='applied': continue
        if source['role']=='narrative':
            from narrative import validate_narrative
            report=validate_narrative(c.decode(raw))
            if not report['ok']: raise ValueError('invalid narrative: '+str(report['errors']))
        elif source['role']=='scene-plot':
            from scene_plot import validate_scene_plot
            report=validate_scene_plot(c.decode(raw))
            if not report['ok']: raise ValueError('invalid scene plot: '+str(report['errors']))
        elif source['role']=='public-artifact':
            from protocol_contract import validate_artifact
            report=validate_artifact(c.decode(raw))
            if not report['ok']: raise ValueError('invalid public artifact: '+str(report['errors']))
    delivery=add(root,task['delivery']['path'],'project').decode('utf-8'); c.text(delivery,'delivery')
    sequence=None
    if task['sequence_plan'] is not None:
        import timed_sequence
        plan_raw=add(root,task['sequence_plan'],'project'); plan=c.decode(plan_raw)
        sequence=timed_sequence.validate_plan(root,plan)
        for asset in plan['assets']:
            if c.digest(add(root,asset['path'],'project'))!=asset['sha256']:
                raise ValueError('sequence asset changed during preparation')
    import scene_persona
    scene_materials = scene_persona.consume(root, task.get('scene_materials', []), add)
    skill_files={execution_routes.MANIFEST} | {x['path'] for x in route['reads']}
    for parent,glob in [('scripts','*.py'),('schemas','*.json'),('protocols','*.json')]:
        skill_files.update(f.relative_to(ROOT).as_posix() for f in (ROOT/parent).rglob(glob))
    for path in sorted(skill_files): add(ROOT,path,'skill')
    consumer={'route':task['route'],'transport':task['delivery']['transport'],'instructions':delivery,
              'criteria':task['criteria'],'direction':production_direction.compile_direction(task['direction'],delivery,task['delivery']['transport']),
              'sequence':sequence,'authoring_materials':scene_materials}
    prepared={'task_path':task_path,'task':task,'route':route,
              'route_reading':reading,'route_reading_sha256':c.content_id(reading),'reading_issuance':issuance,'dependencies':sorted(dependencies.values(),key=lambda x:(x['space'],x['path'])),
              'consumer_sha256':c.content_id(consumer)}
    prepared['input_sha256']=c.content_id(prepared)
    return prepared,consumer,prepared['dependencies'],blobs


def _prepare(root: Path, task: str, *, parent: dict | None = None, identity: str | None = None) -> dict[str, Any]:
    import work_ledger
    prepared,consumer,_,blobs=snapshot(root,task)
    current=work_ledger.require_open(root)
    if current['task_id']!=prepared['task']['task_id']:
        raise ValueError('task is not the open work-ledger task')
    production=c.local(root,'production',exists=False); production.mkdir(exist_ok=True)
    run=identity or generate_uuid7(); target=run_dir(root,run,exists=False)
    prepared['run_id']=run
    prepared['parent']=parent
    prepared.pop('input_sha256')
    prepared['input_sha256']=c.content_id(prepared)
    if target.exists():
        _,existing,_,_=load_run(root,run)
        if existing!=prepared:
            raise ValueError('revision child conflicts with its prepared inputs')
        if current.get('production_run')!=run:
            current['production_run']=run
            work_ledger.write_current(root,current)
            work_ledger.append(root,{'at':work_ledger.now(),'task_id':current['task_id'],'event':'note','text':f'restored production run {run}'})
        return {'run':run,'input_sha256':prepared['input_sha256'],'consumer':str(target/'consumer.json')}
    staging=Path(tempfile.mkdtemp(prefix='.pending-',dir=production))
    try:
        for raw in blobs.values(): c.object_store(staging,raw)
        c.atomic(staging/'prepared.json',c.encoded(prepared))
        c.atomic(staging/'consumer.json',c.encoded(consumer))
        (staging/'records').mkdir()
        c.publish_directory(staging, target); c.fsync_dir(production)
    finally:
        if staging.exists(): shutil.rmtree(staging)
    current['production_run']=run
    work_ledger.write_current(root,current)
    work_ledger.append(root,{'at':work_ledger.now(),'task_id':current['task_id'],'event':'note','text':f'prepared production run {run}'})
    return {'run':run,'input_sha256':prepared['input_sha256'],'consumer':str(target/'consumer.json')}


def prepare(root: Path, task: str) -> dict[str, Any]:
    root=root.absolute()
    with c.lock(root):
        return _prepare(root,task)


def load_run(root: Path, run: str) -> tuple[Path,dict[str,Any],dict[str,Any],list[dict[str,Any]]]:
    directory=run_dir(root,run)
    prepared=c.load(c.local(directory,'prepared.json')); consumer=c.load(c.local(directory,'consumer.json'))
    check=dict(prepared); key=check.pop('input_sha256',None)
    if c.content_id(check)!=key or c.content_id(consumer)!=prepared['consumer_sha256']:
        raise ValueError('prepared input or consumer integrity mismatch')
    for dep in prepared['dependencies']:
        raw=c.object_read(directory,dep['sha256'])
        if len(raw)!=dep['size']: raise ValueError('source snapshot size mismatch')
    records=[]; previous=None
    for path in sorted((directory/'records').iterdir()):
        if path.name.startswith('.pending-'): continue
        if not path.is_file() or path.is_symlink(): raise ValueError('unexpected receipt path')
        row=c.load(path); value=dict(row); key=value.pop('sha256',None)
        if c.content_id(value)!=key or row.get('previous')!=previous or row.get('sequence')!=len(records)+1:
            raise ValueError('receipt chain integrity mismatch')
        if path.name!=f'{len(records)+1:06d}-{key}.json' or row.get('input_sha256')!=prepared['input_sha256']:
            raise ValueError('receipt address or input mismatch')
        if row.get('event') not in {'handoff','dispatch-claim','dispatch-results','dispatch-trace','candidate','review','selection','completion',
                                      'authorization','revocation','reservation','choice','action-result','revision','action-output'} | lifecycle.EVENTS:
            raise ValueError('unknown receipt event')
        records.append(row); previous=key
    lifecycle.completion_tail(records,prepared,run)
    for row in records:
        for item in row['data'].get('files',[])+row['data'].get('evidence',[]):
            if len(c.object_read(directory,item['sha256']))!=item['size']:
                raise ValueError('recorded artifact snapshot size mismatch')
    return directory,prepared,consumer,records


def assert_current(root: Path, run: str) -> tuple[Path,dict[str,Any],dict[str,Any],list[dict[str,Any]]]:
    loaded=load_run(root,run); directory,prepared,consumer,records=loaded
    import route_reading
    route_reading.require_route_reading(prepared['route_reading'],project=root,routes={prepared['task']['route']},features=prepared['task']['features'])
    for dep in prepared['dependencies']:
        base=ROOT if dep['space']=='skill' else root
        raw=c.read(c.local(base,dep['path']))
        if c.digest(raw)!=dep['sha256']:
            raise ValueError(f'changed {dep["space"]} input: {dep["path"]}; prepare a new run')
    for row in records:
        data=row['data']
        for item in data.get('files',[]) + data.get('evidence',[]):
            raw=c.read(c.local(root,item['path']))
            if c.digest(raw)!=item['sha256'] or c.object_read(directory,item['sha256'])!=raw:
                raise ValueError(f'changed recorded artifact: {item["path"]}')
    for row in records:
        if row['event']=='selection' and row['data']['selection']['scope']=='registry-adoption':
            selection=row['data']['selection']
            candidate=find(records,'candidate',selection['candidate'])
            confirm_asset_adoption(root,selection['adoption'],candidate['data']['files'][0])
    return loaded

def require_mutable(records: list[dict[str,Any]]) -> None:
    if any(r['event']=='completion' for r in records):
        raise ValueError('this run is complete; prepare a new run for new work')


def append_record(directory: Path, prepared: dict[str,Any], records: list[dict[str,Any]], event: str, data: dict[str,Any]) -> dict[str,Any]:
    # Exact repeated calls reuse durable evidence instead of duplicating it.
    for row in reversed(records):
        if row['event']==event and row['data']==data: return row
    if event!='reservation-release':require_mutable(records)
    row={'sequence':len(records)+1,'previous':records[-1]['sha256'] if records else None,
         'input_sha256':prepared['input_sha256'],'event':event,'data':data}
    row['sha256']=c.content_id(row)
    lifecycle.completion_tail([*records,row],prepared,directory.name)
    c.atomic(directory/'records'/f'{row["sequence"]:06d}-{row["sha256"]}.json',c.encoded(row))
    return row


def find(records: list[dict[str,Any]], event: str, identifier: str | None = None) -> dict[str,Any]:
    matches=[r for r in records if r['event']==event and (identifier is None or r['sha256']==identifier)]
    if not matches: raise ValueError(f'missing {event} evidence')
    return matches[-1]


def file_record(root: Path, directory: Path, path: str) -> dict[str,Any]:
    raw=c.read(c.local(root,path))
    return {'path':path,'sha256':c.object_store(directory,raw),'size':len(raw)}


def handoff(root: Path, run: str, recipient: str, method: str) -> dict[str,Any]:
    c.text(recipient,'recipient')
    if method not in {'conversation','manual','dispatcher','editor'}: raise ValueError('invalid handoff method')
    with c.lock(root):
        directory,p,consumer,rows=assert_current(root,run)
        data={'recipient':recipient,'method':method,'consumer_sha256':c.content_id(consumer)}
        existing=[r for r in rows if r['event']=='handoff']
        if existing and existing[0]['data']!=data: raise ValueError('run already handed to a different consumer')
        return append_record(directory,p,rows,'handoff',data)


def capture(root: Path, run: str, artifact: str, note: str, limitations: list[str] | None = None) -> dict[str,Any]:
    c.text(note,'candidate provenance')
    production_direction.strings(limitations or [], 'candidate limitations')
    with c.lock(root):
        directory,p,_,rows=assert_current(root,run); h=find(rows,'handoff')
        if h['data']['method']=='dispatcher':
            result=find(rows,'dispatch-results')
            if artifact not in {f['path'] for f in result['data']['files']}: raise ValueError('artifact is not a recorded dispatch result')
        f=file_record(root,directory,artifact)
        if f['size']==0: raise ValueError('empty artifact')
        media=media_evidence.inspect(directory/'objects'/f['sha256'],c.object_read(directory,f['sha256']))
        return append_record(directory,p,rows,'candidate',{'handoff':h['sha256'],'files':[f],'note':note,
                             'media':media,'limitations':limitations or []})



def capture_dispatch_result(root: Path, run: str, artifact: str) -> dict[str, Any]:
    """Register an already acquired result against its saved claim and bytes."""
    with c.lock(root):
        directory, prepared, _, rows = load_run(root, run)
        handoff_record = find(rows, 'handoff')
        if handoff_record['data']['method'] != 'dispatcher':
            raise ValueError('recording recovery requires the saved dispatcher handoff')
        claim = find(rows, 'dispatch-claim')
        result = find(rows, 'dispatch-results')
        if result['data']['claim'] != claim['sha256']:
            raise ValueError('acquired results belong to a different dispatch claim')
        matches = [item for item in result['data']['files'] if item['path'] == artifact]
        if len(matches) != 1:
            raise ValueError('recording recovery requires one exact acquired result')
        item = matches[0]
        raw = c.object_read(directory, item['sha256'])
        if len(raw) != item['size'] or not raw:
            raise ValueError('acquired result snapshot size differs')
        existing = [row for row in rows if row['event'] == 'candidate'
                    and row['data']['handoff'] == handoff_record['sha256']
                    and row['data']['files'] == [item]]
        if len(existing) > 1:
            raise ValueError('acquired result has ambiguous candidate registrations')
        if not existing:
            require_mutable(rows)
        path = c.local(root, artifact, exists=False)
        if path.exists():
            if c.read(path) != raw:
                raise ValueError('recorded output path contains different bytes')
        else:
            c.atomic(path, raw)
        if existing:
            return existing[0]
        inspected = media_evidence.inspect(directory / 'objects' / item['sha256'], raw)
        return append_record(directory, prepared, rows, 'candidate', {
            'handoff': handoff_record['sha256'], 'files': [item],
            'note': 'Recorded from acquired dispatch evidence; content review pending.',
            'media': inspected, 'limitations': []})


def recover_recording(root: Path, run: str) -> dict[str, Any]:
    """Recover local candidate records using completed output snapshots only."""
    with c.lock(root):
        _, _, _, rows = load_run(root, run)
        result = find(rows, 'dispatch-results')
        records = [capture_dispatch_result(root, run, item['path']) for item in result['data']['files']]
        return {'ok': True, 'run': run, 'candidates': [row['sha256'] for row in records],
                'network_calls': 0, 'new_reservations': 0}


def draft_review(root: Path, run: str, candidate: str) -> dict[str,Any]:
    directory,p,_,rows=assert_current(root,run); find(rows,'candidate',candidate)
    from tactic_consultation import review_questions
    questions = review_questions(root, p['task'], directory=directory, dependencies=p['dependencies'])
    return {'input_sha256':p['input_sha256'],'candidate':candidate,'reviewer':'','observations':[],
            'checks':[{'criterion':x['id'],'verdict':'not-assessed','observation_indices':[],
                       'evidence_basis':'not-assessed','reason':'\n'.join(questions.get(x['id'], []))} for x in p['task']['criteria']],
            'repairs':[],'unresolved':[],'conclusion':''}


def validate_review(data: Any, p: dict[str,Any], candidate: dict[str,Any], raw: bytes) -> None:
    schema_check(data,'review')
    c.exact(data,{'input_sha256','candidate','reviewer','observations','checks','repairs','unresolved','conclusion'} | ({'visual_assessment'} & data.keys()),'review')
    if data['input_sha256']!=p['input_sha256'] or data['candidate']!=candidate['sha256']: raise ValueError('review names another input or candidate')
    c.text(data['reviewer'],'reviewer'); c.text(data['conclusion'],'conclusion')
    obs=data['observations']; media=candidate['data']['media']
    if not isinstance(obs,list) or not obs: raise ValueError('actual observations required')
    support=[]
    for entry in obs:
        c.exact(entry,{'locator','observation','method'},'observation')
        c.text(entry['observation'],'observation')
        if entry['method'] not in {'visual-inspection','audio-inspection','text-inspection','measurement','operator-report'}:
            raise ValueError('declare the actual observation method')
        support.append(media_evidence.validate_locator(entry['locator'],raw,media))
        if entry['method']=='audio-inspection' and 'audio' not in support[-1]:
            raise ValueError('audio inspection needs an observed interval of actual audio')
    assessment=data.get('visual_assessment')
    if assessment is not None:
        if media.get('kind')!='image': raise ValueError('a single-image assessment needs an inspected still image')
        indices=assessment['observation_indices']
        if any(type(i) is not int or not 0<=i<len(obs) or obs[i]['method']!='visual-inspection' for i in indices):
            raise ValueError('visual subjects must cite the actual visual inspection')
        for subject in assessment['subjects'].values():
            if subject['continuity']=='recurring' and subject['character_id'] is None:
                raise ValueError('a recurring assessed subject needs a character ID')
    if not isinstance(data['checks'],list): raise ValueError('checks list required')
    expected={x['id']:x for x in p['task']['criteria']}; seen=set()
    for check in data['checks']:
        c.exact(check,{'criterion','verdict','observation_indices','evidence_basis','reason'},'review check')
        if check['criterion'] not in expected or check['criterion'] in seen: raise ValueError('unknown or repeated review criterion')
        seen.add(check['criterion']); c.text(check['reason'],'review reason')
        if check['verdict'] not in {'pass','fail','not-assessed','not-applicable'}: raise ValueError('invalid review verdict')
        if check['evidence_basis'] not in {'reviewer-interpretation','audience-report','technical-measurement','not-assessed'}:
            raise ValueError('distinguish interpretation, audience evidence and measurement')
        indices=check['observation_indices']
        if not isinstance(indices,list) or not indices or any(type(i) is not int or not 0<=i<len(obs) for i in indices):
            raise ValueError('check must cite actual observations by zero-based index')
        if len(set(indices))!=len(indices):
            raise ValueError('observation indices must be unique')
        if check['verdict']=='pass' and (check['evidence_basis']=='not-assessed' or not any(expected[check['criterion']]['evidence'] in support[i] for i in indices)):
            raise ValueError('the observed medium or interval cannot support this claimed pass')
    if seen!=set(expected): raise ValueError('review must account for every criterion')
    production_direction.strings(data['unresolved'],'unresolved issues')
    production_direction.validate_repairs(data['repairs'],p['task']['direction'],obs)
    if any(x['verdict']=='fail' for x in data['checks']) and not data['repairs'] and not data['unresolved']:
        raise ValueError('a failed review needs a concrete repair or unresolved issue')


def review(root: Path, run: str, review_file: str) -> dict[str,Any]:
    with c.lock(root):
        directory,p,_,rows=assert_current(root,run)
        f=file_record(root,directory,review_file); data=c.decode(c.object_read(directory,f['sha256']))
        candidate=find(rows,'candidate',data.get('candidate'))
        raw=c.object_read(directory,candidate['data']['files'][0]['sha256'])
        validate_review(data,p,candidate,raw)
        return append_record(directory,p,rows,'review',{'candidate':candidate['sha256'],'files':[f],'review':data})


def eligible(p: dict[str,Any], reviewed: dict[str,Any]) -> None:
    data=reviewed['data']['review']
    hard={x['id'] for x in p['task']['criteria'] if x['strength']=='hard'}
    if data['unresolved']: raise ValueError('review has unresolved issues')
    for check in data['checks']:
        if check['criterion'] in hard and check['verdict']!='pass':
            raise ValueError('a hard criterion has not passed')


def draft_selection(root: Path, run: str, candidate: str) -> dict[str,Any]:
    _,p,_,rows=assert_current(root,run); find(rows,'candidate',candidate)
    matching=[r for r in rows if r['event']=='review' and r['data']['candidate']==candidate]
    if not matching: raise ValueError('candidate needs a recorded review')
    return {'input_sha256':p['input_sha256'],'candidate':candidate,'review':matching[-1]['sha256'],
            'selector':'','reason':'','scope':'delivery-only','adoption':None,'authorization':''}


def confirm_asset_adoption(root: Path, selector: dict[str,Any], target: dict[str,Any]) -> list[Path]:
    import asset_registry
    c.exact(selector,{'owner_path','asset_id','role'},'registry adoption selector')
    path=c.local(root,selector['owner_path']); text=c.read(path).decode('utf-8')
    errors,_=asset_registry.check(text,[])
    if errors: raise ValueError('invalid asset registry: '+'; '.join(errors))
    matches=[r for r in asset_registry.parse(text) if r['id']==selector['asset_id']]
    if len(matches)!=1: raise ValueError('adopted asset must have exactly one registry record')
    fields=matches[0]['fields']
    if fields.get('status')!='accepted' or fields.get('role')!=selector['role']:
        raise ValueError('registry does not adopt the selected asset for this role')
    if fields.get('file')!=target['path'] or fields.get('sha-256')!=target['sha256']:
        raise ValueError('registry adoption must bind the exact candidate path and bytes')
    return [path,c.local(root,target['path'])]


def select(root: Path, run: str, selection_file: str) -> dict[str,Any]:
    with c.lock(root):
        directory,p,_,rows=assert_current(root,run)
        f=file_record(root,directory,selection_file); data=c.decode(c.object_read(directory,f['sha256']))
        schema_check(data,'selection')
        c.exact(data,{'input_sha256','candidate','review','selector','reason','scope','adoption','authorization'} | ({'influence','continuity_decision'} & data.keys()),'selection')
        if data['input_sha256']!=p['input_sha256']: raise ValueError('selection is for a different input')
        c.text(data['selector'],'selector'); c.text(data['reason'],'selection reason')
        find(rows,'candidate',data['candidate'])
        matching=[r for r in rows if r['event']=='review' and r['data']['candidate']==data['candidate']]
        if not matching or matching[-1]['sha256']!=data['review']: raise ValueError('selection must use the latest review of this candidate')
        eligible(p,matching[-1]); files=[f]
        if data.get('influence')=='identity':
            if data['scope']!='registry-adoption': raise ValueError('identity acceptance requires registry adoption')
            import visual_continuity
            visual_continuity.selection_subject(root,run,data,loaded=(directory,p,{},rows))
        elif data.get('continuity_decision') is not None:
            raise ValueError('a continuity decision belongs to an identity acceptance')

        if data['scope']=='delivery-only' and data['adoption'] is not None:
            raise ValueError('delivery-only must not carry an adoption claim')
        if data['scope']=='registry-adoption':
            confirm_asset_adoption(root,data['adoption'],find(rows,'candidate',data['candidate'])['data']['files'][0])
        selection_reservation=_reserve(directory,p,rows,authorization=data['authorization'],actor=data['selector'],
            operation='select',scopes=['candidate:'+data['candidate']],request_sha256=c.content_id(data))
        tokens=[selection_reservation['sha256']]
        rows=load_run(root,run)[3]
        if data['scope']=='delivery-only':
            if data['adoption'] is not None: raise ValueError('delivery-only must not carry an adoption claim')
        elif data['scope']=='registry-adoption':
            adoption_reservation=_reserve(directory,p,rows,authorization=data['authorization'],actor=data['selector'],
                operation='adopt',scopes=['candidate:'+data['candidate']],request_sha256=c.content_id({'adopt':data}))
            tokens.append(adoption_reservation['sha256'])
            rows=load_run(root,run)[3]
            candidate=find(rows,'candidate',data['candidate'])
            for path in confirm_asset_adoption(root,data['adoption'],candidate['data']['files'][0]):
                files.append(file_record(root,directory,path.relative_to(root).as_posix()))
        else: raise ValueError('invalid selection scope')
        return lifecycle.commit_effect(root,run,'selection',
            {'files':files,'selection':data,'reservation':selection_reservation['sha256']},tokens,effect='local-action')


def complete(root: Path, run: str) -> dict[str,Any]:
    with c.lock(root):
        directory,p,_,rows=assert_current(root,run); selection=find(rows,'selection')
        chosen=selection['data']['selection']; matching=[r for r in rows if r['event']=='review' and r['data']['candidate']==chosen['candidate']]
        if not matching or matching[-1]['sha256']!=chosen['review']: raise ValueError('selected review is no longer current')
        eligible(p,matching[-1])
        production_authority.reservation(p,rows,history=permission_history(root,p),authorization=chosen['authorization'],actor=chosen['selector'],
            operation='select',scopes=['candidate:'+chosen['candidate']],request_sha256=c.content_id(chosen))
        if chosen['scope'] != 'delivery-only':
            production_authority.reservation(p,rows,history=permission_history(root,p),authorization=chosen['authorization'],actor=chosen['selector'],
                operation='adopt',scopes=['candidate:'+chosen['candidate']],request_sha256=c.content_id({'adopt':chosen}))
        data={'selection':selection['sha256'],'candidate':chosen['candidate'],'scope':chosen['scope'],
              'task_id':p['task']['task_id'],'run':run}
        return append_record(directory,p,rows,'completion',data)


def verify_completion(root: Path, run: str, task_id: str) -> dict[str,Any]:
    _,p,_,rows=assert_current(root,run); done=find(rows,'completion')
    if p['task']['task_id']!=task_id or done['data']['task_id']!=task_id or done['data']['run']!=run:
        raise ValueError('completion belongs to another task')
    lifecycle.completion_tail(rows,p,run)
    if done['data']['selection']!=find(rows,'selection')['sha256']:
        raise ValueError('completion is not the terminal selected state')
    chosen=find(rows,'selection')['data']['selection']
    production_authority.reservation(p,rows,history=permission_history(root,p),authorization=chosen['authorization'],actor=chosen['selector'],
        operation='select',scopes=['candidate:'+chosen['candidate']],request_sha256=c.content_id(chosen))
    if chosen['scope']!='delivery-only':
        production_authority.reservation(p,rows,history=permission_history(root,p),authorization=chosen['authorization'],actor=chosen['selector'],
            operation='adopt',scopes=['candidate:'+chosen['candidate']],request_sha256=c.content_id({'adopt':chosen}))
    return done


def status(root: Path, run: str) -> dict:
    from production_resume import report
    return report(root, run)


def draft_authorization(root: Path, run: str) -> dict[str,Any]:
    _,p,_,_=assert_current(root,run)
    return {'input_sha256':p['input_sha256'],'principal':'','actor':'','purpose':'',
            'permissions':[],'preserve_sources':[x['id'] for x in p['task']['sources']],
            'stop_conditions':[],'halt_on':[],'expires_at':None,'evidence':{'path':'','locator':''}}


def authorize(root: Path, run: str, filename: str) -> dict[str,Any]:
    with c.lock(root):
        from production_revision import assert_context
        directory,p,_,rows=assert_context(root,run)
        require_mutable(rows)
        f=file_record(root,directory,filename); grant=c.decode(c.object_read(directory,f['sha256']))
        if any(permission.get('operation')!='edit' for permission in grant.get('permissions',[])):
            assert_current(root,run)
        schema_check(grant,'authorization'); production_authority.validate(grant,p)
        proof=file_record(root,directory,grant['evidence']['path'])
        if not proof['size']: raise ValueError('authorization evidence is empty')
        from input_evidence import InputEvidence
        import request_scope
        reader = InputEvidence(root)
        for permission in grant['permissions']:
            request_scope.verify_sources(permission['request_scope'], None, reader)
        scope_files = [file_record(root, directory, name) for name in sorted(reader.read_paths)]
        key=production_authority.authority_key(grant,proof['sha256'])
        history=permission_history(root,p)
        for prior in history:
            if prior['event']=='authorization' and prior['data'].get('authority_key')==key:
                if production_authority.grant_body(prior['data']['authorization'])!=production_authority.grant_body(grant):
                    raise ValueError('the same approval cannot silently change its permissions; obtain new explicit evidence')
            if prior['event']=='revocation' and prior['data'].get('authority_key')==key:
                raise ValueError('this approval was revoked across the task')
        return append_record(directory,p,rows,'authorization',{'authorization':grant,'authority_key':key,'files':[f,proof,*scope_files]})


def revoke(root: Path, run: str, authorization: str, reason: str) -> dict[str,Any]:
    c.text(reason,'revocation reason')
    with c.lock(root):
        directory,p,_,rows=assert_current(root,run); grant=find(rows,'authorization',authorization)
        return append_record(directory,p,rows,'revocation',{'authorization':authorization,'authority_key':grant['data']['authority_key'],'reason':reason})


def permission_history(root: Path, prepared: dict[str, Any]) -> list[dict[str, Any]]:
    """Read every immutable receipt in this task, including superseded runs."""
    folder=c.local(root,'production',exists=False)
    result=[]
    if folder.exists():
        for child in sorted(folder.iterdir()):
            if child.name.startswith('.pending-'):
                continue
            _,other,_,records=load_run(root,child.name)
            if other['task']['task_id']==prepared['task']['task_id']:
                hard=[x['id'] for x in other['task']['criteria'] if x['strength']=='hard']
                result.extend({**row,'hard_criteria':hard} if row['event']=='review' else row for row in records)
    return result


def _reserve(directory: Path, prepared: dict[str,Any], rows: list[dict[str,Any]], **request: Any) -> dict[str,Any]:
    data=production_authority.reservation(prepared,rows,history=permission_history(directory.parent.parent,prepared),**request)
    return append_record(directory,prepared,rows,'reservation',data)


def reserve_action(root: Path, run: str, **request: Any) -> dict[str,Any]:
    with c.lock(root):
        directory,p,_,rows=assert_current(root,run)
        data=production_authority.reservation(p,rows,history=permission_history(root,p),**request)
        prior=[r for r in rows if r['event']=='reservation' and r['data']==data]
        if prior:
            lifecycle.require_active(rows,p,run,prior[-1]['sha256'])
            raise ValueError('external action permission was already handed out; recover its existing result')
        reservation=append_record(directory,p,rows,'reservation',data)
        lifecycle.begin(root,run,reservation['sha256'],effect='external-handoff')
        return {'record':reservation,'repeated':False}


def action_result(root: Path, run: str, reservation: str, artifact: str, note: str,
                  evidence: list[str] | None = None, limitations: list[str] | None = None) -> dict[str,Any]:
    with c.lock(root):
        directory,p,_,rows=assert_current(root,run); reserved=find(rows,'reservation',reservation)
        from production_recovery import _authorized
        _authorized(root,p,rows,reservation)
        if reserved['data']['operation'] not in {'edit','submit'}:
            raise ValueError('this reservation cannot produce an artifact')
        if reserved['data']['outputs']<1: raise ValueError('reservation allows no output')
        h=find(rows,'handoff'); f=file_record(root,directory,artifact)
        if not f['size']: raise ValueError('empty action output')
        c.text(note,'action provenance'); production_direction.strings(limitations or [],'action limitations')
        ev=[file_record(root,directory,x) for x in (evidence or [])]
        prior=[r for r in rows if r['event']=='action-result' and r['data']['reservation']==reservation]
        if prior and prior[-1]['data']['files']!=[f]: raise ValueError('reservation already produced a different output')
        result=append_record(directory,p,rows,'action-result',{'reservation':reservation,'files':[f],'evidence':ev,'note':note})
        rows=load_run(root,run)[3]
        media=media_evidence.inspect(directory/'objects'/f['sha256'],c.object_read(directory,f['sha256']))
        return append_record(directory,p,rows,'candidate',{'handoff':h['sha256'],'files':[f],'note':note,'media':media,
            'limitations':limitations or [],'action_result':result['sha256']})


def record_choice(root: Path, run: str, filename: str) -> dict[str,Any]:
    with c.lock(root):
        directory,p,_,rows=assert_current(root,run)
        f=file_record(root,directory,filename); data=c.decode(c.object_read(directory,f['sha256']))
        c.exact(data,{'input_sha256','decision','selected','actor','authorization','reason'},'choice')
        if data['input_sha256']!=p['input_sha256']: raise ValueError('choice belongs to another input')
        matches=[d for d in p['task']['direction']['decisions'] if d['id']==data['decision']]
        if len(matches)!=1 or matches[0]['selected']!=data['selected']:
            raise ValueError('choice changes the prepared direction; prepare the revised task before execution')
        c.text(data['reason'],'choice reason')
        reserved=_reserve(directory,p,rows,authorization=data['authorization'],actor=data['actor'],operation='decide',
                          scopes=['decision:'+data['decision']],request_sha256=c.content_id(data))
        rows=load_run(root,run)[3]
        return lifecycle.commit_effect(root,run,'choice',{'choice':data,'reservation':reserved['sha256'],'files':[f]},
            [reserved['sha256']],effect='local-action')


def impact(root: Path, run: str) -> dict[str,Any]:
    with c.lock(root):
        directory,p,_,rows=load_run(root,run); changes=[]
        for dep in p['dependencies']:
            base=ROOT if dep['space']=='skill' else root
            try:
                current=c.digest(c.read(c.local(base,dep['path'])))
                if current==dep['sha256']: continue
                change='changed'
            except (ValueError,OSError) as exc:
                current=None; change='missing-or-unreadable'
            changes.append({'space':dep['space'],'path':dep['path'],'change':change,'recorded_sha256':dep['sha256'],'current_sha256':current})
        for row in rows:
            for item in row['data'].get('files',[])+row['data'].get('evidence',[]):
                try: current=c.digest(c.read(c.local(root,item['path'])))
                except (ValueError,OSError): current=None
                if current!=item['sha256']:
                    changes.append({'space':'artifact','path':item['path'],'change':'changed-or-missing',
                                    'recorded_sha256':item['sha256'],'current_sha256':current})
        consequence=production_direction.impact(p,{x['path'] for x in changes if x['space']=='project'})
        return {'ok':not changes,'run':run,'changes':changes,'direction':consequence,
                'next':'prepare-from-revised-sources' if changes else 'continue-current-run',
                'invalidated':['consumer','authorization','package','review','selection','completion'] if changes else []}











def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    import production_inputs
    production_inputs.add_arguments(sub)
    import tactic_consultation
    tactic_consultation.add_arguments(sub)
    import production_variation
    production_variation.add_arguments(sub)
    for name in ['prepare','handoff','capture','draft-review','review','draft-selection','select','complete','status','impact','resume','draft-authorization','authorize','revoke','record-choice','revision-intent','revise','recover-action','recover-recording','release-reservation','draft-release']:
        p=sub.add_parser(name); p.add_argument('--root',type=Path,required=True)
        if name=='prepare': p.add_argument('--task',required=True)
        else: p.add_argument('--run',required=True)
        if name=='handoff': p.add_argument('--recipient',required=True); p.add_argument('--method',choices=['conversation','manual','dispatcher','editor'],required=True)
        if name=='capture': p.add_argument('--artifact',required=True); p.add_argument('--note',required=True)
        if name in {'draft-review','draft-selection'}: p.add_argument('--candidate',required=True); p.add_argument('--out',required=True)
        if name in {'review','select','authorize','record-choice'}: p.add_argument('--file',required=True)
        if name=='draft-authorization': p.add_argument('--out',required=True)
        if name=='revoke': p.add_argument('--authorization',required=True); p.add_argument('--reason',required=True)
        if name=='capture': p.add_argument('--limitation',action='append',default=[])
        if name in {'revision-intent','revise'}:
            p.add_argument('--task',required=True);p.add_argument('--candidate',required=True);p.add_argument('--repair-index',type=int,required=True)
        if name=='revise':
            p.add_argument('--authorization',required=True);p.add_argument('--actor',required=True)
        if name in {'recover-action','draft-release'}: p.add_argument('--reservation',required=True)
        if name=='draft-release':p.add_argument('--out',required=True)
        if name=='release-reservation':p.add_argument('--request',required=True)
    a=parser.parse_args(); root=a.root.absolute()
    try:
        if a.command in tactic_consultation.COMMANDS: result=tactic_consultation.command(a,parser)
        elif a.command == 'draft-variation': result=production_variation.command(a,parser)
        elif a.command in production_inputs.COMMANDS: result=production_inputs.command(a,parser)
        elif a.command=='release-reservation':result=lifecycle.release(root,a.run,a.request)
        elif a.command=='draft-release':
            result=lifecycle.draft_release(root,a.run,a.reservation)
            c.atomic(c.local(root,a.out,exists=False),c.encoded(result))
        elif a.command=='prepare': result=prepare(root,a.task)
        elif a.command=='revision-intent':
            from production_revision import revision_intent
            result=revision_intent(root,a.run,a.task,a.candidate,a.repair_index)
        elif a.command=='revise':
            from production_revision import revise
            result=revise(root,a.run,a.task,a.candidate,a.repair_index,a.authorization,a.actor)
        elif a.command=='recover-recording': result=recover_recording(root,a.run)
        elif a.command=='recover-action':
            from production_recovery import recover
            result=recover(root,a.run,a.reservation)
        elif a.command=='handoff': result=handoff(root,a.run,a.recipient,a.method)
        elif a.command=='capture': result=capture(root,a.run,a.artifact,a.note,a.limitation)
        elif a.command in {'draft-review','draft-selection'}:
            fn=draft_review if a.command=='draft-review' else draft_selection
            result=fn(root,a.run,a.candidate); c.atomic(c.local(root,a.out,exists=False),c.encoded(result))
        elif a.command=='draft-authorization':
            result=draft_authorization(root,a.run); c.atomic(c.local(root,a.out,exists=False),c.encoded(result))
        elif a.command=='authorize': result=authorize(root,a.run,a.file)
        elif a.command=='revoke': result=revoke(root,a.run,a.authorization,a.reason)
        elif a.command=='record-choice': result=record_choice(root,a.run,a.file)
        elif a.command=='impact': result=impact(root,a.run)
        elif a.command=='review': result=review(root,a.run,a.file)
        elif a.command=='select': result=select(root,a.run,a.file)
        elif a.command=='complete': result=complete(root,a.run)
        else: result=status(root,a.run)
        print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result.get('ok',True) else 1
    except (ValueError,OSError,UnicodeError,KeyError,TypeError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)})); return 1
if __name__=='__main__': raise SystemExit(main())
