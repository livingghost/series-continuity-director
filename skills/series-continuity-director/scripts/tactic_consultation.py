"""Consult directing vocabulary and project tactics, then record scoped uses.

The agent selects source passages and applies their craft relationships. Existing
production sources and review criteria carry the decisions into the next run.
"""
from __future__ import annotations

import copy
from pathlib import Path

import execution_contract as c
from input_evidence import InputEvidence
import material_support as m

ROLE = 'tactic-application'
COMMANDS = frozenset({'consult-tactics', 'apply-tactics'})


def strings(value, label, *, empty=False):
    if not isinstance(value, list) or (not empty and not value):
        raise ValueError(label + ' must be an explicit array')
    for item in value:
        c.text(item, label)
    if len(value) != len(set(value)):
        raise ValueError(label + ' repeats an identifier')
    return value


def source_paths(root: Path, task: dict, extra: list[str]) -> list[str]:
    """List explicit sources by declared role; read the full production record."""
    paths = []
    if c.local(root, 'production-state.md', exists=False).is_file():
        paths.append('production-state.md')
    paths.extend(row['path'] for row in task.get('sources', [])
                 if row['role'] in {'production-state', 'production-tactics'})
    paths.extend(strings(extra, 'source paths', empty=True))
    return list(dict.fromkeys(paths))


def prior_applications(task: dict) -> list[dict]:
    """Expose intended-use records for explicit inspection without nesting them."""
    return [copy.deepcopy(row) for row in task.get('sources', []) if row['role'] == ROLE]


def navigation(root: Path, task_path: str | None = None, *, task: dict | None = None) -> dict:
    args = {'root': str(root)}
    if task_path is not None:
        args['task'] = task_path
    return {'sources': source_paths(root, task or {}, []),
            'prior_applications': prior_applications(task or {}),
            'coverage': 'The selected directing vocabulary and explicit project sources supply reusable craft knowledge.',
            'next_actions': [{'operation': 'consult-tactics', 'script': 'scripts/production_workflow.py',
                'args': args, 'required_args': ['query', 'out-dir', *(['task'] if task_path is None else [])],
                'external_effect': False, 'budget_effect': 'none'}]}


def consult(root: Path, task_path: str, query: str, out_dir: str, *, sources=None,
            vocabulary_path: str | None = None, category: str | None = None, limit: int = 8) -> dict:
    import vocabulary
    import production_inputs as inputs
    root = root.resolve(strict=True); reader = InputEvidence(root)
    task_ref = reader.select(task_path); task = reader.json(task_ref)
    c.text(task.get('task_id'), 'work task ID'); c.text(query, 'craft question')
    if type(limit) is not int or limit < 1:
        raise ValueError('limit must be a positive integer')
    try:
        data, path = vocabulary.load(vocabulary_path)
    except SystemExit as exc:
        raise ValueError(str(exc)) from exc
    raw_vocabulary = c.read(path)
    # Capture the same bytes used by the existing lexical search.
    if c.decode(raw_vocabulary) != data:
        raise ValueError('selected vocabulary changed while being read')
    hits = vocabulary.search(data, query, category, limit)
    full = []
    for hit in hits:
        matches = [entry for cat in data.get('categories', []) if cat['id'] == hit['category']
                   for entry in cat.get('entries', []) if entry['term'] == hit['term']]
        if len(matches) != 1:
            raise ValueError('vocabulary term has no unique category and term selector')
        full.append({'category': hit['category'], 'term': hit['term'], 'record': matches[0]})
    documents = []
    for name in source_paths(root, task, sources or []):
        ref = reader.select(name); raw = reader.read(ref); text = raw.decode('utf-8')
        documents.append({'file': ref, 'text': text, 'line_count': len(text.splitlines()),
                          'selection': 'Select an inclusive line range after reading the complete source.'})
    result = {'artifact_type': 'tactic-consultation', 'ok': True, 'task': task_ref, 'question': query,
              'vocabulary': {'path': str(path), 'sha256': c.digest(raw_vocabulary),
                             'category': category, 'limit': limit, 'results': full},
              'sources': documents, 'prior_applications': prior_applications(task),
              'coverage': 'Vocabulary matches are lexical candidates. Project tactic sources are returned in full, without inferred ranking.',
              'empty_result': 'An empty vocabulary result is not proof that the project has no useful tactic.',
              'application_template': {'source_id': None, 'reason': None, 'uses': [], 'not_used': []},
              'external_effect': False, 'budget_effect': 'none'}
    result['next_actions'] = [{'operation': 'apply-tactics', 'script': 'scripts/production_workflow.py',
        'args': {'root': str(root), 'task': task_path, 'consultation': out_dir + '/consultation.json',
                 'decisions': out_dir + '/decisions.json'}, 'required_args': ['out-dir'],
        'external_effect': False, 'budget_effect': 'none'}]
    def recheck():
        if c.read(path) != raw_vocabulary:
            raise ValueError('consulted vocabulary changed before publication')
    inputs._publish(root, out_dir, {'consultation.json': c.encoded(result),
                                   'decisions.json': c.encoded(result['application_template'])},
                    reader=reader, before_publish=recheck)
    return {**result, 'consultation': out_dir + '/consultation.json', 'decisions': out_dir + '/decisions.json'}


