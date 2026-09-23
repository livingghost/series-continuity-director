"""Runware transport: the Runware task API behind scripts/transport_contract.py.

The contract states the functions, the outcomes and the network rules. This
module adds only what is particular to Runware:

- a request is one task object sent in a JSON array, authorized by
  `Authorization: Bearer <key>`;
- `taskType` carries the operation, `taskUUID` the task identifier, `model` the
  model identifier, `positivePrompt` the primary text (or the spec's `text_key`),
  `negativePrompt` the negative text and `numberResults` the output count;
- an input is registered by an `imageUpload` task, or by a `mediaStorage`
  upload for audio and video, and its id comes back as `imageUUID`,
  `mediaUUID` or `mediaId`;
- an answer carries `data` (results with `imageURL`, `videoURL` or `audioURL`,
  `seed` and `taskUUID`) and `errors` (refusals);
- a pending task is polled with a `getResponse` task for its `taskUUID`.

When an exchange yields no Runware answer object, the recorded answer is
{"exchange": {...}}: the status, redirect location, complete body and reason
that `transport_contract.post_json` returned. A refused exchange also carries
`errors`.

REQUEST_SHAPE is the `request_shape` a Runware offering declares by default.
"""
from __future__ import annotations

import base64
import json
import uuid
from typing import Any

import transport_contract as contract

REQUEST_SHAPE = {'model_key': 'model', 'text_key': 'positivePrompt', 'media_reference': 'uuid',
                 'single_value_keys': []}


def _post(payload: list[dict[str, Any]], service: dict[str, Any], key: str) -> dict[str, Any]:
    exchange = contract.post_json(service, payload, {"Authorization": f"Bearer {key}"})
    if exchange['outcome'] is None:
        return exchange['body']['json']
    if exchange['outcome'] == contract.REFUSED:
        value = exchange['body'].get('json')
        errors = value.get('errors') if isinstance(value, dict) else None
        if not isinstance(errors, list) or not errors:
            errors = [{'code': f"http{exchange['status']}",
                       'message': exchange['body'].get('text', 'the service refused the request')}]
        return {'errors': errors, 'exchange': exchange}
    return {'exchange': exchange}


def media_paths(spec: dict[str, Any], offering: dict[str, Any]) -> list[str]:
    return [str(item["path"]) for item in spec.get("inputs") or [] if item.get("path")]


def _request_key(offering: dict, role: str, given: str | None) -> str:
    if given:return given
    mapped=(offering.get('request_keys') or {}).get(role)
    if not mapped:raise ValueError('input role has no exact request-key declaration: '+role)
    return mapped[0] if isinstance(mapped,list) else mapped


def compile_request(spec: dict, offering: dict, service: dict, media_ids: dict | None = None) -> dict:
    from request_contract import RequestWriter,path_parts,MANAGEMENT_VALUE,present
    operation=spec.get('operation')
    if operation not in service.get('operations',{}):raise ValueError('service does not declare the selected operation')
    writer=RequestWriter();media_ids=media_ids or {};source=[{'kind':'offering','service':spec['service'],'model_identifier':spec.get('model') or offering['model_identifier']}]
    def write(path,value,kind,transform,bindings=None):writer.write(path,value,source_kind=kind,source_refs=source,transform_id=transform,binding_ids=bindings)
    write(['taskType'],operation,'transport-envelope','operation');write(['taskUUID'],spec.get('task_uuid') or str(uuid.uuid4()),'transport-envelope','task-identifier')
    write(['model'],spec.get('model') or offering['model_identifier'],'model-setting','model-identifier')
    primary=path_parts(spec.get('text_key') or REQUEST_SHAPE['text_key']);write(primary,spec['text'],'authored','selected-rendition')
    if spec.get('_prompt_trace'):
        writer.trace=[x for x in writer.trace if x['target_field']!=primary]+[{**x,'target_field':primary} for x in spec['_prompt_trace']]
    layout={'model':['model'],'operation':['taskType'],'primary_text':primary,'negative_text':None,'output_count':['numberResults'],'fixed_output_count':None,
        'seed':None,'media':[],'management':[['taskUUID']],'content':[{'id':'prompt','field':primary}],
        'fields':[{'id':'model','field':['model'],'kind':'fixed'},{'id':'operation','field':['taskType'],'kind':'fixed'},
          {'id':'prompt','field':primary,'kind':'content'}]}
    if spec.get('negative_text'):
        field=path_parts(spec.get('negative_key') or 'negativePrompt');write(field,spec['negative_text'],'authored','selected-negative-channel')
        layout['negative_text']=field;layout['content'].append({'id':'negative','field':field});layout['fields'].append({'id':'negative','field':field,'kind':'content'})
    grouped={}
    for index,item in enumerate(spec.get('inputs') or []):
        key=_request_key(offering,item['role'],item.get('request_key'));field=path_parts(key)
        grouped.setdefault(tuple(field),[]).append((index,item))
    for key,entries in grouped.items():
        # A per-input array declaration is part of the current contract, not a role-name guess.
        array=any(item.get('request_array',False) for _,item in entries) or len(entries)>1
        values=[media_ids.get(item['path'],MANAGEMENT_VALUE) for _,item in entries]
        write(list(key),values if array else values[0],'reference-binding','ordered-media',[f'attachment:{i+1}' for i,_ in entries])
        for position,(index,item) in enumerate(entries):
            field=list(key)+[position] if array else list(key)
            layout['media'].append({'index':index,'field':field});layout['fields'].append({'id':f'media:{index+1}','field':field,'kind':'media'})
    for group in ('parameters','options'):
        for name,value in (spec.get(group) or {}).items():
            field=path_parts(name);write(field,value,'model-setting','selected-'+group)
            ident={'numberResults':'count','seed':'seed'}.get(name,'parameter:'+name)
            layout['fields'].append({'id':ident,'field':field,'kind':'parameter'})
            if name=='seed':layout['seed']=field
    for control in spec.get('_native_reference_controls',[]):
        write(control['field'],control['value'],'reference-binding','native-reference-controls',control['binding_ids'])
        layout['fields'].append({'id':control['id'],'field':control['field'],'kind':'fixed'})
    writer.defaults((offering.get('constraints') or {}).get('as_written') or {},source)
    if not present(writer.request,['numberResults']):raise ValueError('declare an explicit numberResults before requesting authorization')
    if not any(x['id']=='count' for x in layout['fields']):layout['fields'].append({'id':'count','field':['numberResults'],'kind':'parameter'})
    return {'request':writer.request,'layout':layout,'request_trace':writer.trace}


