"""Read applicable target advice as data, separately from acceptance contracts."""
from __future__ import annotations
import copy
from pathlib import Path
from typing import Any
import execution_contract as c
import request_contract as rc
from resource_files import resolve_resource
from schema_engine import validate_against_schema

ROOT = Path(__file__).resolve().parents[1]
CONTEXT_FIELDS = {'output_kind', 'input_modes', 'purpose', 'visual_language'}


def validate(value: Any) -> dict:
    schema = c.load(ROOT / 'schemas/authoring/target-guidance.schema.json')
    errors = list(validate_against_schema(value, schema, resolve_ref=lambda ref: (_ for _ in ()).throw(ValueError("unexpected guidance schema reference: " + ref))))
    if errors:
        raise ValueError('target guidance: ' + '; '.join(errors))
    ids = set()
    for entry in value['entries']:
        if entry['id'] in ids:
            raise ValueError('guidance entry ID repeats')
        ids.add(entry['id'])
        if entry['kind'] == 'parameter':
            rc.path_parts(entry['field'])
            proposed = entry['proposed']
            if proposed['kind'] == 'range' and proposed['minimum'] > proposed['maximum']:
                raise ValueError('guidance range is reversed')
        if entry['id'] in entry['conflicts_with']:
            raise ValueError('guidance entry conflicts with itself')
    if any(not set(x['conflicts_with']) <= ids for x in value['entries']):
        raise ValueError('guidance conflict names an absent entry')
    return value


def records(value: Any) -> list[dict]:
    if isinstance(value, dict) and value.get('artifact_type') == 'target-guidance':
        return [validate(value)]
    c.exact(value, {'guidance'}, 'target guidance collection')
    if not isinstance(value['guidance'], list):
        raise ValueError('guidance collection needs an array')
    return [validate(item) for item in value['guidance']]


def context(value: Any) -> dict:
    c.exact(value, CONTEXT_FIELDS, 'guidance context')
    c.text(value['output_kind'], 'output kind')
    c.text(value['purpose'], 'use purpose')
    for key in ('input_modes', 'visual_language'):
        if not isinstance(value[key], list) or len(value[key]) != len(set(value[key])):
            raise ValueError(key + ' must be an explicit unique list')
        for item in value[key]:
            c.text(item, key)
    return value


def applicable(document: dict, target_id: str, target: dict, ctx: dict) -> bool:
    applies = document['applies_to']
    if applies['target_id'] != target_id:
        return False
    for key in ('service', 'model_identifier', 'operation'):
        if applies[key] is not None and applies[key] != target[key]:
            return False
    for key in ('output_kinds', 'purposes'):
        selected = ctx['output_kind' if key == 'output_kinds' else 'purpose']
        if applies[key] and selected not in applies[key]:
            return False
    # Null leaves modes unrestricted; every supplied list is an exact set.
    if applies['input_modes'] is not None and set(applies['input_modes']) != set(ctx['input_modes']):
        return False
    if applies['visual_language'] and not set(applies['visual_language']) <= set(ctx['visual_language']):
        return False
    return True


def collect(documents: list[tuple[dict, Any]], target_id: str, target: dict, ctx: dict) -> list[dict]:
    context(ctx)
    selected = []
    seen = set()
    for ref, value in documents:
        for document in records(value):
            if not applicable(document, target_id, target, ctx):
                continue
            if document['id'] in seen:
                raise ValueError('multiple applicable guidance records share ID: ' + document['id'])
            seen.add(document['id'])
            selected.append({'source': copy.deepcopy(ref), 'guidance': copy.deepcopy(document)})
    return selected


def display(profile: dict, target: dict, ctx: dict, documents: list[tuple[dict, Any]], *, source=None) -> dict:
    selected = collect(documents, profile['target_id'], target, ctx)
    return {'target_id': profile['target_id'], 'target': copy.deepcopy(target),
            'definition': source, 'context': copy.deepcopy(ctx),
            'prompt_contract': copy.deepcopy(profile.get('prompt_contract', {})),
            'guidance_status': 'available' if selected else 'not-registered-for-context',
            'guidance': selected,
            'meaning': 'Advice is a choice, not a capability, schema or permission. No text or setting is applied automatically.'}


def resources(paths: list[Path | str] | None = None) -> list[tuple[dict, Any]]:
    selected = list(paths or [])
    if not selected:
        configured = resolve_resource('target-guidance')
        if configured is not None:
            selected.append(configured)
    documents = []
    for path in selected:
        p = Path(path)
        if p.is_symlink() or not p.is_file():
            raise ValueError('guidance must be a regular data file: ' + str(p))
        raw = c.read(p)
        value = c.decode(raw)
        records(value)
        documents.append(({'path': str(p.absolute()), 'sha256': c.digest(raw)}, value))
    return documents
