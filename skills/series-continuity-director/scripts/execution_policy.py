"""Resolve local execution policy and preserve its original byte witnesses."""
from __future__ import annotations
from pathlib import Path
import execution_contract as c
from input_evidence import InputEvidence


def load_policy(record:dict|None,reader:InputEvidence,target:dict,*,dialect:str|None=None)->tuple[dict,InputEvidence]:
    ref=(record or {}).get('execution_policy')
    if ref is None:return {},reader
    value=reader.json(ref);local=reader.at(ref)
    required={'artifact_type','target','text_dialect','production_context_transport','reference_instruction_transport','basis','controls'}
    optional={'label','observed_at','parameter_observations','reference_schemas','host_interface'}
    if not isinstance(value,dict) or set(value)-required-optional or not required<=set(value):raise ValueError('invalid local execution policy fields')
    if value['artifact_type']!='execution-policy' or value['target']!=target:raise ValueError('execution policy target mismatch')
    c.text(value['text_dialect'],'explicit text dialect');local.basis(value['basis'])
    if dialect is not None and value['text_dialect']!=dialect:raise ValueError('execution policy text dialect differs from the selected model record')
    if value['production_context_transport'] not in {'none','prompt-prefix'}:raise ValueError('unknown production context transport')
    controls = value['controls']
    if not isinstance(controls, list):
        raise ValueError('execution policy controls must be an explicit array')
    from request_contract import path_parts, overlaps
    paths = []
    for control in controls:
        c.exact(control, {'field', 'availability', 'allow_provider_managed', 'reason'}, 'operation control')
        path = path_parts(control['field'])
        if any(overlaps(path, previous) for previous in paths):
            raise ValueError('operation controls overlap')
        paths.append(path)
        if control['availability'] not in {'selectable', 'not-applicable', 'not-exposed'} or type(control['allow_provider_managed']) is not bool:
            raise ValueError('operation control availability is invalid')
        c.text(control['reason'], 'operation control reason')
    if value['reference_instruction_transport'] is not None:
        c.exact(value['reference_instruction_transport'],{'mode','contract'},'reference instruction policy')
    return value,local
