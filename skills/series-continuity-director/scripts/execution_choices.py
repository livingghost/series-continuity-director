"""Bind chosen text and settings to exact, snapshotted target definitions.

Builders resolve choices. Transports only carry the resulting fields. This is
part of the existing submission and its request receipt, not another ledger.
"""
from __future__ import annotations
import copy
from pathlib import Path
from typing import Any
import execution_contract as c
import request_contract as rc
import target_guidance as guidance

PLAN_FIELDS = {'context', 'settings', 'recommendations', 'segments'}
RECORD_FIELDS = PLAN_FIELDS | {'selection', 'text_sha256', 'negative_sha256'}
STATES = {'explicit', 'recommended', 'offering', 'not-applicable', 'not-exposed', 'provider-managed'}
SENT_STATES = {'explicit', 'recommended', 'offering'}


def leaves(value: dict, prefix: str = '') -> dict:
    """Dotted paths describe fields; arrays and empty objects remain values."""
    if not isinstance(value, dict):
        raise ValueError('settings must be an object')
    result = {}
    for key, item in value.items():
        path = prefix + '.' + key if prefix else key
        rc.path_parts(path)
        if isinstance(item, dict) and item:
            children = leaves(item, path)
        else:
            children = {path: item}
        for name, child in children.items():
            if name in result:
                raise ValueError('settings declare the same field twice: ' + name)
            result[name] = child
    paths = [rc.path_parts(key) for key in result]
    if any(rc.overlaps(a, b) for i, a in enumerate(paths) for b in paths[i + 1:]):
        raise ValueError('settings contain overlapping field paths')
    return result


def entry_key(value: Any) -> tuple[str, str]:
    c.exact(value, {'guidance', 'entry'}, 'recommendation reference')
    for key in value:
        c.text(value[key], 'recommendation ' + key)
    return value['guidance'], value['entry']


def values_equal(a, b) -> bool:
    return c.encoded(a) == c.encoded(b)


def _proposed(value: Any, rule: dict) -> bool:
    if rule['kind'] == 'choices':
        return any(values_equal(value, x) for x in rule['values'])
    if type(value) not in (int, float) or not rule['minimum'] <= value <= rule['maximum']:
        return False
    return not rule['integer'] or type(value) is int


def _setting_map(rows: Any, entries: dict, decisions: dict, offering: dict, policy: dict) -> tuple[dict, dict, set]:
    if not isinstance(rows, list):
        raise ValueError('setting choices must be an array')
    result, by_field, used = {}, {}, set()
    declared = leaves((offering.get('constraints') or {}).get('as_written') or {})
    for row in rows:
        c.exact(row, {'field', 'state', 'value', 'reason', 'recommendation'}, 'setting choice')
        path = rc.path_parts(row['field'])
        c.text(row['reason'], 'setting reason')
        if row['state'] not in STATES or row['field'] in by_field:
            raise ValueError('setting state is unresolved or field repeats')
        if any(rc.overlaps(path, rc.path_parts(other)) for other in by_field):
            raise ValueError('setting choices overlap')
        by_field[row['field']] = row
        rec = row['recommendation']
        if row['state'] == 'recommended':
            key = entry_key(rec)
            if decisions.get(key) != 'adopt' or key not in entries:
                raise ValueError('recommended value has no adopted applicable recommendation')
            entry = entries[key]
            if entry['kind'] != 'parameter' or entry['field'] != row['field'] or not _proposed(row['value'], entry['proposed']):
                raise ValueError('setting differs from its selected recommendation')
            used.add(key)
        elif rec is not None:
            raise ValueError('only a recommended setting names a recommendation')
        if row['state'] == 'offering':
            if row['field'] not in declared or not values_equal(declared[row['field']], row['value']):
                raise ValueError('offering choice differs from the offering declaration')
        if row['state'] in SENT_STATES:
            result[row['field']] = copy.deepcopy(row['value'])
        elif row['value'] is not None:
            raise ValueError('an omitted control carries no request value')
    if not set(declared) <= set(by_field):
        raise ValueError('decide each offering setting before request construction: ' + ', '.join(sorted(set(declared) - set(by_field))))
    for control in policy.get('controls', []):
        c.exact(control, {'field', 'availability', 'allow_provider_managed', 'reason'}, 'operation control')
        rc.path_parts(control['field']); c.text(control['reason'], 'control evidence reason')
        if type(control['allow_provider_managed']) is not bool:
            raise ValueError('provider-managed permission must be boolean')
        if control['availability'] not in {'selectable', 'not-applicable', 'not-exposed'}:
            raise ValueError('unknown control availability')
        row = by_field.get(control['field'])
        if row is None:
            raise ValueError('important operation control has no choice: ' + control['field'])
        if control['availability'] != 'selectable':
            if row['state'] != control['availability']:
                raise ValueError('a nonapplicable or unexposed control cannot be sent')
        elif row['state'] not in SENT_STATES and not (row['state'] == 'provider-managed' and control['allow_provider_managed']):
            raise ValueError('select a value for this operation control: ' + control['field'])
    return result, by_field, used