def selected_source(selector: dict, report: dict, root: Path, reader: InputEvidence) -> dict:
    """Resolve a selected passage or exact vocabulary entry without guessing."""
    if not isinstance(selector, dict):
        raise ValueError('select a source passage or vocabulary term')
    if selector.get('kind') == 'passage':
        c.exact(selector, {'kind', 'path', 'start_line', 'end_line'}, 'passage selector')
        matches = [row for row in report['sources'] if row['file']['path'] == selector['path']]
        if len(matches) != 1:
            raise ValueError('passage source was not consulted')
        row = matches[0]; raw = reader.read(row['file'])
        if raw.decode('utf-8') != row['text']:
            raise ValueError('consulted passage snapshot differs')
        quoted = m.line_span(raw, selector['start_line'], selector['end_line'])
        c.text(quoted, 'selected tactic passage')
        return {'selector': selector, 'file': row['file'], 'quote': quoted, 'source_text': row['text']}
    if selector.get('kind') == 'vocabulary':
        c.exact(selector, {'kind', 'category', 'term'}, 'vocabulary selector')
        ref = report['vocabulary']; path = Path(ref['path']); raw = c.read(path)
        if c.digest(raw) != ref['sha256']:
            raise ValueError('consulted vocabulary changed')
        matches = [row for row in ref['results'] if row['category'] == selector['category'] and row['term'] == selector['term']]
        if len(matches) != 1:
            raise ValueError('vocabulary selection was not consulted')
        data = c.decode(raw)
        actual = [entry for cat in data['categories'] if cat['id'] == selector['category']
                  for entry in cat['entries'] if entry['term'] == selector['term']]
        if len(actual) != 1 or c.content_id(actual[0]) != c.content_id(matches[0]['record']):
            raise ValueError('vocabulary record differs from the consulted entry')
        return {'selector': selector, 'file': {'path': str(path), 'sha256': ref['sha256']}, 'record': actual[0]}
    raise ValueError('source kind must be passage or vocabulary')


