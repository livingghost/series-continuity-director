"""Apply series drawing and presentation choices through production decisions."""
from __future__ import annotations
import copy
import execution_contract as c

VISUAL_OUTPUTS = {'image', 'video', 'video-with-audio'}


def validate(value, sources, decisions):
    if value is None:
        return
    c.exact(value, {'anchor', 'register', 'coordination'}, 'visual language selection')
    applied = {s['id'] for s in sources if s['disposition'] == 'applied'}
    known = {d['id'] for d in decisions}
    if value['coordination'] is not None:
        c.text(value['coordination'], 'mixed treatment coordination')
    for kind in ('anchor', 'register'):
        rows = value[kind]
        if not isinstance(rows, list) or not rows:
            raise ValueError('select an explicit visual ' + kind)
        if len(rows) > 1 and not value['coordination']:
            raise ValueError('multiple treatments need declared scope coordination')
        assignments = {}
        for row in rows:
            c.exact(row, {'decision', 'source', 'scope', 'actor', 'dimensions'}, 'visual ' + kind)
            if row['decision'] not in known:
                raise ValueError('visual language names no realization decision')
            if row['source'] is not None and row['source'] not in applied:
                raise ValueError('visual language source must be applied in this production')
            for key in ('scope', 'actor'):
                c.text(row[key], 'visual ' + key)
            if not isinstance(row['dimensions'], dict) or not row['dimensions']:
                raise ValueError('visual language requires observable dimension choices')
            if kind == 'anchor' and not {'medium_family', 'dimensional_treatment'} <= set(row['dimensions']):
                raise ValueError('an anchor selects medium family and dimensional treatment')
            for axis, choice in row['dimensions'].items():
                c.text(axis, 'visual dimension'); c.text(choice, 'visual dimension choice')
                key = row['scope'], axis
                if key in assignments and assignments[key] != choice:
                    raise ValueError('different choices for the same visual scope and dimension')
                assignments[key] = choice


def require_for_output(value, output_kind):
    if output_kind in VISUAL_OUTPUTS and value is None:
        raise ValueError('visual production requires selected visual anchor and register')
    if output_kind not in VISUAL_OUTPUTS and value is not None:
        raise ValueError('nonvisual output has no visual language selection')


def compile_selection(value, decisions):
    if value is None:
        return None
    result = copy.deepcopy(value)
    for kind in ('anchor', 'register'):
        for row in result[kind]:
            decision = next(d for d in decisions if d['id'] == row['decision'])
            option = next(o for o in decision['options'] if o['id'] == decision['selected'])
            row['instruction'] = option['realization']
            row['reason'] = decision['reason']
            row['criteria'] = list(decision['criteria'])
    return result


def validate_compiled(value, output_kind):
    require_for_output(value, output_kind)
    if value is None:
        return
    c.exact(value, {'anchor', 'register', 'coordination'}, 'compiled visual language')
    sources, decisions, selection = {}, {}, copy.deepcopy(value)
    for kind in ('anchor', 'register'):
        for row in selection[kind]:
            instruction = row.pop('instruction'); reason = row.pop('reason'); criteria = row.pop('criteria')
            c.text(instruction, 'visual instruction'); c.text(reason, 'visual choice reason')
            if not isinstance(criteria, list) or not criteria:
                raise ValueError('visual language needs observation criteria')
            for criterion in criteria:
                c.text(criterion, 'visual criterion')
            if row['source']:
                sources[row['source']] = {'id': row['source'], 'disposition': 'applied'}
            decisions[row['decision']] = {'id': row['decision']}
    validate(selection, list(sources.values()), list(decisions.values()))


def review_requirements(value):
    if value is None:
        return []
    return [{'id': 'visual-language', 'kind': 'meaning', 'binding_ids': [], 'sources': [],
             'statement': 'Assess the scoped anchor and register in the exact rendition; inspect the returned media for their visible and temporal realization.'}]