def _segments(rows: Any, text: str, channel: str, entries: dict, decisions: dict) -> tuple[list, set]:
    if not isinstance(rows, list):
        raise ValueError('text segments must be an array')
    end, result, used = 0, [], set()
    for row in rows:
        c.exact(row, {'start', 'end', 'text', 'recommendation', 'reason'}, 'chosen text segment')
        if type(row['start']) is not int or type(row['end']) is not int or row['start'] != end or row['end'] <= end:
            raise ValueError('text segments have a gap, overlap or empty span')
        if text[row['start']:row['end']] != row['text']:
            raise ValueError('text segment differs from submitted text')
        c.text(row['reason'], 'segment reason')
        ref = row['recommendation']; key = None
        if ref is not None:
            key = entry_key(ref)
            if decisions.get(key) != 'adopt' or key not in entries:
                raise ValueError('text uses no adopted applicable recommendation')
            entry = entries[key]
            if entry['kind'] != 'text' or entry['channel'] != channel:
                raise ValueError('recommendation names a different text channel')
            if not entry['allow_rewording'] and entry['text'] != row['text']:
                raise ValueError('this recommended fragment must be used exactly')
            used.add(key)
        result.append({'source_kind': 'model-setting' if ref is not None else 'authored',
                       'start': row['start'], 'end': row['end'], 'text': row['text'],
                       'source_refs': ([{'kind': 'target-guidance', **ref,
                                         'reason': row['reason']}] if ref is not None else [])})
        end = row['end']
    if end != len(text):
        raise ValueError('text segments must cover the entire submitted channel')
    return result, used


def build(plan: dict, reader, *, spec: dict, profile_ref: dict, service_ref: dict, guidance_refs: list[dict], policy: dict) -> dict:
    c.exact(plan, PLAN_FIELDS, 'execution choices')
    from state_protocol import validate_against_schema
    errors = validate_against_schema(plan, c.load(Path(__file__).resolve().parents[1] / 'schemas/authoring/execution-choices.schema.json'))
    if errors:
        raise ValueError('execution choices: ' + '; '.join(errors))
    value = copy.deepcopy(plan)
    value['selection'] = {'profile': profile_ref, 'service_profiles': service_ref, 'guidance': guidance_refs}
    value['text_sha256'] = c.digest(spec['text'].encode('utf-8'))
    value['negative_sha256'] = c.digest(spec.get('negative_text', '').encode('utf-8'))
    resolved = resolve(value, reader, spec=spec, policy=policy)
    # A builder may fill only values explicitly selected in this plan. Existing
    # authored settings cannot be silently changed by a recommendation.
    authored = leaves(spec.get('parameters') or {})
    for key, val in leaves(spec.get('options') or {}).items():
        if key in authored:
            raise ValueError('parameters and options repeat a setting')
        authored[key] = val
    for field, val in authored.items():
        if field not in resolved['parameters'] or not values_equal(val, resolved['parameters'][field]):
            raise ValueError('execution choices change an already authored setting: ' + field)
    return value


