"""Synthetic transport: the suite's own test implementation of scripts/transport_contract.py.

It exists so the generic dispatch machinery is tested against a request shape
that no real service defines. It sends only to a loopback endpoint, so a service
record that names it can reach no remote service. Its shape:

- the request is one JSON object: `action` carries the operation, `engine` the
  model identifier, `prompt` the primary text, `avoid` the negative text and
  `count` the output count; `envelope.request_id` is the management field;
- each parameter or option is written at its own request key;
- inputs travel in order in `attachments`, each the id an upload returned;
- an upload is {"upload": base64, "media_type"} and answers {"upload_id"};
- an answer carries `outputs` ({"job", "location", "seed"}) and `problems`
  (refusals); a pending output has no `location` and is polled by {"poll": jobs};
- an exchange without an answer object is recorded as {"unknown": {...}}.

REQUEST_SHAPE is the `request_shape` an offering served by this transport declares.
"""
from __future__ import annotations

import base64
import json
import uuid
from typing import Any

import service_profile
import transport_contract as contract

REQUEST_SHAPE = {'model_key': 'engine', 'text_key': 'prompt', 'negative_text_key': 'avoid',
                 'media_reference': 'uuid', 'single_value_keys': []}


def _post(payload: dict[str, Any], service: dict[str, Any], key: str) -> dict[str, Any]:
    if not service_profile.is_loopback(service_profile.endpoint_url(service)):
        raise ValueError('the synthetic transport sends only to a loopback endpoint')
    exchange = contract.post_json(service, payload, {'X-Synthetic-Key': key})
    if exchange['outcome'] is None:
        return exchange['body']['json']
    if exchange['outcome'] == contract.REFUSED:
        return {'problems': [exchange]}
    return {'unknown': exchange}


def media_paths(spec: dict[str, Any], offering: dict[str, Any]) -> list[str]:
    return [str(item['path']) for item in spec.get('inputs') or []]


def compile_request(spec: dict, offering: dict, service: dict, media_ids: dict | None = None) -> dict:
    from request_contract import RequestWriter, path_parts, MANAGEMENT_VALUE, present
    operation = spec.get('operation')
    if operation not in service.get('operations', {}):
        raise ValueError('service does not declare the selected operation')
    model = spec.get('model') or offering['model_identifier']
    writer = RequestWriter()
    source = [{'kind': 'offering', 'service': spec['service'], 'model_identifier': model}]

    def write(path, value, kind, transform, bindings=None):
        writer.write(path, value, source_kind=kind, source_refs=source, transform_id=transform, binding_ids=bindings)

    write(['action'], operation, 'transport-envelope', 'operation')
    write(['envelope', 'request_id'], str(uuid.uuid4()), 'transport-envelope', 'request-identifier')
    write(['engine'], model, 'model-setting', 'model-identifier')
    write(['prompt'], spec['text'], 'authored', 'selected-rendition')
    if spec.get('_prompt_trace'):
        writer.trace = ([x for x in writer.trace if x['target_field'] != ['prompt']]
                        + [{**x, 'target_field': ['prompt']} for x in spec['_prompt_trace']])
    layout = {'model': ['engine'], 'operation': ['action'], 'primary_text': ['prompt'], 'negative_text': None,
              'output_count': ['count'], 'fixed_output_count': None, 'seed': None, 'media': [],
              'management': [['envelope', 'request_id']], 'content': [{'id': 'prompt', 'field': ['prompt']}],
              'fields': [{'id': 'model', 'field': ['engine'], 'kind': 'fixed'},
                         {'id': 'operation', 'field': ['action'], 'kind': 'fixed'},
                         {'id': 'prompt', 'field': ['prompt'], 'kind': 'content'}]}
    if spec.get('negative_text'):
        write(['avoid'], spec['negative_text'], 'authored', 'selected-negative-channel')
        layout['negative_text'] = ['avoid']
        layout['content'].append({'id': 'negative', 'field': ['avoid']})
        layout['fields'].append({'id': 'negative', 'field': ['avoid'], 'kind': 'content'})
    inputs = spec.get('inputs') or []
    if inputs:
        ids = [(media_ids or {}).get(item['path'], MANAGEMENT_VALUE) for item in inputs]
        write(['attachments'], ids, 'reference-binding', 'ordered-media', [f'attachment:{i + 1}' for i in range(len(inputs))])
        for index in range(len(inputs)):
            layout['media'].append({'index': index, 'field': ['attachments', index]})
            layout['fields'].append({'id': f'media:{index + 1}', 'field': ['attachments', index], 'kind': 'media'})
    for group in ('parameters', 'options'):
        for name, value in (spec.get(group) or {}).items():
            field = path_parts(name)
            write(field, value, 'model-setting', 'selected-' + group)
            layout['fields'].append({'id': {'count': 'count', 'seed': 'seed'}.get(name, 'parameter:' + name),
                                     'field': field, 'kind': 'parameter'})
            if name == 'seed':
                layout['seed'] = field
    for control in spec.get('_native_reference_controls', []):
        write(control['field'], control['value'], 'reference-binding', 'native-reference-controls', control['binding_ids'])
        layout['fields'].append({'id': control['id'], 'field': control['field'], 'kind': 'fixed'})
    if not present(writer.request, ['count']):
        raise ValueError('declare an explicit count before requesting authorization')
    return {'request': writer.request, 'layout': layout, 'request_trace': writer.trace}


def upload_bytes(data: bytes, media_type: str, service: dict, key: str) -> str:
    answer = _post({'upload': base64.b64encode(data).decode('ascii'), 'media_type': media_type}, service, key)
    if rejections(answer) or 'upload_id' not in answer:
        raise ValueError('the synthetic upload was refused or its outcome is unknown: ' + json.dumps(answer))
    return str(answer['upload_id'])


def send(request: dict[str, Any], service: dict[str, Any], key: str) -> dict[str, Any]:
    return _post(request, service, key)


def poll(task_ids: list[str], service: dict[str, Any], key: str) -> dict[str, Any]:
    return _post({'poll': list(task_ids)}, service, key)


def rejections(answer: dict[str, Any]) -> list:
    problems = answer.get('problems')
    return list(problems) if isinstance(problems, list) else []


def results(answer: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = answer.get('outputs')
    return [{'url': item.get('location'), 'seed': item.get('seed'), 'id': item.get('job'),
             'pending': item.get('location') is None}
            for item in (outputs if isinstance(outputs, list) else []) if isinstance(item, dict)]


def observation_outcome(answer: dict[str, Any]) -> str:
    if rejections(answer):
        return contract.REFUSED
    if answer.get('unknown') is not None:
        return contract.UNKNOWN
    return contract.ACCEPTED if results(answer) else contract.UNKNOWN
