#!/usr/bin/env python3
"""Prepare and compare noncanonical creative alternatives against pinned sources.

prepare --project WORK --spec options.json
status  --project WORK --workspace options-ID
select  --project WORK --workspace options-ID --alternative ID --actor NAME --reason TEXT --evidence FILE
export  --project WORK --workspace options-ID --out reviews/NAME

All mutations stay in creative-options/. Selection does not write narrative,
scene, state, asset, production authority or canonical records.
"""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import tempfile
from typing import Any

import artifact_review
import execution_contract as c

ID = re.compile(r'^options-[0-9a-f]{32}$')


def _texts(value: Any, label: str) -> None:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(label + ' must be a list of nonempty strings')


def validate(spec: Any) -> None:
    c.exact(spec, {'purpose', 'intent', 'sources', 'alternatives'}, 'creative options')
    c.text(spec['purpose'], 'purpose')
    c.exact(spec['intent'], {'durable', 'focus'}, 'intent')
    c.text(spec['intent']['durable'], 'durable intent')
    c.text(spec['intent']['focus'], 'current focus')
    if not isinstance(spec['sources'], list):
        raise ValueError('sources must be a list')
    known = set()
    for source in spec['sources']:
        c.exact(source, {'id', 'path', 'role'}, 'source')
        for key in ('id', 'path', 'role'):
            c.text(source[key], 'source ' + key)
        if source['id'] in known:
            raise ValueError('duplicate source id')
        known.add(source['id'])
    if not isinstance(spec['alternatives'], list) or not spec['alternatives']:
        raise ValueError('at least one explicitly authored alternative is required')
    ids = set()
    for option in spec['alternatives']:
        c.exact(option, {'id', 'title', 'plan', 'rationale', 'preserves', 'changes', 'uncertainties', 'trace'}, 'alternative')
        for key in ('id', 'title', 'plan', 'rationale'):
            c.text(option[key], 'alternative ' + key)
        if option['id'] in ids:
            raise ValueError('duplicate alternative id')
        ids.add(option['id'])
        for key in ('preserves', 'changes', 'uncertainties'):
            _texts(option[key], key)
        if not isinstance(option['trace'], list):
            raise ValueError('trace must be a list')
        for link in option['trace']:
            c.exact(link, {'source', 'locator', 'target', 'treatment', 'reason'}, 'trace link')
            if link['source'] not in known:
                raise ValueError('trace refers to an undeclared source')
            if link['treatment'] not in {'preserve', 'transform', 'omit', 'repeat', 'hold'}:
                raise ValueError('unknown trace treatment')
            for key in ('locator', 'target', 'reason'):
                c.text(link[key], 'trace ' + key)
    # Coverage is an authored explanation, not an exactly-once beat rule.


def directory(root: Path, identifier: str, *, exists: bool = True) -> Path:
    if not isinstance(identifier, str) or not ID.fullmatch(identifier):
        raise ValueError('invalid creative workspace id')
    return c.local(root, 'creative-options/' + identifier, exists=exists)


def prepare(root: Path, spec_path: str) -> dict:
    root = artifact_review.workspace(root)
    with c.lock(root):
        raw = c.read(c.local(root, spec_path))
        spec = c.decode(raw)
        validate(spec)
        paths = {spec_path} | {s['path'] for s in spec['sources']} | {o['plan'] for o in spec['alternatives']}
        payload = {p: c.read(c.local(root, p)) for p in sorted(paths)}
        if payload[spec_path] != raw:
            raise ValueError('options specification changed during preparation')
        for option in spec['alternatives']:
            try:
                c.text(payload[option['plan']].decode('utf-8'), 'alternative plan')
            except UnicodeDecodeError as exc:
                raise ValueError('alternative plans must be inspectable UTF-8 text') from exc
        identifier = 'options-' + secrets.token_hex(16)
        target = directory(root, identifier, exists=False)
        target.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix='.pending-', dir=target.parent))
        try:
            dependencies = [{'path': path, 'sha256': c.object_store(stage, data), 'size': len(data)}
                            for path, data in payload.items()]
            prepared = {'workspace': identifier, 'spec_path': spec_path, 'spec': spec, 'dependencies': dependencies}
            prepared['input_sha256'] = c.content_id(prepared)
            c.atomic(stage / 'prepared.json', c.encoded(prepared))
            # Detect concurrent edits by writers that do not respect the project lock.
            for path, data in payload.items():
                if c.read(c.local(root, path)) != data:
                    raise ValueError('source changed during preparation: ' + path)
            c.publish_directory(stage, target)
            c.fsync_dir(target.parent)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    return {'ok': True, 'workspace': identifier, 'input_sha256': prepared['input_sha256'],
            'alternatives': len(spec['alternatives']), 'canonical_changes': False}


