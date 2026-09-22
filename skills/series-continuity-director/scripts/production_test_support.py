"""Synthetic current-form fixtures. Never represents real user authorization."""
from pathlib import Path
import execution_contract as c

def direction(task, instructions):
    return {'purpose':'Exercise this declared synthetic production task.',
      'intended_effect':'Known fixture behavior; not evidence of audience effect.',
      'basis':[{'source':s['id'],'applicability':'Applicable synthetic premise, retained in full.'} for s in task['sources'] if s['disposition']=='applied'],
      'decisions':[{'id':'realization','question':'How is this fixture realized?','compare':False,
        'options':[{'id':'specified','realization':instructions,'consequence':'A measured fixture, not proof of artistic merit.'}],
        'selected':'specified','reason':'Explicit fixture requirement.', 'criteria':[x['id'] for x in task['criteria']]}],
      'departures':[],'action_context':None,'verification_limits':['Synthetic tests do not demonstrate acting or audience response.']}

def grant(workflow, root, run, actor='synthetic selector', operations=('select',), outputs=0, calls=10, cost='0',currency='none',stop_conditions=None):
    name='grant-'+c.new_run_id()
    data=workflow.draft_authorization(root,run)
    data.update(principal='SYNTHETIC TEST PRINCIPAL, NOT USER CONSENT',actor=actor,purpose='Only this synthetic test.',
        permissions=[{'operation':op,'scopes':['task'],'max_calls':calls,'max_outputs':outputs,'max_cost':cost,'currency':currency, 'request_scope': None, 'submission_validation_modes': (['target-schema', 'bounded-probe', 'observed-profile'] if op == 'submit' else [])} for op in operations],
        evidence={'path':name+'.txt','locator':'whole'})
    if stop_conditions is not None:data['stop_conditions']=list(stop_conditions)
    (root/(name+'.txt')).write_text('SYNTHETIC AUTHORITY FIXTURE. NOT A HUMAN APPROVAL.\n',encoding='utf-8')
    (root/(name+'.json')).write_bytes(c.encoded(data))
    return workflow.authorize(root,run,name+'.json')['sha256']

def observed(data, text='The synthetic file was inspected.', method='text-inspection'):
    data.update(reviewer='synthetic reviewer',observations=[{'locator':{'kind':'whole'},'observation':text,'method':method}],conclusion='Synthetic integrity check only.')
    for check in data['checks']:check.update(verdict='pass',observation_indices=[0],evidence_basis='technical-measurement',reason='Actual synthetic fixture.')
    return data


def model_inputs(root, spec, service):
    """Capture an explicit synthetic interface for real offline dispatcher tests."""
    import input_contracts
    from input_evidence import InputEvidence
    import reading_fixtures
    import request_contract as rc
    import request_validation as rv
    import target_protocol
    import transport_runware
    offering = {'service': spec['service'], 'model_identifier': spec['model'],
                'request_keys': {}, 'constraints': {}, 'observed_at': '2000-01-01'}
    profile = target_protocol.finalize_profile({
        'artifact_type': 'target-profile', 'target_id': spec['target'],
        'label': 'Synthetic offline text return through an image request envelope',
        'model_identifier': spec['model'], 'media_kind': ['text'],
        'evidence': {'checked_on': '2000-01-01', 'sources': [
            {'kind': 'user-supplied', 'reference': 'Synthetic test interface. No live provider claim.'}]},
        'prompt_contract': {'layers': ['declared text']}, 'offerings': [offering]})
    target_protocol.validate_profile(profile)
    profiles = root/'profiles'; profiles.mkdir(exist_ok=True)
    (profiles/'fixture.json').write_bytes(c.encoded(profile))
    spec['output_kind'] = 'text'; spec['text_form'] = 'natural-language'
    spec['route_reading'] = reading_fixtures.fixture_reading(route='media', project=root)
    visual = {'purpose': 'nonvisual', 'basis': None, 'subjects': {},
              'shot_camera': None, 'shot_request': None, 'reference_activation': None}
    spec['visual_continuity'] = visual; spec['visual_continuity_sha256'] = c.content_id(visual)
    target = {'service': spec['service'], 'model_identifier': spec['model'], 'operation': spec['operation']}
    schema = {'type': 'object'}
    def save(name, value):
        raw = c.encoded(value); (root/name).write_bytes(raw)
        return {'path': name, 'sha256': c.digest(raw)}
    response = save('interface-response.json', {'schema': schema, 'synthetic': True})
    save('interface-acquisition.json', {'artifact_type': 'schema-acquisition', 'target': target,
        'source': {'kind': 'document', 'identifier': 'Synthetic offline interface', 'locator': 'schema'},
        'acquired_at': '2000-01-01T00:00:00Z', 'response': response,
        'status': {'document_status': 'schema-provided'}})
    save('interface-contract.json', {'artifact_type': 'model-schema-contract', 'target': target,
        'schema': schema, 'schema_sha256': c.content_id(schema), 'response_pointer': '/schema', 'local_overlay': None})
    reader = InputEvidence(root)
    execution = rc.execution_hashes(service, offering, Path(transport_runware.__file__), model=profile, policy={})
    record = rv.build_record({'mode': 'target-schema', 'contract': 'interface-contract.json',
        'evidence': 'interface-acquisition.json', 'execution_policy': None}, reader,
        expected_target=target, execution=execution)
    input_contracts.attach(spec, record, reader)
    return profile, offering, profiles


def model_decision(workflow, root, run, authorization, rendered):
    """Supply labeled fixture judgments, never used in normal command execution."""
    import production_request
    rows = workflow.load_run(root, run)[3]
    grant = workflow.find(rows, 'authorization', authorization)['data']['authorization']
    decision = production_request.draft_decision(rendered, actor=grant['actor'], conditions=grant['stop_conditions'])
    decision['rendition_review'].update(conclusion='satisfied', reason='Synthetic transport contract test only.')
    proof = dict(grant['evidence'])
    proof['sha256'] = c.digest(c.read(root/proof['path']))
    decision['principal_approval'] = {'request_sha256': rendered['request_sha256'],
        'principal': grant['principal'], 'evidence': proof}
    for assessment in decision['stop_assessments']:
        assessment.update(clear=True, reason='Explicit synthetic test condition; no real approval.')
    return decision
