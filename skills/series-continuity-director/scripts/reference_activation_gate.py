#!/usr/bin/env python3
"""Verify a public reference set and explicitly selected state bindings."""
from __future__ import annotations
import argparse
import copy
from pathlib import Path
from typing import Any
import execution_contract as c
from protocol_contract import validate_artifact

# Consumer dimensions and the public influence that supplies them.
DIMENSION_INFLUENCE = {
    'identity': 'identity', 'shot-geometry': 'pose-camera',
    'appearance-state': 'outfit', 'lighting': 'lighting',
    'surface-finish': 'surface-finish', 'environment': 'environment',
    'prop-accessory': 'prop-accessory', 'local-color': 'local-color',
}


def finding(code: str, message: str, **extra: Any) -> dict:
    return {'code': code, 'message': message, **extra}


def file_ref(root: Path, value: Any) -> dict:
    c.exact(value, {'path', 'sha256'}, 'artifact reference')
    c.sha(value['sha256'])
    raw = c.read(c.local(root, value['path']))
    if c.digest(raw) != value['sha256']:
        raise ValueError('artifact bytes changed: ' + value['path'])
    obj = c.decode(raw)
    report = validate_artifact(obj)
    if not report['ok']:
        raise ValueError('invalid public artifact: ' + '; '.join(report['errors']))
    return obj


def reference_id(row: dict) -> str:
    if 'binding_id' in row:
        return c.text(row['binding_id'], 'binding ID')
    source = row['source']
    if source['kind'] == 'supplied-file':
        return c.text(source['reference_id'], 'source reference ID')
    # These are explicit components of a public artifact identifier, not a label.
    return '/'.join((source['pack_id'], source['asset_id'], source['artifact_id']))


