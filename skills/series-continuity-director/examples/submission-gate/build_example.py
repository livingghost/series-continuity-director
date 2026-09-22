#!/usr/bin/env python3
"""Build synthetic, self-contained submissions from declared scenario inputs."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
import execution_contract as c
from submission_fixtures import current_submission
from submission_gate import gate


def build(destination: Path) -> list[dict]:
    fixtures = destination / 'fixtures'
    fixtures.mkdir(parents=True)
    for source in sorted((HERE / 'fixtures').iterdir()):
        if source.is_file() and source.name != 'submission-basis.txt':
            shutil.copyfile(source, fixtures / source.name)
    reports = []
    for source in sorted((HERE / 'sources').glob('*.json')):
        specimen = c.load(source)
        metadata = {key: specimen.pop(key) for key in tuple(specimen) if key.startswith('expected_')}
        submission = current_submission(specimen, destination, ROOT / 'protocols/target/profiles')
        report = gate(submission, ROOT / 'protocols/target/profiles', destination)
        actual = {item['code'] for item in report['errors']}
        if (report['status'] != metadata['expected_status']
                or metadata.get('expected_code') is not None and metadata['expected_code'] not in actual):
            raise ValueError(source.name + ': ' + json.dumps(report, ensure_ascii=False))
        (destination / source.name).write_bytes(c.encoded({**submission, **metadata}))
        reports.append({'case': source.stem, 'status': report['status'], 'codes': sorted(actual)})
    return reports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='submission-example-') as directory:
        root = Path(directory)
        report = build(root)
        generated = [path for path in root.rglob('*') if path.is_file() and path.name != '.execution.lock']
        for path in generated:
            target = HERE / path.relative_to(root)
            if args.check:
                if not target.is_file() or target.read_bytes() != path.read_bytes():
                    raise ValueError('Rebuild the synthetic submission example: ' + str(path.relative_to(root)))
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
    print(json.dumps({'synthetic': True, 'cases': report}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
