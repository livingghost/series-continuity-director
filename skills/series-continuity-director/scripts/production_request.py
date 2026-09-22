"""Bind an exact model request to the actor's supplied scope and rendition review."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import execution_contract as c
from input_evidence import InputEvidence
import request_contract as rc
import request_scope
import request_validation

DECISION_FIELDS = {'case', 'assessments', 'principal_approval', 'rendition_review', 'stop_assessments'}


def production_selector(prepared: dict, spec: dict) -> dict:
    """Describe a production by declared IDs, independently of a file's display name."""
    selected = {'task_id': prepared['task']['task_id'], 'kind': spec['kind'], 'target': spec['target']}
    if spec['kind'] == 'shot':
        selected.update(scene_id=spec['scene_id'], shot_id=spec['shot_id'])
    return selected


def validate_request(spec: dict, rendered: dict, *, live_root: Path | None = None) -> dict:
    rc.validate_seal(rendered)
    import input_contracts
    reader, _ = input_contracts.verify_fields(spec, root=live_root, live=live_root is not None)
    from request_renderer import envelope_fields
    return request_validation.require(spec['request_validation'],
        reader,
        expected_target=rendered['sealed']['target'], execution=rendered['sealed']['execution'],
        rendered=rendered, envelope_fields=envelope_fields(rendered))


def draft_decision(rendered: dict, *, actor: str | None, conditions: list[str]) -> dict:
    """Derive identifiers while leaving judgments and approval sources unanswered."""
    rc.validate_seal(rendered)
    return {'case': None, 'assessments': [], 'principal_approval': None,
            'rendition_review': {'request_sha256': rendered['request_sha256'], 'reviewer': actor,
                'conclusion': None, 'reason': '',
                'binding_ids': ['reference:' + str(item['reference_number']) for item in rendered['sealed']['bindings']]},
            'stop_assessments': [{'condition': item, 'clear': None, 'reason': ''} for item in conditions]}


def check(root: Path, prepared: dict, spec: dict, rendered: dict, decision: Any,
          grant: dict, permission: dict, *, actor: str) -> tuple[dict, list[dict]]:
    """Validate evidence and structure; the named actor evaluates creative meaning."""
    validation = validate_request(spec, rendered, live_root=root)
    c.exact(decision, DECISION_FIELDS, 'model request decision')
    review = decision['rendition_review']
    c.exact(review, {'request_sha256', 'reviewer', 'conclusion', 'reason', 'binding_ids'}, 'rendition review')
    if review['request_sha256'] != rendered['request_sha256'] or review['reviewer'] != actor:
        raise ValueError('rendition review belongs to another request or actor')
    c.text(review['reason'], 'rendition review reason')
    if review['conclusion'] != 'satisfied':
        raise ValueError('the actor has not recorded a satisfied rendition review')
    bindings = review['binding_ids']
    if not isinstance(bindings, list) or any(not isinstance(item, str) for item in bindings) or len(set(bindings)) != len(bindings):
        raise ValueError('rendition review requires distinct declared binding IDs')
    expected = {'reference:' + str(item['reference_number']) for item in rendered['sealed']['bindings']}
    if set(bindings) != expected:
        raise ValueError('rendition review omits or adds a transported reference binding')
    supplied = {}
    if not isinstance(decision['stop_assessments'], list):
        raise ValueError('stop assessments must be an explicit array')
    for item in decision['stop_assessments']:
        c.exact(item, {'condition', 'clear', 'reason'}, 'stop assessment')
        c.text(item['condition'], 'stop condition'); c.text(item['reason'], 'stop assessment reason')
        if item['condition'] in supplied or item['clear'] is not True:
            raise ValueError('each stop condition needs one explicit clear assessment')
        supplied[item['condition']] = item
    if set(supplied) != set(grant['stop_conditions']):
        raise ValueError('stop assessments differ from the authorization conditions')
    principal = decision['principal_approval']
    if principal is not None and (not isinstance(principal, dict) or principal.get('principal') != grant['principal']):
        raise ValueError('exact request approval must name the authorization principal')
    reader = InputEvidence(root)
    request_scope.verify_sources(permission['request_scope'], principal, reader)
    result = request_scope.assess(permission['request_scope'], case_id=decision['case'], rendered=rendered,
        production=production_selector(prepared, spec), mode=validation['mode'], modes=permission['submission_validation_modes'],
        assessments=decision['assessments'], principal_approval=principal)
    if result['state'] != 'delegated-ready':
        raise ValueError('model request authority: ' + result['state'] + '; ' +
                         str(result['scope_blockers'] or result['assessment_required']))
    return {'validation': validation, 'scope': result}, [
        {'path': path, 'sha256': reader.snapshots[path]['sha256']} for path in sorted(reader.read_paths)]