def load(root: Path, identifier: str) -> tuple[Path, dict]:
    root = artifact_review.workspace(root)
    folder = directory(root, identifier)
    prepared = c.load(c.local(folder, 'prepared.json'))
    c.exact(prepared, {'workspace', 'spec_path', 'spec', 'dependencies', 'input_sha256'}, 'prepared options')
    check = dict(prepared)
    expected = check.pop('input_sha256')
    if c.content_id(check) != expected or prepared['workspace'] != identifier:
        raise ValueError('options snapshot integrity mismatch')
    validate(prepared['spec'])
    deps = prepared['dependencies']
    if not isinstance(deps, list) or any(not isinstance(dep, dict) for dep in deps):
        raise ValueError('invalid source dependency list')
    paths = [dep.get('path') for dep in deps]
    spec = prepared['spec']
    required = {prepared['spec_path']} | {src['path'] for src in spec['sources']} | {option['plan'] for option in spec['alternatives']}
    if len(paths) != len(set(paths)) or set(paths) != required:
        raise ValueError('source dependencies must match every declared source and alternative exactly')
    for dep in deps:
        c.exact(dep, {'path', 'sha256', 'size'}, 'source dependency')
        c.local(root, dep['path'], exists=False)
        if isinstance(dep['size'], bool) or not isinstance(dep['size'], int) or dep['size'] < 0:
            raise ValueError('source size must be a nonnegative integer')
        if len(c.object_read(folder, dep['sha256'])) != dep['size']:
            raise ValueError('options source size mismatch')
    spec_dep = next((d for d in prepared['dependencies'] if d['path'] == prepared['spec_path']), None)
    if spec_dep is None or c.decode(c.object_read(folder, spec_dep['sha256'])) != prepared['spec']:
        raise ValueError('options specification does not match its pinned source')
    return folder, prepared


def status(root: Path, identifier: str) -> dict:
    folder, prepared = load(root, identifier)
    changed = []
    for dep in prepared['dependencies']:
        try:
            if c.digest(c.read(c.local(root, dep['path']))) != dep['sha256']:
                changed.append({'path': dep['path'], 'reason': 'content changed'})
        except (OSError, ValueError):
            changed.append({'path': dep['path'], 'reason': 'missing or unreadable'})
    selection_path = c.local(folder, 'selected.json', exists=False)
    selection = None
    if selection_path.exists():
        pointer = c.load(selection_path)
        c.exact(pointer, {'selection_sha256'}, 'selection pointer')
        selection = c.decode(c.object_read(folder, pointer['selection_sha256']))
        c.exact(selection, {'workspace', 'input_sha256', 'alternative', 'actor', 'reason', 'evidence', 'plan'}, 'selection')
        if selection['input_sha256'] != prepared['input_sha256'] or selection['workspace'] != identifier:
            raise ValueError('selection belongs to another input')
        matches = [o for o in prepared['spec']['alternatives'] if o['id'] == selection['alternative']]
        if len(matches) != 1:
            raise ValueError('selection names an unknown alternative')
        dep = next(d for d in prepared['dependencies'] if d['path'] == matches[0]['plan'])
        if selection['plan'] != dep:
            raise ValueError('selected plan is not the prepared alternative')
        c.object_read(folder, selection['evidence']['sha256'])
    return {'ok': True, 'workspace': identifier, 'current': not changed, 'changed_sources': changed,
            'spec': prepared['spec'], 'selection': selection,
            'input_sha256': prepared['input_sha256'], 'canonical_changes': False}


