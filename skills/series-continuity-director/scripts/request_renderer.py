"""Build one submission request from explicit target, policy and reference records."""
from __future__ import annotations
import copy
from pathlib import Path
import execution_contract as c
import request_contract as rc
import model_rendition
import runtime_evidence
from execution_policy import load_policy


def submission(spec:dict,profile:dict,offering:dict,service:dict,transport,*,root:Path,consumer:dict|None=None)->dict:
    record=spec['request_validation'];reader=runtime_evidence.reader(root,snapshots=copy.deepcopy(spec['input_snapshots']))
    target={'service':spec['service'],'model_identifier':spec['model'],'operation':spec['operation']}
    if target!=record['target'] or target['model_identifier']!=offering['model_identifier']:
        raise ValueError('submission target differs from the selected execution contract')
    policy,local=load_policy(record,reader,target)
    rows=[];visual=spec['visual_continuity']
    if visual['reference_activation'] is not None:
        from reference_activation_gate import settle
        from reference_carriers import delivered
        activation=reader.json(visual['reference_activation']);settled=settle(activation,root)
        if settled['errors']:raise ValueError('reference activation refuses this submission')
        package=settled['package'];locations=delivered(package,root=root,package_dir=c.local(root,activation['package']).parent,inputs=spec['inputs'])
        for ref,location in zip(package['selected_references'],locations,strict=True):
            rows.append({'reference_number':location['reference_number'],'attachment_number':location['input_index']+1,
                'region_pixels':location['region_pixels'],'role':ref['role'],
                'controls':ref['authority']['controls'],'must_not_control':ref['authority']['must_not_control']})
    composed=model_rendition.compose(spec['text'],segments=None,authored_source={'kind':'submission-rendition','sha256':c.digest(spec['text'].encode('utf-8'))},
        bindings=rows,reference_policy=policy.get('reference_instruction_transport'),production_consumer=consumer,
        context_policy=policy.get('production_context_transport'),policy_source=record['execution_policy'],reader=local,target=target,
        dialect=policy.get('text_dialect'))
    resolved=copy.deepcopy(spec);resolved.update(text=composed['text'],_prompt_trace=composed['trace'],_native_reference_controls=composed['native_reference_controls'])
    compiled=transport.compile_request(resolved,offering,service,{})
    paths=transport.media_paths(spec,offering)
    if paths!=[x['path'] for x in spec['inputs']]:raise ValueError('transport reorders or omits submitted media')
    media=[rc.media_metadata(c.local(root,item['path']),role=item['role'],
        binding_ids=['reference:'+str(r['reference_number']) for r in rows if r['attachment_number']==i+1]) for i,item in enumerate(spec['inputs'])]
    execution=rc.execution_hashes(service,offering,Path(transport.__file__),model=profile,policy=policy)
    context={'subjects':visual['subjects'],'purpose':visual['purpose'],'output_kind':spec['output_kind']}
    rendered=rc.seal(compiled['request'],compiled['layout'],media,target,execution,compiled['request_trace'],rows,context)
    return {'rendered':rendered,'review_requirements':composed['review_requirements'],'input_snapshots':reader.snapshots}


def envelope_fields(rendered:dict)->list[list]:
    """Only the adapter's declared management and operation fields are overlay slots."""
    return [*rendered['layout']['management'],rendered['layout']['operation']]


def check_final(record:dict,reader,rendered:dict,*,known_schema:dict|None=None)->dict:
    from request_validation import require
    return require(record,reader,expected_target=rendered['sealed']['target'],execution=rendered['sealed']['execution'],
        rendered=rendered,envelope_fields=envelope_fields(rendered),known_schema=known_schema)
