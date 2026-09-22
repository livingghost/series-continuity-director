"""Bind explicit visual subjects to adopted media and delivered reference bytes."""
from __future__ import annotations
import copy
from pathlib import Path
from typing import Any
import execution_contract as c

CONTINUITIES = {'recurring', 'one-off', 'undecided'}
VISUAL_KINDS = {'image', 'video', 'video-with-audio'}


def file_ref(root: Path, path: str, *, locator: str | None = None) -> dict:
    value = {'path': path, 'sha256': c.digest(c.read(c.local(root, path)))}
    if locator is not None: value['locator'] = c.text(locator, 'source locator')
    return value


def check_file(root: Path, value: Any, *, basis: bool = False) -> Path:
    c.exact(value, {'path', 'sha256'} | ({'locator'} if basis else set()), 'source reference')
    c.sha(value['sha256'])
    if basis: c.text(value['locator'], 'source locator')
    path = c.local(root, value['path'])
    if c.digest(c.read(path)) != value['sha256']: raise ValueError('source bytes changed: ' + value['path'])
    return path


def validate_content(value: Any, *, kind: str) -> None:
    c.exact(value, {'purpose', 'basis', 'subjects', 'shot_camera', 'shot_request', 'reference_activation'}, 'visual continuity')
    if value['purpose'] not in {'sheet-panel', 'image', 'video', 'nonvisual'}:
        raise ValueError('declare the output purpose')
    if not isinstance(value['subjects'], dict): raise ValueError('subjects must be an ID-keyed object')
    visual = value['purpose'] != 'nonvisual'
    if not visual:
        if value['subjects'] or any(value[x] is not None for x in ('basis','shot_camera','shot_request','reference_activation')):
            raise ValueError('nonvisual output has no visual subjects or selectors')
        return
    c.exact(value['basis'], {'path','sha256','locator'}, 'visual basis')
    for key in ('path','locator'): c.text(value['basis'][key], key)
    c.sha(value['basis']['sha256'])
    for key in ('shot_camera','shot_request','reference_activation'):
        ref = value[key]
        if ref is not None:
            c.exact(ref, {'path','sha256'}, key); c.text(ref['path'], key); c.sha(ref['sha256'])
    if kind == 'shot' and (value['shot_camera'] is None or value['shot_request'] is None):
        raise ValueError('a visual shot needs its camera and shot request')
    if kind == 'asset' and (value['shot_camera'] is not None or value['shot_request'] is not None):
        raise ValueError('an asset does not borrow a shot camera or request')
    if kind not in {'shot','asset'}: raise ValueError('declare shot or asset')
    count = len(value['subjects'])
    if value['purpose'] == 'sheet-panel' and count != 1: raise ValueError('a sheet panel needs exactly one subject')
    for ident, item in value['subjects'].items():
        c.text(ident, 'subject ID')
        c.exact(item, {'continuity','character_id','identity_refs'}, 'visual subject')
        if item['continuity'] not in CONTINUITIES: raise ValueError(ident + ': explicitly select a continuity')
        if item['continuity'] == 'undecided' and count != 1: raise ValueError(ident + ': undecided subjects require single-subject exploration')
        if item['character_id'] is not None: c.text(item['character_id'], 'character ID')
        if item['continuity'] == 'recurring' and item['character_id'] is None: raise ValueError(ident + ': a recurring subject needs its character ID')
        if not isinstance(item['identity_refs'], list): raise ValueError(ident + ': identity_refs must be an array')
        if count > 1 and item['continuity'] == 'recurring' and not item['identity_refs']:
            raise ValueError(ident + ': select an adopted identity before a multiple-subject generation')
        seen = set()
        for ref in item['identity_refs']:
            c.exact(ref, {'registry','file','activation_reference','adoption'}, 'identity selector')
            c.exact(ref['registry'], {'owner_path','asset_id','role'}, 'registry selector')
            for x in ref['registry'].values(): c.text(x, 'registry identifier')
            c.exact(ref['file'], {'path','sha256'}, 'identity image'); c.text(ref['file']['path'], 'identity path'); c.sha(ref['file']['sha256'])
            name = c.text(ref['activation_reference'], 'activation reference ID')
            if name in seen: raise ValueError('duplicate identity activation: ' + name)
            seen.add(name)
            adoption = ref['adoption']
            if not isinstance(adoption, dict): raise ValueError('identity adoption selector required')
            if adoption.get('kind') == 'production-selection':
                c.exact(adoption, {'kind','run','selection_sha256'}, 'production selection')
                c.text(adoption['run'], 'adoption run'); c.sha(adoption['selection_sha256'])
            elif adoption.get('kind') == 'public-receipt':
                c.exact(adoption, {'kind','manifest','receipt','candidate_id'}, 'public adoption')
                for k in ('manifest','receipt'):
                    c.exact(adoption[k], {'path','sha256'}, k); c.sha(adoption[k]['sha256']); c.text(adoption[k]['path'], k)
                c.text(adoption['candidate_id'], 'candidate ID')
            else: raise ValueError('select a production selection or a public adoption receipt')
    if any(x['identity_refs'] for x in value['subjects'].values()) and value['reference_activation'] is None:
        raise ValueError('identity references require their activation')


