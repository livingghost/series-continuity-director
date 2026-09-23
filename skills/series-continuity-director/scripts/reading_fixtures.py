"""Synthetic reading records for executable examples and offline tests only."""
from __future__ import annotations
import io
import os
import tempfile
from pathlib import Path
import execution_contract as c
import route_reading as r

_WORK = tempfile.TemporaryDirectory(prefix='synthetic-reading-')


def fixture_reading(*, route: str = 'generation', features: list[str] | None = None,
                    project: Path | None = None, ledger: Path | None = None) -> dict:
    """Read full fixture documents, then author a labeled synthetic application.

    The documents that need an application are the ones `submission_draft.py`
    names in the placeholder it leaves for them.
    """
    from submission_draft import application_paths
    if ledger is None and project is None:
        raise ValueError('a synthetic project root is required')
    ledger = ledger if ledger is not None else project/'work/reads.jsonl'
    manifest, bodies = r.capture(route, features)
    key = c.content_id({'fixture': 'synthetic reading', 'manifest': manifest})[:32]
    issued = r.issue(route, features, ledger=ledger, stream=io.StringIO(), key=key,
                     at='2000-01-01T00:00:00Z', cwd='synthetic-fixture')
    required = set(application_paths(manifest['documents']))
    applications = {'applied': []}
    for meta, raw in bodies:
        if meta['kind'] == 'document' and meta['path'] in required:
            candidates = [block for block in r.prose_blocks(raw.decode('utf-8')) if len(block.split()) >= 12]
            if not candidates:
                raise ValueError('fixture needs a paragraph quotation in ' + meta['path'])
            applications['applied'].append({'path':meta['path'], 'quote':candidates[0],
                'why':'Exercise quotation integrity with synthetic input, not evidence of a real reading session.'})
    return r.build_record(issued, applications, ledgers=[ledger])


def task_reading(root: Path, task: dict) -> dict:
    record = fixture_reading(route=task['route'], features=task['features'], project=root)
    path = 'work/fixture-reading-' + c.content_id(record) + '.json'
    target = root/path; target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(c.encoded(record))
    task['route_reading'] = path
    return task
