#!/usr/bin/env python3
"""Exercise public tactic consultation commands with synthetic local authoring."""
from __future__ import annotations
import argparse
import difflib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import execution_contract as c


def call(root, operation, *args):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/production_workflow.py'), operation,
        '--root', str(root), '--task', 'task.json', *args], capture_output=True, text=True, encoding='utf-8', timeout=120)
    if result.returncode:
        raise ValueError(result.stdout + result.stderr)
    return json.loads(result.stdout)


def build(root):
    task = {'task_id': 'synthetic-craft', 'route': 'development', 'features': [],
            'sources': [], 'route_reading': 'reading.json',
            'delivery': {'path': 'delivery.txt', 'transport': 'authored-rendition',
                         'translation_notes': 'Use only the authored synthetic scope.'},
            'criteria': [{'id': 'readability', 'text': 'Keep the declared subject information readable.',
                          'strength': 'hard', 'evidence': 'text'}]}
    (root / 'delivery.txt').write_text('Synthetic local direction with readable subject information.\n', encoding='utf-8', newline='\n')
    import production_test_support
    task['sequence_plan'] = None
    task['direction'] = production_test_support.direction(task, 'Synthetic tactic consultation.')
    (root / 'task.json').write_bytes(c.encoded(task))
    original_task = (root / 'task.json').read_bytes()
    tactic = '# Synthetic production knowledge\n\nKeep the near shoulder out of the far subject eyes.\nRetain a readable separation between the two subjects.\n'
    (root / 'production-state.md').write_text(tactic, encoding='utf-8', newline='\n')
    original_delivery = (root / 'delivery.txt').read_bytes()
    opened = call(root, 'consult-tactics', '--query', 'over the shoulder', '--out-dir', 'consulted')
    if not opened['vocabulary']['results']:
        raise ValueError('The example query did not return directing vocabulary.')
    decisions = {'source_id': 'coverage-method', 'reason': 'Apply the scoped separation method to the authored coverage.',
        'uses': [{'source': {'kind': 'passage', 'path': 'production-state.md', 'start_line': 3, 'end_line': 4},
                  'borrowed': 'Shoulder placement that leaves the other subject readable.',
                  'preserved': 'The authored viewpoint and the visible separation.',
                  'changed': 'Use the relationship in this neutral local direction.',
                  'target_source': '@delivery', 'target_locator': 'Authored coverage instruction.',
                  'review_criteria': ['readability'],
                  'review_question': 'Does the actual coverage retain the declared readable separation?'}], 'not_used': []}
    (root / 'decisions.json').write_bytes(c.encoded(decisions))
    result = call(root, 'apply-tactics', '--consultation', opened['consultation'], '--decisions', 'decisions.json',
                  '--out-dir', 'applied')
    application = c.load(root / result['application'])
    import tactic_consultation
    questions = tactic_consultation.review_questions(root, c.load(root / result['task']))
    if (root / 'delivery.txt').read_bytes() != original_delivery:
        raise ValueError('The tool rewrote the authored direction.')
    return {'synthetic': True, 'vocabulary_terms': [row['term'] for row in opened['vocabulary']['results']],
            'source_paths': [row['file']['path'] for row in opened['sources']],
            'full_source_preserved': application['applications'][0]['source_evidence']['source_text'] == tactic,
            'selected_quote': application['applications'][0]['source_evidence']['quote'],
            'original_task_preserved': (root / 'task.json').read_bytes() == original_task,
            'authored_direction_preserved': True, 'review_questions': questions,
            'execution_ready': result['execution_ready'], 'external_effect': result['external_effect'],
            'budget_effect': result['budget_effect']}


def difference(expected, path):
    """A unified diff of the committed file against the rebuilt bytes.

    JSON compares field by field first, then as raw text. A carriage return
    prints as \\r, so a line-ending difference shows.
    """
    if not path.is_file():
        return f'{path} is missing.'
    found = path.read_bytes()
    for structured in (True, False):
        def lines(raw):
            text = raw.decode('utf-8', 'replace')
            if structured:
                try:
                    text = json.dumps(json.loads(text), indent=2, sort_keys=True)
                except ValueError:
                    pass
            return text.replace('\r', '\\r').split('\n')
        shown = '\n'.join(difflib.unified_diff(lines(found), lines(expected), f'{path.name} (committed)',
                                               f'{path.name} (rebuilt)', lineterm=''))
        if shown:
            return shown.encode('ascii', 'backslashreplace').decode('ascii')
    return f'{path} differs in bytes that do not decode as UTF-8.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--out', type=Path, default=Path(__file__).with_name('report.json'))
    parser.add_argument('--workspace', type=Path, help='New external directory retaining the actual commands and files.')
    args = parser.parse_args()
    if args.workspace is not None:
        args.workspace.mkdir(parents=True, exist_ok=False)
        result = build(args.workspace.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix='synthetic-craft-example-') as temporary:
            result = build(Path(temporary))
    raw = c.encoded(result)
    if args.check:
        if not args.out.is_file() or args.out.read_bytes() != raw:
            print(difference(raw, args.out), file=sys.stderr)
            raise SystemExit('Synthetic output differs. Rebuild this example.')
    else:
        args.out.write_bytes(raw)
    print(raw.decode(), end='')
    return 0


if __name__ == '__main__':
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