def settle(activation: Any, root: Path) -> dict:
    """Return structural evidence and unresolved scope without granting adoption."""
    required = {'activation_id', 'package', 'story_point', 'uses', 'state_bindings'}
    c.exact(activation, required, 'reference activation')
    c.text(activation['activation_id'], 'activation ID')
    path = c.local(root, c.text(activation['package'], 'reference package'))
    package = c.load(path)
    report = validate_artifact(package)
    if not report['ok'] or package.get('artifact_type') != 'prepared-reference-set':
        raise ValueError('invalid prepared reference set: ' + '; '.join(report['errors']))
    point = activation['story_point']
    if point is not None and type(point) is not int:
        raise ValueError('story_point must be a story order or null')
    if not isinstance(activation['uses'], list) or not isinstance(activation['state_bindings'], dict):
        raise ValueError('activation needs explicit uses and state binding selectors')
    references = {}
    for row in package['selected_references']:
        ident = reference_id(row)
        if ident in references:
            raise ValueError('reference identifiers must be unique: ' + ident)
        references[ident] = row
    extra = set(activation['state_bindings']) - set(references)
    if extra:
        raise ValueError('state bindings name absent references: ' + ', '.join(sorted(extra)))
    uses = {}; bound = {}; unmeasured = []; errors = []
    plan = package['reference_use_plan']
    for index, row in enumerate(package['selected_references']):
        ident = reference_id(row)
        influence = set(row.get('intended_influence', []))
        if plan is not None:
            items = plan['reference_items']
            if index >= len(items) or items[index]['source'] != row['source'] or items[index]['authority'] != row['authority']:
                raise ValueError('prepared reference differs from its ordered use plan: ' + ident)
            influence.add(items[index]['intended_influence'])
        selector = activation['state_bindings'].get(ident)
        state = file_ref(root, selector) if selector is not None else None
        if state is not None:
            if state['artifact_type'] != 'state-aware-reference-binding':
                raise ValueError('state selector must name a state-aware-reference-binding')
            if state['source'] != row['source'] or state['role'] != row['role']:
                raise ValueError('state binding names different reference bytes or role: ' + ident)
            if 'binding_id' in row and state['binding_id'] != row['binding_id']:
                raise ValueError('prepared reference and state binding IDs differ: ' + ident)
            if influence and not influence.issubset(set(state['intended_influence'])):
                raise ValueError('prepared influence exceeds the selected state binding: ' + ident)
            influence.update(state['intended_influence'])
        bound[ident] = {'reference': row, 'state_binding': state, 'influence': sorted(influence)}
    for use in activation['uses']:
        if not isinstance(use, dict) or set(use) - {'reference', 'settles', 'overrides', 'declined', 'reason'}:
            raise ValueError('activation use has unknown fields')
        name = c.text(use.get('reference'), 'activated reference')
        if name not in references:
            errors.append(finding('REFERENCE_NOT_IN_PACKAGE', 'Activation names an absent reference.', reference=name)); continue
        if name in uses:
            raise ValueError('an activation repeats a reference: ' + name)
        uses[name] = use
        if 'declined' in use and type(use['declined']) is not bool:
            raise ValueError('declined must be an explicit Boolean')
        if use.get('declined'):
            c.text(use.get('reason'), 'declined reference reason')
            if use.get('settles') or use.get('overrides'):
                raise ValueError('a declined reference cannot settle or override dimensions')
            continue
        dimensions = use.get('settles')
        if not isinstance(dimensions, list) or not dimensions or any(not isinstance(x, str) for x in dimensions):
            raise ValueError('an activated reference needs explicit dimensions')
        if len(dimensions) != len(set(dimensions)):
            raise ValueError('activated dimensions must be unique')
        overrides = use.get('overrides', [])
        if not isinstance(overrides, list) or any(not isinstance(x, str) for x in overrides):
            raise ValueError('overrides must be explicit dimension IDs')
        evidence = bound[name]; state = evidence['state_binding']
        for dimension in dimensions:
            wanted = DIMENSION_INFLUENCE.get(dimension)
            if wanted is None:
                unmeasured.append({'reference': name, 'field': 'settles', 'dimension': dimension,
                                   'reason': 'No declared influence mapping for this dimension.'})
            elif wanted not in evidence['influence']:
                errors.append(finding('OUTSIDE_AUTHORITY', 'The selected evidence does not supply this dimension.',
                                      reference=name, dimension=dimension))
        if overrides:
            # Reopening an influence requires a newly selected binding, not an in-place exception.
            errors.append(finding('LOCKED_DIMENSION_REOPENED', 'Select a binding that permits the requested change.',
                                  reference=name, dimensions=overrides))
        if state is None:
            unmeasured.append({'reference': name, 'field': 'state_binding', 'reason': 'No state binding was selected.'})
            continue
        if point is None:
            unmeasured.append({'reference': name, 'field': 'story_point', 'reason': 'No story order was declared.'})
        else:
            span = state['effective_story_range']; start, end = span['from_order'], span['to_order']
            if point < start:
                errors.append(finding('BEFORE_STORY_RANGE', 'Reference is not effective at this story order.', reference=name))
            if end is not None and point > end:
                errors.append(finding('AFTER_STORY_RANGE', 'Reference is no longer effective at this story order.', reference=name))
            if state['superseded_for_future_scenes'] and end is None:
                unmeasured.append({'reference': name, 'field': 'effective_story_range', 'reason': 'Supersession has no end boundary.'})
        if state['unsupported_assumptions']:
            unmeasured.append({'reference': name, 'field': 'unsupported_assumptions',
                               'reason': 'The source explicitly records unsupported assumptions.',
                               'values': state['unsupported_assumptions']})
        blocked = set(state['unsupported_or_occluded_state']) & set(dimensions)
        if blocked:
            errors.append(finding('STATE_NOT_VISIBLE', 'The selected state explicitly marks these dimensions unsupported.',
                                  reference=name, dimensions=sorted(blocked)))
    for missing in sorted(set(references) - set(uses)):
        errors.append(finding('REFERENCE_DROPPED_SILENTLY', 'Use or explicitly decline every selected reference.', reference=missing))
    return {'package': package, 'package_path': path, 'references': bound, 'uses': uses,
            'errors': errors, 'unmeasured': unmeasured}


def gate(activation: Any, root: Path) -> dict:
    try:
        result = settle(activation, root)
        errors, unmeasured = result['errors'], result['unmeasured']
        count = len(result['references'])
    except (ValueError, OSError, TypeError, KeyError) as exc:
        errors, unmeasured, count = [finding('ACTIVATION_INVALID', str(exc))], [], 0
    return {'gate': 'reference-activation', 'activation_id': activation.get('activation_id') if isinstance(activation, dict) else None,
            'references': count, 'status': 'refused' if errors else 'admitted',
            'errors': errors, 'unmeasured': unmeasured}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('activation', type=Path); p.add_argument('--root', type=Path); p.add_argument('--json', action='store_true')
    a = p.parse_args(argv)
    try:
        report = gate(c.load(a.activation), a.root or a.activation.absolute().parent)
        print(c.encoded(report).decode('utf-8'), end='')
        return int(report['status'] != 'admitted')
    except (ValueError, OSError) as exc:
        print(c.encoded({'error': str(exc)}).decode('utf-8'), end=''); return 2


if __name__ == '__main__':
    raise SystemExit(main())
