"""Runware transport: the service-specific half of a dispatch.

A transport module turns a dispatch spec into the exact bytes one service accepts
and reads the service's answer back. `dispatch.py` owns everything that is not
service-specific: the gate, the offering, the run record, the files on disk.

A module named `transport_<service>.py` is found by that service id and must
provide, with these exact signatures:

    media_paths(spec, offering)  -> list[str]
        The selected input files that must be registered with the service before the
        request can name them.

    build(spec, offering, service, media_ids) -> dict
        The request as it would be sent, with input file paths replaced by the service ids in
        `media_ids`. Called once for the dry run with `media_ids` empty and once
        with the real ids, so a caller can show the user the shape before
        anything is uploaded or spent.

    describe_request(request, spec) -> {primary_text, output_count}
        Resolve actual built text and explicit requested output count. These must
        equal the prepared text and reserved count before any upload or send.

    upload(path, service, key) -> str
        Register one selected file and return the id the request will carry.

    send(request, service, key) -> dict
        Perform the request and return the parsed answer.

    rejections(answer) -> list[dict]
        The service's refusals, empty when it accepted the request.

    results(answer) -> list[dict]
        One entry per returned artifact: {"url", "seed", "id", "pending"}.
        `pending` is true when the service has accepted the task and the artifact
        is not ready, in which case `poll` is called later.

    poll(task_ids, service, key) -> dict
        Ask again for tasks that were pending. Absent when a service is
        synchronous only.
"""
from __future__ import annotations
from io_budget import environment_seconds

import base64
import json
import mimetypes
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

SERVICE = "runware"


def _endpoint(service: dict[str, Any]) -> str:
    url = ((service.get("endpoint") or {}).get("base_url") or "").strip()
    if not url:
        raise SystemExit("the service record carries no endpoint.base_url")
    return url


def _post(payload: list[dict[str, Any]], service: dict[str, Any], key: str) -> dict[str, Any]:
    request = urllib.request.Request(
        _endpoint(service),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=environment_seconds("PRODUCTION_HTTP_TIMEOUT_SECONDS")) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"errors": [{"code": f"http{error.code}", "message": body}]}


def media_paths(spec: dict[str, Any], offering: dict[str, Any]) -> list[str]:
    return [str(item["path"]) for item in spec.get("inputs") or [] if item.get("path")]


def _place(task: dict[str, Any], key_path: str, value: Any) -> None:
    """Write a value at a request key, which may name a nested envelope."""
    parts = key_path.split(".")
    target = task
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    leaf = parts[-1]
    if leaf in target and isinstance(target[leaf], list):
        target[leaf].append(value)
    elif leaf in target:
        target[leaf] = [target[leaf], value]
    else:
        target[leaf] = value


def _request_key(offering: dict, role: str, given: str | None) -> str:
    if given:return given
    mapped=(offering.get('request_keys') or {}).get(role)
    if not mapped:raise ValueError('input role has no exact request-key declaration: '+role)
    return mapped[0] if isinstance(mapped,list) else mapped


def compile_request(spec: dict, offering: dict, service: dict, media_ids: dict | None = None) -> dict:
    from request_contract import RequestWriter,path_parts,MANAGEMENT_VALUE,get,present
    operation=spec.get('operation')
    if operation not in service.get('operations',{}):raise ValueError('service does not declare the selected operation')
    writer=RequestWriter();media_ids=media_ids or {};source=[{'kind':'offering','service':spec['service'],'model_identifier':spec.get('model') or offering['model_identifier']}]
    def write(path,value,kind,transform,bindings=None):writer.write(path,value,source_kind=kind,source_refs=source,transform_id=transform,binding_ids=bindings)
    write(['taskType'],operation,'transport-envelope','operation');write(['taskUUID'],spec.get('task_uuid') or str(uuid.uuid4()),'transport-envelope','task-identifier')
    write(['model'],spec.get('model') or offering['model_identifier'],'model-setting','model-identifier')
    primary=path_parts(spec.get('text_key') or 'positivePrompt');write(primary,spec['text'],'authored','selected-rendition')
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


def build(spec: dict, offering: dict, service: dict, media_ids: dict) -> dict:
    return compile_request(spec,offering,service,media_ids)['request']


def _merge_absent(target: dict[str, Any], defaults: dict[str, Any]) -> None:
    """Write each default at its key path where the target has nothing there."""
    for key, value in defaults.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_absent(target[key], value)
        elif isinstance(value, dict) and key not in target:
            target[key] = json.loads(json.dumps(value))
        elif key not in target:
            target[key] = value


def describe_request(request: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """Describe the actual built request, not the intended spec or inferred default.

    A sent production request explicitly names numberResults. New transports
    implement their own actual count/text semantics rather than copying a key.
    """
    count=request.get('numberResults')
    text=request.get(spec.get('text_key') or 'positivePrompt')
    if isinstance(count,bool) or not isinstance(count,int) or count<1:
        raise ValueError('a production request must explicitly declare a positive numberResults')
    if not isinstance(text,str) or not text.strip():raise ValueError('built request has no primary text')
    return {'primary_text':text,'output_count':count}


def upload(path: str, service: dict[str, Any], key: str) -> str:
    data = Path(path).read_bytes()
    media_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return upload_bytes(data, media_type, service, key)


def upload_bytes(data: bytes, media_type: str, service: dict, key: str) -> str:
    """Send only the byte snapshot already checked by the authorized dispatcher."""
    if not isinstance(data, bytes) or not isinstance(media_type, str) or not media_type:
        raise ValueError('upload requires verified bytes and their declared media type')
    payload = f"data:{media_type};base64," + base64.b64encode(data).decode("ascii")
    video = media_type.startswith("video") or media_type.startswith("audio")
    task = {"taskUUID": str(uuid.uuid4())}
    if video:
        task.update({"taskType": "mediaStorage", "operation": "upload", "media": payload})
    else:
        task.update({"taskType": "imageUpload", "image": payload})
    answer = _post([task], service, key)
    refused = rejections(answer)
    if refused:
        raise SystemExit(f"the service refused an upload: {json.dumps(refused)}")
    entry = (answer.get("data") or [{}])[0]
    identifier = entry.get("imageUUID") or entry.get("mediaUUID") or entry.get("mediaId")
    if not identifier:
        raise SystemExit(f"an upload returned no identifier: {json.dumps(answer)}")
    return str(identifier)


def send(request: dict[str, Any], service: dict[str, Any], key: str) -> dict[str, Any]:
    return _post([request], service, key)


def rejections(answer: dict[str, Any]) -> list[dict[str, Any]]:
    return list(answer.get("errors") or [])


def results(answer: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for entry in answer.get("data") or []:
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


def observation_outcome(answer:dict)->str:
    if rejections(answer):return 'rejected'
    entries=results(answer)
    return 'accepted' if any(entry.get('id') or entry.get('url') or entry.get('pending') for entry in entries) else 'indeterminate'
