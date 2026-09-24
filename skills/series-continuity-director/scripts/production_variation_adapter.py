"""Resolve one recorded submission and its local selections into a variation draft."""
from __future__ import annotations
import copy
import execution_contract as c
import production_inputs


def source(root,directory,prepared,rows,claim,reader):
    manifest=claim['data']['manifest']
    if c.content_id(manifest)!=claim['data']['manifest_sha256']:raise ValueError('dispatch manifest mismatch')
    return manifest['rendered'],{**manifest['spec'],'_manifest':manifest}


def inputs(root,out,prepared,spec,rendered,proposed,difference,reader,*,reason):
    task=copy.deepcopy(prepared['task']);choices=production_inputs.draft_choices(task);files={};issues=[]
    copied=copy.deepcopy(spec);manifest=copied.pop('_manifest');visual=copied['visual_continuity'];validation=copied['request_validation']
    for change in difference:
        field=rendered['fields'][change['field']];path=field['field']
        if change['kind']=='parameter':
            name='.'.join(path)
            group='options' if name in copied.get('options',{}) else 'parameters'
            copied.setdefault(group,{})[name]=change['after']
        elif change['kind']=='content':
            if path==rendered['layout']['primary_text']:copied['text']=change['after']
            elif path==rendered['layout']['negative_text']:copied['negative_text']=change['after']
        else:
            entry=next(item for item in rendered['layout']['media'] if item['field']==path)
            copied['inputs'][entry['index']]['path']=change['after']['path']
            issues.append({'field':'visual.reference_activation','code':'rebind-selected-media'})
    import execution_choices
    pinned = copied['execution_choices']['selection']
    profile = pinned['profile']['path']
    plan = {key: copy.deepcopy(copied['execution_choices'][key]) for key in execution_choices.PLAN_FIELDS}
    for change in difference:
        field = rendered['fields'][change['field']]['field']
        if change['kind'] == 'parameter':
            name = '.'.join(field)
            row = next((r for r in plan['settings'] if r['field'] == name), None)
            if row is None:
                raise ValueError('variation parameter has no original setting choice')
            row.update(state='explicit', value=change['after'], recommendation=None, reason=reason)
        elif change['kind'] == 'content':
            channel = 'positive' if field == rendered['layout']['primary_text'] else 'negative'
            text = change['after']
            plan['segments'][channel] = [{'start': 0, 'end': len(text), 'text': text,
                                          'recommendation': None, 'reason': reason}]
    used = {execution_choices.entry_key(row['recommendation']) for row in plan['settings'] if row['recommendation'] is not None}
    used.update(execution_choices.entry_key(row['recommendation']) for rows in plan['segments'].values() for row in rows if row['recommendation'] is not None)
    for decision in plan['recommendations']:
        if decision['decision'] == 'adopt' and (decision['guidance'], decision['entry']) not in used:
            decision.update(decision='reject', reason=reason)
    plan['context']['input_modes'] = sorted({i['mode'] for i in copied['inputs'] if 'mode' in i})
    subjects={}
    for ident,item in visual['subjects'].items():
        selectors=[]
        for ref in item['identity_refs']:
            selected=copy.deepcopy(ref)
            selected['file']={'path':ref['file']['path']}
            if ref['adoption']['kind']=='production-selection':
                import production_workflow as w
                prior=w.load_run(root,ref['adoption']['run'])[3]
                matches=[r for r in prior if r['event']=='selection' and r['sha256']==ref['adoption']['selection_sha256']]
                if len(matches)!=1:raise ValueError('selected adoption has no unique recorded selection')
                selected['adoption']={'kind':'production-selection','run':ref['adoption']['run'],'selection':matches[0]['sha256']}
            elif ref['adoption']['kind']=='public-receipt':
                for key in ('manifest','receipt'):selected['adoption'][key]={'path':ref['adoption'][key]['path']}
            selectors.append(selected)
        subjects[ident]={**item,'identity_refs':selectors}
    def selection(ref):return {k:ref[k] for k in ('path','locator') if k in ref} if ref else None
    choices['visual']={'purpose':visual['purpose'],'basis':selection(visual['basis']), 'subjects':subjects,
        'shot_camera':selection(visual['shot_camera']),'shot_request':selection(visual['shot_request']),
        'reference_activation':selection(visual['reference_activation']),'submission':out+'/submission-source.json'}
    choices['validation']={'mode':validation['mode'],'submission':out+'/submission-source.json','target_profile':profile,
        'service_profiles':pinned['service_profiles']['path'], 'guidance': [ref['path'] for ref in pinned['guidance']],
        'execution': plan, 'contract':validation['contract']['path'],
        'evidence':validation['evidence']['path'],'execution_policy':validation['execution_policy']['path'] if validation['execution_policy'] else None}
    # The ordinary builder reattaches current records; old hashes are never approvals.
    for key in ('request_validation','request_validation_sha256','input_snapshots','input_snapshots_sha256',
                'visual_continuity','visual_continuity_sha256','route_reading','execution_choices','execution_choices_sha256','visual_language'):copied.pop(key,None)
    files['submission-source.json']=c.encoded(copied);files['delivery.txt']=copied['text'].encode('utf-8')
    delivery=task['delivery']['path'];task['delivery']['path']=out+'/delivery.txt'
    for item in task['sources']:
        if item['path']==manifest['spec_path']:item['path']=out+'/submission-source.json'
        if item['path']==delivery:item['path']=out+'/delivery.txt'
    actions=[{'operation':'dispatch-preview','script':'scripts/dispatch.py',
        'args':{'root':str(root),'service-profiles':str(root/manifest['service_path'])},
        'requires':['formal submission from build-inputs','new production run'],
        'external_effect':False,'budget_effect':'none'}]
    return files,choices,task,actions,issues