def apply(root: Path, task_path: str, report_path: str, decisions_path: str, out_dir: str) -> dict:
    import production_inputs as inputs
    import production_workflow as workflow
    root = root.resolve(strict=True); reader = InputEvidence(root)
    task_ref = reader.select(task_path); task = reader.json(task_ref); workflow.validate_task(task)
    report_ref = reader.select(report_path); report = reader.json(report_ref)
    choices_ref = reader.select(decisions_path); choices = reader.json(choices_ref)
    if report.get('artifact_type') != 'tactic-consultation' or report.get('ok') is not True:
        raise ValueError('select a successful tactic consultation')
    if report['task'] != task_ref:
        raise ValueError('consultation names a different task snapshot; consult the current task')
    c.exact(choices, {'source_id', 'reason', 'uses', 'not_used'}, 'tactic choices')
    source_id = c.text(choices['source_id'], 'source ID'); c.text(choices['reason'], 'application reason')
    if source_id in {row['id'] for row in task['sources']}:
        raise ValueError('application source ID already exists')
    if not isinstance(choices['uses'], list) or not isinstance(choices['not_used'], list):
        raise ValueError('uses and not_used must be explicit arrays')
    targets = {row['id']: row['path'] for row in task['sources']}
    if '@delivery' in targets:
        raise ValueError('source ID conflicts with the delivery selector')
    targets['@delivery'] = task['delivery']['path']
    known = {row['id'] for row in task['criteria']}
    applications = []; seen = set(); unused = []
    for use in choices['uses']:
        c.exact(use, {'source', 'borrowed', 'preserved', 'changed', 'target_source', 'target_locator',
                      'review_criteria', 'review_question'}, 'tactic application')
        for key in ('borrowed', 'preserved', 'changed', 'target_locator', 'review_question'):
            c.text(use[key], key)
        c.text(use['target_source'], 'target source ID')
        if use['target_source'] not in targets:
            raise ValueError('application target must be a declared source ID or @delivery')
        criteria = strings(use['review_criteria'], 'review criteria')
        if set(criteria) - known:
            raise ValueError('application names an unknown review criterion')
        source = selected_source(use['source'], report, root, reader)
        identity = c.content_id(use['source'])
        if identity in seen:
            raise ValueError('duplicate application source selector')
        seen.add(identity)
        target_ref = reader.select(targets[use['target_source']])
        applications.append({**copy.deepcopy(use), 'source_evidence': source, 'target_file': target_ref})
    for row in choices['not_used']:
        c.exact(row, {'source', 'reason'}, 'unused tactic'); c.text(row['reason'], 'nonuse reason')
        identity = c.content_id(row['source'])
        if identity in seen:
            raise ValueError('a source cannot be both selected and unused, or repeated')
        seen.add(identity)
        unused.append({**row, 'source_evidence': selected_source(row['source'], report, root, reader)})
    if not applications and not unused:
        raise ValueError('record a deliberate application or nonuse decision')
    path = out_dir + '/tactic-application.json'
    task_out = copy.deepcopy(task)
    task_out['sources'].append({'id': source_id, 'path': path, 'role': ROLE,
        'disposition': 'applied' if applications else 'considered-not-used',
        'locator': 'applications and not_used', 'reason': choices['reason']})
    task_out['delivery']['translation_notes'] += '\nRead source ' + source_id + ' for scoped craft applications and review questions.'
    workflow.validate_task(task_out)
    record = {'artifact_type': ROLE, 'task_id': task['task_id'], 'reason': choices['reason'],
              'consultation': report, 'consultation_file': report_ref, 'decisions_file': choices_ref,
              'applications': applications, 'not_used': unused,
              'assessment': 'Intended application only. Review actual outputs within the declared tactic scope.'}
    def recheck():
        for row in choices['uses'] + choices['not_used']:
            selected_source(row['source'], report, root, reader)
    inputs._publish(root, out_dir, {'tactic-application.json': c.encoded(record),
        'production-task.json': c.encoded(task_out), 'input-snapshots.json': c.encoded(reader.snapshots)},
        reader=reader, before_publish=recheck)
    return {'ok': True, 'task': out_dir + '/production-task.json', 'application': path,
            'execution_ready': False, 'external_effect': False, 'budget_effect': 'none',
            'next_actions': [{'operation': 'draft-inputs', 'script': 'scripts/production_workflow.py',
                'args': {'root': str(root), 'task': out_dir + '/production-task.json'},
                'required_args': ['out-dir'], 'external_effect': False, 'budget_effect': 'none'}]}


def review_questions(root: Path, task: dict, *, directory: Path | None = None,
                     dependencies: list[dict] | None = None) -> dict[str, list[str]]:
    output = {}
    for source in task['sources']:
        if source['role'] != ROLE or source['disposition'] != 'applied':
            continue
        if directory is None:
            record = c.load(c.local(root, source['path']))
        else:
            matches = [item for item in dependencies or []
                       if item['space'] == 'project' and item['path'] == source['path']]
            if len(matches) != 1:
                raise ValueError('application source has no unique prepared dependency')
            record = c.decode(c.object_read(directory, matches[0]['sha256']))
        if record.get('artifact_type') != ROLE or record.get('task_id') != task['task_id']:
            raise ValueError('tactic application belongs to a different task')
        for row in record['applications']:
            for criterion in row['review_criteria']:
                output.setdefault(criterion, []).append(row['review_question'])
    return output


def add_arguments(subparsers) -> None:
    for name in sorted(COMMANDS):
        parser = subparsers.add_parser(name, help='Consult directing knowledge or record its scoped use without execution.')
        parser.add_argument('--root', type=Path, required=True)
        parser.add_argument('--task', required=True)
        parser.add_argument('--out-dir', required=True)
        if name == 'consult-tactics':
            parser.add_argument('--query', required=True)
            parser.add_argument('--source', action='append', default=[])
            parser.add_argument('--vocabulary')
            parser.add_argument('--category')
            parser.add_argument('--limit', type=int, default=8)
        else:
            parser.add_argument('--consultation', required=True)
            parser.add_argument('--decisions', required=True)


def command(args, parser) -> dict:
    if args.command == 'consult-tactics':
        return consult(args.root, args.task, args.query, args.out_dir, sources=args.source,
                       vocabulary_path=args.vocabulary, category=args.category, limit=args.limit)
    return apply(args.root, args.task, args.consultation, args.decisions, args.out_dir)
