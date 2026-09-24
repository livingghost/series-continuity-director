"""Resolve input choices through project artifacts and explicit target profiles."""
from __future__ import annotations

import copy
from pathlib import Path

import execution_contract as c
import request_contract
import request_validation
import visual_continuity
from execution_policy import load_policy


def check_series(before: dict, after: dict) -> None:
    # The project workflow owns revision relationships within the work task.
    return None


def inventory(root: Path, task: dict) -> dict:
    import asset_registry
    paths = ['asset-registry.md']
    paths.extend(source['path'] for source in task.get('sources', [])
                 if source.get('role') == 'asset-registry')
    registries = []
    for name in dict.fromkeys(paths):
        path = c.local(root, name, exists=False)
        if path.is_file():
            records = asset_registry.parse(c.read(path).decode('utf-8'))
            registries.append({'owner_path': name, 'records': records})
    import production_workflow as workflow
    selections = []
    for run in workflow.run_ids(root):
        _, _, _, rows = workflow.load_run(root, run)
        for row in rows:
            if row['event'] != 'selection':
                continue
            selection = row['data']['selection']
            if selection['scope'] == 'registry-adoption' and selection.get('influence') == 'identity':
                selections.append({'run': run, 'selection': row['sha256'], 'candidate': selection['candidate'],
                                   'registry': selection['adoption']})
    return {'declared_sources': [{key: source.get(key) for key in ('id', 'role', 'path')}
                                  for source in task.get('sources', [])],
            'registries': registries, 'identity_selections': selections,
            'selection': 'Select exact project registry, candidate and activation identifiers.'}


def authority(root: Path, task: dict, saved: dict | None) -> dict:
    if saved is None:
        return {'present': False, 'eligibility_evaluated': False}
    import production_workflow as workflow
    _, _, _, rows = workflow.load_run(root, saved['run'])
    return {'present': any(row['event'] == 'authorization' for row in rows),
            'records': [{'sha256': row['sha256'], 'event': row['event']}
                        for row in rows if row['event'] in {'authorization', 'revocation'}],
            'eligibility_evaluated': False}


def _not_applicable(choices: dict, task: dict, field: str) -> bool:
    if choices.get('applicability') != 'not-applicable':
        return False
    c.exact(choices, {'applicability', 'reason'}, field + ' applicability choice')
    c.text(choices['reason'], field + ' applicability reason')
    if task['route'] == 'media':
        raise ValueError('a media production requires explicit visual and validation inputs')
    return True


def build_visual(choices: dict, task: dict, reader, root: Path) -> tuple[dict | None, dict]:
    if _not_applicable(choices, task, 'visual'):
        return None, {}
    c.exact(choices, {'purpose', 'basis', 'subjects', 'shot_camera', 'shot_request',
                      'reference_activation', 'submission'}, 'visual input choices')
    submission_ref = reader.select(choices['submission'])
    submission = reader.json(submission_ref)
    selected = {key: copy.deepcopy(value) for key, value in choices.items() if key != 'submission'}
    result = visual_continuity.build_record(selected, submission=submission, root=root)
    for key in ('basis', 'shot_camera', 'shot_request', 'reference_activation'):
        if result[key] is not None:
            if key == 'basis':
                reader.basis(result[key])
            else:
                reader.read(result[key])
    for subject in result['subjects'].values():
        for ref in subject['identity_refs']:
            reader.read(ref['file'])
            if ref['adoption']['kind'] == 'public-receipt':
                reader.read(ref['adoption']['manifest'])
                reader.read(ref['adoption']['receipt'])
    return result, {'submission': submission_ref, 'spec': submission}


def build_validation(choices: dict, task: dict, reader, root: Path) -> tuple[dict | None, dict]:
    if _not_applicable(choices, task, 'validation'):
        return None, {}
    c.exact(choices, {'mode', 'submission', 'target_profile', 'service_profiles',
                      'contract', 'evidence', 'execution_policy', 'guidance', 'execution'}, 'validation input choices')
    submission_ref = reader.select(choices['submission'])
    spec = reader.json(submission_ref)
    target = request_contract.target({key: spec.get(field) for key, field in
                                       [('service', 'service'), ('model_identifier', 'model'), ('operation', 'operation')]})
    profile_ref = reader.select(choices['target_profile'])
    profile = reader.json(profile_ref)
    from target_protocol import validate_profile
    checked = validate_profile(profile)
    if not checked['ok']:
        raise ValueError('selected target profile violates its public artifact contract: ' + str(checked['errors']))
    if profile.get('target_id') != spec['target']:
        raise ValueError('target profile does not match the exact submission target ID')
    offerings = [offering for offering in profile.get('offerings', [])
                 if offering.get('service') == target['service']
                 and offering.get('model_identifier') == target['model_identifier']]
    if len(offerings) != 1:
        raise ValueError('select a target with one exact service and model offering')
    offering = offerings[0]
    service_ref = reader.select(choices['service_profiles'])
    data = reader.json(service_ref)
    services = data.get('services')
    if not isinstance(services, dict) or target['service'] not in services:
        raise ValueError('service-profiles has no exact selected service')
    service = services[target['service']]
    if target['operation'] not in service.get('operations', {}):
        raise ValueError('the selected service does not declare this operation')
    import transport_contract
    transport = transport_contract.load(service)
    policy_ref = reader.select(choices['execution_policy']) if choices['execution_policy'] is not None else None
    policy, local = load_policy({'execution_policy': policy_ref}, reader, target)
    reference = policy.get('reference_instruction_transport')
    if reference is not None:
        contract = local.json(reference['contract'])
        local.at(reference['contract']).basis(contract['basis'])
    execution = request_contract.execution_hashes(service, offering, Path(transport.__file__), model=profile, policy=policy)
    selected = {key: choices[key] for key in ('mode', 'contract', 'evidence', 'execution_policy')}
    value = request_validation.build_record(selected, reader, expected_target=target, execution=execution)
    import execution_choices
    guidance_refs = [reader.select(path) for path in choices['guidance']]
    chosen = execution_choices.build(choices['execution'], reader, spec=spec, profile_ref=profile_ref,
                                     service_ref=service_ref, guidance_refs=guidance_refs, policy=policy)
    resolved = execution_choices.resolve(chosen, reader, spec=spec, policy=policy)
    return value, {'submission': submission_ref, 'target_profile': profile_ref, 'service_profiles': service_ref,
                   'execution_choices': chosen, 'resolved_choices': resolved}