def decided_subject(root: Path, subject: dict, decision: Any) -> dict:
    if decision is not None:
        c.exact(decision, {'character_id','continuity','basis','by','at'}, 'continuity decision')
        c.text(decision['character_id'], 'decision character'); c.text(decision['by'], 'decision author'); c.text(decision['at'], 'decision time')
        if decision['continuity'] not in {'recurring','one-off'}: raise ValueError('identity adoption requires an author decision')
        check_file(root, decision['basis'], basis=True)
        if subject['character_id'] not in {None, decision['character_id']}: raise ValueError('decision names another character')
        return {**subject, 'character_id': decision['character_id'], 'continuity': decision['continuity']}
    if subject['continuity'] == 'undecided' or subject['character_id'] is None:
        raise ValueError('the candidate requires an explicit author continuity decision before identity adoption')
    return subject


def selection_subject(root: Path, run: str, selection: dict, *, loaded: tuple | None = None) -> dict:
    """Read single-subject provenance or the recorded visual inspection of an import."""
    import production_workflow as w
    directory, prepared, consumer, rows = loaded or w.load_run(root, run)
    candidate = w.find(rows, 'candidate', selection['candidate'])
    reviewed = w.find(rows, 'review', selection['review'])
    if reviewed['data']['candidate'] != candidate['sha256']: raise ValueError('identity review names another candidate')
    w.eligible(prepared, reviewed)
    review = reviewed['data']['review']; visual = None
    candidate_files = {x['sha256'] for x in candidate['data']['files']}
    outputs = [x for x in rows if x['event'] == 'dispatch-results' and candidate_files.intersection(f['sha256'] for f in x['data']['files'])]
    if outputs:
        if len(outputs) != 1: raise ValueError('candidate has ambiguous dispatch provenance')
        claim = w.find(rows, 'dispatch-claim', outputs[0]['data']['claim'])
        manifest = claim['data']['manifest']
        if c.content_id(manifest) != claim['data']['manifest_sha256']: raise ValueError('candidate request manifest changed')
        visual = manifest['spec']['visual_continuity']
        validate_content(visual, kind=manifest['spec']['kind'])
        if len(visual['subjects']) != 1: raise ValueError('identity adoption requires a single-subject generation')
        subject = next(iter(visual['subjects'].values()))
    else:
        assessment = review.get('visual_assessment')
        if not isinstance(assessment, dict) or len(assessment['subjects']) != 1:
            raise ValueError('an imported identity requires a recorded single-subject visual assessment')
        subject = next(iter(assessment['subjects'].values()))
    return decided_subject(root, subject, selection.get('continuity_decision'))


def _local_adoption(root: Path, selector: dict, adoption: dict, character: str | None) -> dict:
    import production_workflow as w
    loaded = w.load_run(root, adoption['run']); directory,p,_,rows = loaded
    record = w.find(rows, 'selection', adoption['selection_sha256']); selection = record['data']['selection']
    if selection['scope'] != 'registry-adoption' or selection['adoption'] != selector['registry'] or selection.get('influence') != 'identity':
        raise ValueError('the selection does not adopt this registry entry for identity')
    candidate = w.find(rows, 'candidate', selection['candidate'])
    if not any(f['path'] == selector['file']['path'] and f['sha256'] == selector['file']['sha256'] for f in candidate['data']['files']):
        raise ValueError('the selected candidate is not the requested identity image')
    current_reviews = [r for r in rows if r['event'] == 'review' and r['data']['candidate'] == selection['candidate']]
    if not current_reviews or current_reviews[-1]['sha256'] != selection['review']:
        raise ValueError('identity selection does not name its current review')
    subject = selection_subject(root, adoption['run'], selection, loaded=loaded)
    if character is not None and subject['character_id'] != character: raise ValueError('the adopted candidate belongs to another character')
    return {'character_id': subject['character_id'], 'continuity': subject['continuity'], 'selection_sha256': record['sha256']}


