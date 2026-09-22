#!/usr/bin/env python3
"""Build a deterministic summary from a synthetic, locally prepared production run."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import execution_contract as c
import production_workflow as w
import work_ledger


def summary(value):
    return {'integrity_ok': value['integrity']['ok'], 'current_inputs': value['freshness']['current'],
            'execution_state': value['execution']['state'],
            'reservation_states': [x['status'] for x in value['reservations']],
            'next': value['next'], 'available_operations': [x['operation'] for x in value['next_actions']]}


def build():
    with tempfile.TemporaryDirectory(prefix='synthetic-resume-example-') as temporary:
        root = Path(temporary)
        started = work_ledger.begin(root, 'Synthetic recovery example', ['inspect retained evidence'])
        (root / 'delivery.txt').write_text('Synthetic local instructions.\n')
        task = {'task_id': started['task_id'], 'route': 'development', 'features': [], 'sources': [],
                'delivery': {'path': 'delivery.txt', 'transport': 'authored-rendition',
                             'translation_notes': 'Synthetic authored fixture.'},
                'criteria': [{'id': 'output', 'strength': 'hard', 'text': 'Inspect retained output.'}]}
        run = prepare_fixture(root, task)
        command = [sys.executable, str(ROOT / 'scripts/production_workflow.py'), 'resume', '--root', str(root), '--run', run]
        before = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)
        if before.returncode != 0:
            raise ValueError(before.stdout + before.stderr)
        (root / 'delivery.txt').write_text('Revised synthetic local instructions.\n')
        after = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)
        if after.returncode != 1:
            raise ValueError('The changed fixture must require updated execution inputs.')
        return {'synthetic': True, 'before_change': summary(json.loads(before.stdout)),
                'after_change': summary(json.loads(after.stdout))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--out', type=Path, default=Path(__file__).with_name('report.json'))
    args = parser.parse_args()
    raw = (json.dumps(build(), indent=2, sort_keys=True) + '\n').encode()
    if args.check:
        if not args.out.is_file() or args.out.read_bytes() != raw:
            raise SystemExit('Synthetic report differs; rebuild it with this script.')
    else:
        args.out.write_bytes(raw)
    print(raw.decode(), end='')
    return 0


def prepare_fixture(root, task):
    import production_test_support as fixture
    from reading_fixtures import task_reading
    task['sequence_plan'] = None
    task['criteria'][0]['evidence'] = 'text'
    task['direction'] = fixture.direction(task, 'Synthetic local instructions.')
    task_reading(root, task)
    (root / 'task.json').write_bytes(c.encoded(task))
    run = w.prepare(root, 'task.json')['run']
    authorization = fixture.grant(w, root, run, operations=['submit'], outputs=1)
    directory, prepared, _, rows = w.load_run(root, run)
    # A synthetic managed executor reserves once without invoking a provider.
    w._reserve(directory, prepared, rows, authorization=authorization, actor='synthetic selector',
               operation='submit', scopes=['task'], request_sha256=c.content_id({'synthetic': True}), outputs=1)
    return run


if __name__ == '__main__':
    raise SystemExit(main())