def cross_check(visual: dict, validation: dict) -> None:
    if visual and validation and visual['submission'] != validation['submission']:
        raise ValueError('visual and validation choices refer to different submissions')


def attach_outputs(content: dict, visual, validation, context: dict, reader, out_dir: str) -> None:
    if visual is None and validation is None:
        return
    if visual is None or validation is None or 'spec' not in context:
        raise ValueError('a model submission needs both visual and validation choices')
    import input_contracts
    spec = copy.deepcopy(context['spec'])
    import execution_choices
    import production_direction
    import visual_language
    task = content['production-task.json']
    visual_language.require_for_output(task['direction']['visual_language'], spec['output_kind'])
    spec['visual_language'] = visual_language.compile_selection(task['direction']['visual_language'], task['direction']['decisions'])
    execution_choices.attach(spec, context['execution_choices'], context['resolved_choices'])
    spec['route_reading'] = content['route-reading.json']
    spec['visual_continuity'] = visual
    spec['visual_continuity_sha256'] = c.content_id(visual)
    input_contracts.attach(spec, validation, reader)
    content['submission.json'] = spec
    source = context['submission']['path']
    for item in content['production-task.json']['sources']:
        if item['path'] == source:
            item['path'] = (Path(out_dir) / 'submission.json').as_posix()


def next_actions(inputs: dict, task: dict, root: Path, *, runtime_arguments: dict | None = None) -> list[dict]:
    return [{'operation': 'prepare', 'args': {'root': str(root), 'task': inputs['production-task']['path']},
             'external_effect': False, 'budget_effect': 'none',
             'requires': ['Complete the authored source and delivery selections.']}]


def add_runtime_arguments(parser) -> None:
    from target_protocol import add_selection_arguments
    add_selection_arguments(parser)


def configure_runtime(args, parser) -> dict | None:
    if not getattr(args, 'target', None):
        return None
    from target_protocol import description_from_args
    return {'target_info': description_from_args(args)}


def visual_template(task: dict) -> dict | None:
    if task.get('route') != 'media':
        return None
    return {'purpose': None, 'basis': None, 'subjects': None, 'shot_camera': None,
            'shot_request': None, 'reference_activation': None, 'submission': None}


def validation_template(task: dict) -> dict | None:
    if task.get('route') != 'media':
        return None
    return {'mode': None, 'submission': None, 'target_profile': None, 'service_profiles': None,
            'contract': None, 'evidence': None, 'execution_policy': None, 'guidance': [], 'execution': None}


OPTIONAL_FIELDS = {'visual': {'basis', 'shot_camera', 'shot_request', 'reference_activation'},
                   'validation': {'execution_policy'}}


def unresolved_choices(choices: dict) -> list[dict]:
    """Describe unanswered selection fields without filling any authored value."""
    output = []
    for field in ('visual', 'validation'):
        value = choices.get(field)
        if not isinstance(value, dict) or value.get('applicability') == 'not-applicable':
            continue
        template = visual_template({'route': 'media'}) if field == 'visual' else validation_template({'route': 'media'})
        for key in template:
            if key in OPTIONAL_FIELDS[field]:
                continue
            if key in value and value[key] is None:
                output.append({'field': field + '.' + key, 'code': 'selection-required'})
        basis = value.get('basis')
        if isinstance(basis, dict):
            for key in ('path', 'locator'):
                if not basis.get(key):
                    output.append({'field': field + '.basis.' + key, 'code': 'source-selection-required'})
        target = value.get('target')
        if isinstance(target, dict):
            for key in ('service', 'model_identifier', 'operation'):
                if not target.get(key):
                    output.append({'field': field + '.target.' + key, 'code': 'target-selection-required'})
    return output