def adopted_identity(root: Path, selector: dict, *, character: str | None, story_point: int | None) -> dict:
    import production_workflow as w
    check_file(root, selector['file'])
    w.confirm_asset_adoption(root, selector['registry'], selector['file'])
    adoption = selector['adoption']
    if adoption['kind'] == 'production-selection': return _local_adoption(root, selector, adoption, character)
    from reference_activation_gate import file_ref as public_file
    manifest = public_file(root, adoption['manifest']); receipt = public_file(root, adoption['receipt'])
    if manifest['artifact_type'] != 'candidate-manifest' or receipt['artifact_type'] != 'adoption-receipt': raise ValueError('wrong public adoption artifact types')
    if receipt['candidate_manifest_sha256'] != manifest['candidate_manifest_sha256'] or receipt['character_id'] != manifest['character_id']:
        raise ValueError('adoption receipt and candidate manifest disagree')
    if character is not None and receipt['character_id'] != character: raise ValueError('public adoption names another character')
    candidate = [x for x in manifest['candidates'] if x['candidate_id'] == adoption['candidate_id']]
    decisions = [x for x in receipt['adoptions'] if x['candidate_id'] == adoption['candidate_id']]
    if len(candidate) != 1 or len(decisions) != 1: raise ValueError('public adoption must identify one candidate and decision')
    candidate, decision = candidate[0], decisions[0]
    if decision['status'] != 'adopted' or decision['asset_registry_id'] != selector['registry']['asset_id']:
        raise ValueError('the public receipt does not adopt the selected registry entry')
    if candidate['file_sha256'] != selector['file']['sha256']: raise ValueError('public candidate and imported image bytes differ')
    span = decision['effective_story_range']
    if story_point is None or story_point < span['from_order'] or (span['to_order'] is not None and story_point > span['to_order']):
        raise ValueError('public adoption is not established for this story order')
    # Import acceptance is a local production selection, not the receipt's mere presence.
    matches = []
    production = c.local(root, 'production', exists=False)
    if production.exists():
        for directory in sorted(production.iterdir()):
            if directory.name.startswith('.pending-'): continue
            _,_,_,records = w.load_run(root, directory.name)
            for record in records:
                if record['event'] != 'selection': continue
                selected = record['data']['selection']
                if selected['scope'] == 'registry-adoption' and selected['adoption'] == selector['registry'] and selected.get('influence') == 'identity':
                    local = {'kind':'production-selection','run':directory.name,'selection_sha256':record['sha256']}
                    proof = _local_adoption(root, selector, local, receipt['character_id'])
                    matches.append(proof)
    if not matches: raise ValueError('public reference must complete the local identity acceptance workflow')
    return {'character_id': receipt['character_id'], 'continuity': matches[-1]['continuity'],
            'receipt_sha256': receipt['adoption_receipt_sha256'], 'local_selections': matches}