def upload_bytes(data: bytes, media_type: str, service: dict, key: str) -> str:
    """Send only the byte snapshot already checked by the authorized dispatcher."""
    from request_contract import MEDIA_TYPES
    if not isinstance(data, bytes) or media_type not in set(MEDIA_TYPES.values()):
        raise ValueError('upload requires verified bytes and a media type from the suite media table')
    payload = f"data:{media_type};base64," + base64.b64encode(data).decode("ascii")
    task = {"taskUUID": str(uuid.uuid4())}
    if media_type.split('/', 1)[0] in {"video", "audio"}:
        task.update({"taskType": "mediaStorage", "operation": "upload", "media": payload})
    else:
        task.update({"taskType": "imageUpload", "image": payload})
    answer = _post([task], service, key)
    if rejections(answer):
        raise ValueError(f"the service refused an upload: {json.dumps(rejections(answer), ensure_ascii=False)}")
    if 'exchange' in answer:
        raise ValueError(f"the upload outcome is unknown: {json.dumps(answer['exchange'], ensure_ascii=False)}")
    entry = (answer.get("data") or [{}])[0]
    identifier = entry.get("imageUUID") or entry.get("mediaUUID") or entry.get("mediaId") if isinstance(entry, dict) else None
    if not identifier:
        raise ValueError(f"an upload returned no identifier: {json.dumps(answer, ensure_ascii=False)}")
    return str(identifier)


def send(request: dict[str, Any], service: dict[str, Any], key: str) -> dict[str, Any]:
    return _post([request], service, key)


def rejections(answer: dict[str, Any]) -> list[dict[str, Any]]:
    errors = answer.get("errors")
    if isinstance(errors, list):
        return list(errors)
    return [errors] if errors else []


def results(answer: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    data = answer.get("data")
    for entry in data if isinstance(data, list) else []:
        if not isinstance(entry, dict):
            continue
        url = entry.get("imageURL") or entry.get("videoURL") or entry.get("audioURL")
        out.append({
            "url": url,
            "seed": entry.get("seed"),
            "id": entry.get("taskUUID"),
            "pending": url is None,
        })
    return out


def poll(task_ids: list[str], service: dict[str, Any], key: str) -> dict[str, Any]:
    return _post([{"taskType": "getResponse", "taskUUID": task_id} for task_id in task_ids], service, key)


def observation_outcome(answer: dict[str, Any]) -> str:
    if rejections(answer):
        return contract.REFUSED
    if 'exchange' in answer:
        return contract.UNKNOWN
    entries = results(answer)
    return contract.ACCEPTED if any(entry.get('id') or entry.get('url') or entry.get('pending') for entry in entries) else contract.UNKNOWN
