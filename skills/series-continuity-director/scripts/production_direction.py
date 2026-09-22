#!/usr/bin/env python3
"""Resolve authored choices into bounded instructions, not artistic scores.

Detailed source documents remain owned and snapshotted by the production run.
Only selected realization instructions cross the consumer boundary. Alternative
comparison is required for a declared material branch, not for every operation.
"""
from __future__ import annotations
from typing import Any
import execution_contract as c


def strings(value: Any, label: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f'{label}: list required')
    for item in value:
        c.text(item, label)
    if len(set(value)) != len(value):
        raise ValueError(f'{label}: duplicate entry')
    return value


def validate(value: Any, sources: list[dict[str, Any]], criteria: list[dict[str, Any]]) -> None:
    c.exact(value, {'purpose', 'intended_effect', 'basis', 'decisions', 'departures',
                    'action_context', 'verification_limits'}, 'direction')
    c.text(value['purpose'], 'purpose')
    c.text(value['intended_effect'], 'intended effect')
    strings(value['verification_limits'], 'verification limits')
    source_ids = {x['id'] for x in sources}
    applied = {x['id'] for x in sources if x['disposition'] == 'applied'}
    criterion_ids = {x['id'] for x in criteria}
    for name in ('basis', 'decisions', 'departures'):
        if not isinstance(value[name], list):
            raise ValueError(f'direction.{name}: list required')
    for row in value['basis']:
        c.exact(row, {'source', 'applicability'}, 'direction basis')
        if row['source'] not in applied:
            raise ValueError('direction basis must name an applied source')
        c.text(row['applicability'], 'basis applicability')
    if not value['decisions']:
        raise ValueError('record at least the decision that realizes this purpose')
    ids: set[str] = set()
    covered: set[str] = set()
    for row in value['decisions']:
        c.exact(row, {'id', 'question', 'compare', 'options', 'selected', 'reason', 'criteria'}, 'direction decision')
        for key in ('id', 'question', 'selected', 'reason'):
            c.text(row[key], 'decision ' + key)
        if row['id'] in ids:
            raise ValueError('duplicate decision id')
        ids.add(row['id'])
        if type(row['compare']) is not bool:
            raise ValueError('compare must be a boolean declaring a material branch')
        if not isinstance(row['options'], list) or len(row['options']) < (2 if row['compare'] else 1):
            raise ValueError('material branches need alternatives; settled decisions need a realization')
        options: set[str] = set()
        for option in row['options']:
            c.exact(option, {'id', 'realization', 'consequence'}, 'direction option')
            for key in option:
                c.text(option[key], 'option ' + key)
            if option['id'] in options:
                raise ValueError('duplicate option id')
            options.add(option['id'])
        if row['selected'] not in options:
            raise ValueError('selected option does not exist')
        selected_checks = strings(row['criteria'], 'decision criteria', nonempty=True)
        if not set(selected_checks) <= criterion_ids:
            raise ValueError('decision names an unknown verification criterion')
        covered.update(selected_checks)
    if covered != criterion_ids:
        raise ValueError('every criterion must be connected to a realization decision')
    for departure in value['departures']:
        c.exact(departure, {'source', 'scope', 'reason', 'preserved'}, 'intentional departure')
        if departure['source'] not in source_ids:
            raise ValueError('departure names an unknown source')
        for key in ('scope', 'reason', 'preserved'):
            c.text(departure[key], 'departure ' + key)
    action = value['action_context']
    if action is not None:
        c.exact(action, {'phase', 'before', 'after', 'relations'}, 'action context')
        for key in ('phase', 'before', 'after'):
            c.text(action[key], 'action ' + key)
        if not isinstance(action['relations'], list):
            raise ValueError('action relations must be a list')
        for relation in action['relations']:
            c.exact(relation, {'subjects', 'relation', 'condition'}, 'action relation')
            strings(relation['subjects'], 'relation subjects', nonempty=True)
            c.text(relation['relation'], 'relation')
            c.text(relation['condition'], 'relation condition')
        if not value['verification_limits']:
            raise ValueError('action context must state what the proposed artifact cannot verify')


def compile_direction(value: dict[str, Any], delivery: str, transport: str) -> dict[str, Any]:
    c.text(delivery, 'delivery')
    if transport not in {'authored-rendition', 'bounded-context'}:
        raise ValueError('invalid direction transport')
    selected = []
    for row in value['decisions']:
        option = next(x for x in row['options'] if x['id'] == row['selected'])
        instruction = option['realization']
        selected.append({'decision': row['id'], 'instruction': instruction, 'criteria': row['criteria']})
    return {'purpose': value['purpose'], 'intended_effect': value['intended_effect'],
            'selected': selected, 'verification_limits': value['verification_limits']}


def validate_repairs(repairs: Any, direction: dict[str, Any], observations: list[Any]) -> None:
    if not isinstance(repairs, list):
        raise ValueError('repairs must be a list')
    decisions = {x['id'] for x in direction['decisions']}
    for item in repairs:
        c.exact(item, {'decisions', 'observation_indices', 'operation', 'scope', 'reason',
                       'expected_evidence', 'targets'}, 'repair proposal')
        strings(item['targets'], 'repair targets', nonempty=True)
        linked = strings(item['decisions'], 'repair decisions')
        if not set(linked) <= decisions:
            raise ValueError('repair names an unknown decision')
        for key in ('operation', 'scope', 'reason', 'expected_evidence'):
            c.text(item[key], 'repair ' + key)
        indices = item['observation_indices']
        if not isinstance(indices, list) or not indices or any(type(i) is not int or not 0 <= i < len(observations) for i in indices):
            raise ValueError('repair must cite actual observations')


def impact(prepared: dict[str, Any], changed_sources: set[str]) -> dict[str, Any]:
    task = prepared['task']
    source_ids = {s['id'] for s in task['sources'] if s['path'] in changed_sources}
    basis = {x['source'] for x in task['direction']['basis']}
    affected = source_ids & basis
    # The association is purpose-level, not a claim of inferred semantic impact.
    return {'changed_source_ids': sorted(source_ids), 'applicable_basis_changed': sorted(affected),
            'reconsider_decisions': [d['id'] for d in task['direction']['decisions']] if affected else [],
            'meaning': 'Declared dependency impact. Artistic consequences need a new reading, not a hash comparison.'}