def resolve(value: dict, reader, *, spec: dict, policy: dict, profile: dict | None = None, service: dict | None = None) -> dict:
    c.exact(value, RECORD_FIELDS, 'resolved execution choices')
    c.exact(value['selection'], {'profile', 'service_profiles', 'guidance'}, 'selected definitions')
    selection = value['selection']
    chosen_profile = reader.json(selection['profile'])
    from target_protocol import validate_profile
    report = validate_profile(chosen_profile)
    if not report['ok'] or chosen_profile['target_id'] != spec['target']:
        raise ValueError('selected target definition is invalid or names another model')
    if profile is not None and chosen_profile != profile:
        raise ValueError('target definition differs from the selected source')
    target = rc.target({'service': spec['service'], 'model_identifier': spec['model'], 'operation': spec['operation']})
    offers = [x for x in chosen_profile.get('offerings', []) if x.get('service') == target['service'] and x.get('model_identifier') == target['model_identifier']]
    if len(offers) != 1:
        raise ValueError('selected source must contain one exact offering')
    chosen_service = reader.json(selection['service_profiles'])['services'][target['service']]
    if service is not None and chosen_service != service:
        raise ValueError('service differs from the selected source')
    if target['operation'] not in chosen_service.get('operations', {}):
        raise ValueError('selected service does not expose this operation')
    ctx = guidance.context(value['context'])
    modes = sorted({x['mode'] for x in spec.get('inputs', []) if 'mode' in x})
    if ctx['output_kind'] != spec['output_kind'] or sorted(ctx['input_modes']) != modes:
        raise ValueError('guidance context differs from the submitted media and modes')
    documents = [(ref, reader.json(ref)) for ref in selection['guidance']]
    card = guidance.display(chosen_profile, target, ctx, documents, source=selection['profile'])
    entries, sources = {}, {}
    for match in card['guidance']:
        for entry in match['guidance']['entries']:
            key = match['guidance']['id'], entry['id']
            entries[key] = entry; sources[key] = match['source']
    decisions = {}
    if not isinstance(value['recommendations'], list):
        raise ValueError('recommendation decisions must be an array')
    for row in value['recommendations']:
        c.exact(row, {'guidance', 'entry', 'decision', 'reason'}, 'recommendation decision')
        key = row['guidance'], row['entry']; c.text(row['reason'], 'recommendation decision reason')
        if key not in entries or key in decisions or row['decision'] not in {'adopt', 'reject'}:
            raise ValueError('recommendation is absent, duplicated or undecided')
        decisions[key] = row['decision']
    if set(decisions) != set(entries):
        raise ValueError('record adoption or rejection for each applicable recommendation')
    for key, decision in decisions.items():
        if decision == 'adopt' and any(decisions.get((key[0], other)) == 'adopt' for other in entries[key]['conflicts_with']):
            raise ValueError('conflicting recommendations were both adopted')
    params, rows, used = _setting_map(value['settings'], entries, decisions, offers[0], policy)
    c.exact(value['segments'], {'positive', 'negative'}, 'submitted text channels')
    compiled = {}
    for channel, field, hash_field in [('positive', 'text', 'text_sha256'), ('negative', 'negative_text', 'negative_sha256')]:
        text = spec.get(field, '')
        if not isinstance(text, str) or c.digest(text.encode('utf-8')) != value[hash_field]:
            raise ValueError('submitted text changed after choices were resolved')
        compiled[channel], linked = _segments(value['segments'][channel], text, channel, entries, decisions)
        for segment in compiled[channel]:
            if segment['source_refs']:
                ref = segment['source_refs'][0]
                ref['source'] = sources[(ref['guidance'], ref['entry'])]
        used |= linked
    if used != {key for key, decision in decisions.items() if decision == 'adopt'}:
        raise ValueError('adopted advice must reach the actual settings or text')
    shape = offers[0].get('request_shape') or {}
    if spec.get('negative_text') and not shape.get('negative_text_key'):
        raise ValueError('this offering exposes no negative text channel')
    return {'parameters': params, 'segments': compiled, 'card': card,
            'setting_choices': copy.deepcopy(value['settings']), 'sources': sources}


def attach(spec: dict, value: dict, resolved: dict) -> None:
    spec['execution_choices'] = copy.deepcopy(value)
    spec['execution_choices_sha256'] = c.content_id(value)
    spec['parameters'] = copy.deepcopy(resolved['parameters'])
    spec.pop('options', None)


def require(spec: dict, reader, *, policy: dict, profile: dict, service: dict) -> dict:
    value = spec.get('execution_choices')
    if not isinstance(value, dict) or spec.get('execution_choices_sha256') != c.content_id(value):
        raise ValueError('resolve execution choices before rendering a request')
    result = resolve(value, reader, spec=spec, policy=policy, profile=profile, service=service)
    if spec.get('options') or not values_equal(leaves(spec.get('parameters') or {}), result['parameters']):
        raise ValueError('submitted settings differ from resolved execution choices')
    return result


def bind_trace(compiled: dict, value: dict, resolved: dict, *, native_controls: list[dict]) -> None:
    """Check every chosen field at its real wire location and attribute its source."""
    layout = compiled['layout']
    covered = [layout['model'], layout['operation'], *layout['management']]
    covered += [x['field'] for x in layout['content']] + [x['field'] for x in layout['media']]
    covered += [x['field'] for x in native_controls]
    covered += [rc.path_parts(row['field']) for row in value['settings'] if row['state'] in SENT_STATES]
    def visit(node, path):
        if any(path[:len(prefix)] == prefix for prefix in covered):
            return
        if isinstance(node, dict) and node:
            for key, child in node.items():
                visit(child, path + [key])
        elif isinstance(node, list) and node:
            for i, child in enumerate(node):
                visit(child, path + [i])
        elif path:
            raise ValueError('transport added a field without a chosen setting: ' + str(path))
    visit(compiled['request'], [])
    for row in value['settings']:
        path = rc.path_parts(row['field'])
        present = rc.present(compiled['request'], path)
        if row['state'] not in SENT_STATES:
            if present:
                raise ValueError('transport inserted an omitted setting: ' + row['field'])
            continue
        if not present or not values_equal(rc.get(compiled['request'], path), row['value']):
            raise ValueError('transport changed a resolved setting: ' + row['field'])
        for item in compiled['request_trace']:
            if item['target_field'] == path:
                ref = row['recommendation']
                item.update(source_kind='model-setting', transform_id='selected-' + row['state'],
                            source_refs=[{'kind': 'execution-choice', 'field': row['field'],
                                          'choices_sha256': c.content_id(value), 'reason': row['reason'],
                                          'source': (resolved['sources'][entry_key(ref)] if ref else value['selection']['profile'])}])