def select(root: Path, identifier: str, alternative: str, actor: str, reason: str, evidence: str) -> dict:
    root = artifact_review.workspace(root)
    for label, value in [('actor', actor), ('reason', reason)]:
        c.text(value, label)
    with c.lock(root):
        current = status(root, identifier)
        if not current['current']:
            raise ValueError('source content changed; prepare alternatives against the current sources')
        folder, prepared = load(root, identifier)
        matches = [o for o in prepared['spec']['alternatives'] if o['id'] == alternative]
        if len(matches) != 1:
            raise ValueError('select one declared alternative')
        evidence_bytes = c.read(c.local(root, evidence))
        if not evidence_bytes.strip():
            raise ValueError('selection evidence must not be empty')
        plan = next(d for d in prepared['dependencies'] if d['path'] == matches[0]['plan'])
        choice = {'workspace': identifier, 'input_sha256': prepared['input_sha256'],
                  'alternative': alternative, 'actor': actor, 'reason': reason,
                  'evidence': {'path': evidence, 'sha256': c.object_store(folder, evidence_bytes)}, 'plan': plan}
        key = c.object_store(folder, c.encoded(choice))
        if not status(root, identifier)['current']:
            raise ValueError('source content changed during selection')
        c.atomic(folder / 'selected.json', c.encoded({'selection_sha256': key}), replace=True)
    return {'ok': True, 'workspace': identifier, 'selection_sha256': key,
            'plan_object': str(folder / 'objects' / plan['sha256']),
            'canonical_changes': False,
            'limit': 'Records a planning choice and its stated evidence. It is not production or canonical approval.'}


def export(root: Path, identifier: str, out: str) -> dict:
    root = artifact_review.workspace(root)
    with c.lock(root):
        current = status(root, identifier)
        folder, prepared = load(root, identifier)
        files = {}
        body = ['<p>' + ('Sources match.' if current['current'] else 'STALE: source content changed.') + '</p>',
                '<p>Choosing an alternative does not alter accepted work, production permission, or canon.</p>',
                '<pre>' + html.escape(json.dumps(current, ensure_ascii=False, indent=2)) + '</pre>']
        by_path = {d['path']: d for d in prepared['dependencies']}
        for option in current['spec']['alternatives']:
            data = c.object_read(folder, by_path[option['plan']]['sha256'])
            name = 'plans/' + by_path[option['plan']]['sha256'] + '.txt'
            files[name] = data
            body += ['<h2>' + html.escape(option['title']) + '</h2><pre>'
                     + html.escape(data.decode('utf-8')) + '</pre>']
        from evaluation_evidence import _page
        files['index.html'] = _page('Creative alternatives', '\n'.join(body))
        files['options.json'] = c.encoded(current)
        target = artifact_review.publish(root, out, files)
    return {'ok': True, 'current': current['current'], 'output': str(target), 'canonical_changes': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('prepare', 'status', 'select', 'export'):
        p = sub.add_parser(command)
        p.add_argument('--project', type=Path, required=True)
        if command == 'prepare':
            p.add_argument('--spec', required=True)
        else:
            p.add_argument('--workspace', required=True)
        if command == 'export':
            p.add_argument('--out', required=True)
        if command == 'select':
            for flag in ('alternative', 'actor', 'reason', 'evidence'):
                p.add_argument('--' + flag, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            result = prepare(args.project, args.spec)
        elif args.command == 'status':
            result = status(args.project, args.workspace)
        elif args.command == 'select':
            result = select(args.project, args.workspace, args.alternative, args.actor, args.reason, args.evidence)
        else:
            result = export(args.project, args.workspace, args.out)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, StopIteration) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