def require(value: Any, *, submission: dict, root: Path, profile: dict | None = None) -> dict:
    validate_content(value, kind=submission.get('kind'))
    kinds = set((profile or {}).get('media_kind') or [])
    purpose = value['purpose']
    declared = submission.get('output_kind')
    if purpose == 'nonvisual':
        actual = {declared} if declared is not None else kinds
        if not actual or actual & VISUAL_KINDS or not actual.issubset({'audio','text'}):
            raise ValueError('nonvisual output requires an explicit supported nonvisual output kind')
        if declared is not None and kinds and declared not in kinds: raise ValueError('output kind is not declared by this target')
        return {'subjects':0, 'identity_bindings':[], 'unmeasured':[]}
    expected_kind = 'video' if purpose == 'video' else 'image'
    if kinds and not ({expected_kind} & kinds or expected_kind == 'video' and 'video-with-audio' in kinds):
        raise ValueError('visual purpose does not match the target output kind')
    if declared is not None and declared not in ({'video','video-with-audio'} if expected_kind=='video' else {'image'}):
        raise ValueError('declared output kind differs from the visual purpose')
    check_file(root, value['basis'], basis=True)
    shot_request = None
    if submission['kind'] == 'shot':
        from reference_activation_gate import file_ref as public_file
        camera = public_file(root, value['shot_camera']); shot_request = public_file(root, value['shot_request'])
        if camera['artifact_type'] != 'shot-camera-spec' or shot_request['artifact_type'] != 'shot-request':
            raise ValueError('visual shot needs the camera specification and generation request')
        if shot_request['camera_spec_sha256'] != camera['camera_spec_sha256']: raise ValueError('shot request and camera differ')
        for key in ('scene_id','shot_id'):
            if camera[key] != shot_request[key] or submission.get(key) != camera[key]: raise ValueError('shot identity mismatch: ' + key)
        if set(value['subjects']) != set(camera['visible_subjects']): raise ValueError('visual subjects must match the camera visible subjects')
        for ident, subject in value['subjects'].items():
            if subject['character_id'] != ident: raise ValueError('shot subject must retain its declared work character ID')
    evidence = []; unmeasured = []; settled = None; deliveries = []
    if value['reference_activation'] is not None:
        from reference_activation_gate import settle, reference_id
        activation_path = check_file(root, value['reference_activation'])
        activation = c.load(activation_path); settled = settle(activation, root)
        if settled['errors']: raise ValueError('reference activation refused: ' + '; '.join(x['message'] for x in settled['errors']))
        from reference_carriers import delivered
        deliveries = delivered(settled['package'], root=root, package_dir=settled['package_path'].parent, inputs=submission.get('inputs') or [])
        unmeasured.extend(settled['unmeasured'])
    for ident, subject in value['subjects'].items():
        for ref in subject['identity_refs']:
            name = ref['activation_reference']
            if settled is None or name not in settled['references']: raise ValueError(ident + ': identity reference is absent from the activation')
            use = settled['uses'].get(name)
            if not use or use.get('declined') or 'identity' not in use['settles']: raise ValueError(ident + ': activation does not use this reference for identity')
            selected = settled['references'][name]; row = selected['reference']; binding = selected['state_binding']
            if binding is None or 'identity' not in selected['influence']: raise ValueError(ident + ': identity authority and character binding must be measured')
            if binding['character_id'] != subject['character_id']: raise ValueError(ident + ': identity state binding belongs to another character')
            if any(x['reference'] == name and x['field'] in {'story_point','effective_story_range','state_binding'} for x in settled['unmeasured']):
                raise ValueError(ident + ': identity applicability is unmeasured')
            if shot_request is not None and shot_request['identity_contract_sha256_by_character'].get(ident) != binding['identity_contract_sha256']:
                raise ValueError(ident + ': reference identity contract differs from the shot request')
            if row['source']['sha256'] != ref['file']['sha256']: raise ValueError(ident + ': adopted image is not the selected reference source')
            proof = adopted_identity(root, ref, character=subject['character_id'], story_point=activation['story_point'])
            if proof['continuity'] == 'recurring' and subject['continuity'] != 'recurring': raise ValueError(ident + ': selected continuity conflicts with the current identity decision')
            position = list(settled['references']).index(name)
            if position >= len(deliveries): raise ValueError(ident + ': identity carrier is not in the actual submission')
            evidence.append({'subject_id':ident,'character_id':subject['character_id'],'adoption':proof, **deliveries[position]})
    return {'subjects':len(value['subjects']), 'identity_bindings':evidence, 'unmeasured':unmeasured}


def selection_choice(root: Path, choice: dict, registry: dict) -> dict:
    """Resolve an explicit run and selection identifier to its recorded identity evidence."""
    c.exact(choice, {'kind', 'run', 'selection'}, 'identity selection choice')
    if choice['kind'] != 'production-selection':
        raise ValueError('identity selection choice must name its recorded kind')
    c.text(choice['run'], 'selection run')
    c.text(choice['selection'], 'selection identifier')
    import production_workflow as workflow
    _, _, _, rows = workflow.load_run(root, choice['run'])
    matches = [row for row in rows if row['event'] == 'selection'
               and row['sha256'] == choice['selection']
               and row['data']['selection']['scope'] == 'registry-adoption'
               and row['data']['selection']['adoption'] == registry
               and row['data']['selection'].get('influence') == 'identity']
    if len(matches) != 1:
        raise ValueError('select one recorded identity adoption for this registry entry')
    return {'kind': 'production-selection', 'run': choice['run'],
            'selection_sha256': matches[0]['sha256']}


def build_record(choices: dict, *, submission: dict, root: Path, profile: dict | None = None) -> dict:
    result = copy.deepcopy(choices)
    for key in ('basis','shot_camera','shot_request','reference_activation'):
        value = result.get(key)
        if value is not None:
            fields = {'path','locator'} if key == 'basis' else {'path'}
            c.exact(value, fields, key + ' choice')
            result[key] = file_ref(root, value['path'], locator=value.get('locator'))
    for subject in result.get('subjects', {}).values():
        for ref in subject['identity_refs']:
            c.exact(ref['file'], {'path'}, 'identity image choice')
            ref['file'] = file_ref(root, ref['file']['path'])
            if ref['adoption']['kind'] == 'production-selection':
                ref['adoption'] = selection_choice(root, ref['adoption'], ref['registry'])
            elif ref['adoption']['kind'] == 'public-receipt':
                for key in ('manifest','receipt'):
                    c.exact(ref['adoption'][key], {'path'}, key + ' choice')
                    ref['adoption'][key] = file_ref(root, ref['adoption'][key]['path'])
    require(result, submission=submission, root=root, profile=profile)
    return result
