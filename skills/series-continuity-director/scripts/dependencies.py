#!/usr/bin/env python3
"""Inspect declared runtime requirements and isolate media imports from core readers."""
from __future__ import annotations

import argparse
import ast
import importlib.metadata
import json
import report_output
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def declaration() -> dict:
    return json.loads((ROOT / 'config/dependencies.json').read_text(encoding='utf-8'))


def _release(value: str) -> tuple[int, ...]:
    parts = value.split('.')
    if not parts or any(not part.isascii() or not part.isdecimal() for part in parts):
        raise ValueError('the declared runtime requires a stable numeric release')
    return tuple(int(part) for part in parts)


# What each declared media requirement is needed for, so a report can say what
# a missing one affects. The versions and names stay in config/dependencies.json.
USES = {
    'Pillow': 'reading and measuring images, and decoding reference rasters',
    'CairoSVG': 'rendering an SVG reference to a raster',
    'defusedxml': 'parsing SVG sources safely before they are rendered',
    'tinycss2': 'checking the CSS inside SVG sources before they are rendered',
    'ffmpeg': 'rendering playable roughs and mixing audio for timed sequences',
    'ffprobe': 'probing audio and video files',
}


def _entry(name: str, kind: str, requirement: str, needed_for: str) -> dict:
    return {'name': name, 'kind': kind, 'requirement': requirement, 'found': None,
            'status': 'not checked', 'needed_for': needed_for}


def _media_entries(declared: dict) -> list[dict]:
    entries = [_entry(name, 'python distribution', rule['requirement'],
                      USES.get(name, 'media operations'))
               for name, rule in declared['media']['distributions'].items()]
    entries += [_entry(tool, 'executable', tool + ' on the executable search path',
                       USES.get(tool, 'media operations'))
                for tool in declared['media']['executables']]
    return entries


def _probe(entry: dict, rule: dict | None) -> None:
    """Fill one media entry from what is installed."""
    name = entry['name']
    if rule is not None:
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            entry['status'] = 'missing; install requirements-media.txt'
            return
        entry['found'] = version
        try:
            release = _release(version)
        except ValueError as error:
            entry['status'] = str(error)
            return
        inside = tuple(rule['minimum_release']) <= release < tuple(rule['maximum_release_exclusive'])
        entry['status'] = 'ok' if inside else 'installed version does not satisfy ' + rule['requirement']
        return
    executable = shutil.which(name)
    if executable is None:
        entry['status'] = 'missing from the executable search path'
        return
    try:
        process = subprocess.run([executable, '-version'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15)
    except (OSError, subprocess.TimeoutExpired) as error:
        entry['status'] = 'did not run: ' + str(error)
        return
    entry['found'] = process.stdout.splitlines()[0] if process.stdout else executable
    entry['status'] = 'ok' if not process.returncode else 'did not run'


def check(scope: str) -> dict:
    """Report what the chosen scope requires, what it does not, and what is missing.

    `required` is what the scope needs, and `ok` is whether all of it is there.
    `optional` is what the scope does not need, with the work it enables. The
    command inspects; it installs nothing.
    """
    if scope not in {'core', 'media'}:
        raise ValueError('select the core or media runtime')
    declared = declaration()
    minimum = '.'.join(map(str, declared['python_minimum']))
    python = _entry('Python', 'interpreter', '>=' + minimum,
                    'every command; core authoring, state and contract readers need nothing else')
    python['found'] = '.'.join(map(str, sys.version_info[:3]))
    python['status'] = ('ok' if tuple(sys.version_info[:2]) >= tuple(declared['python_minimum'])
                        else 'older than the declared minimum ' + minimum)
    media = _media_entries(declared)
    if scope == 'media':
        rules = declared['media']['distributions']
        for entry in media:
            _probe(entry, rules.get(entry['name']))
        required, optional = [python, *media], []
    else:
        required, optional = [python], media
    missing = [entry for entry in required if entry['status'] != 'ok']
    errors = [f"{entry['name']}: {entry['status']}; affects {entry['needed_for']}" for entry in missing]
    if missing:
        summary = (f"Not ready for {scope} work: " + ', '.join(entry['name'] for entry in missing)
                   + ' ' + ('is' if len(missing) == 1 else 'are') + ' not usable.')
    elif scope == 'core':
        summary = ('Ready for core work. The media requirements were not checked; '
                   'run --scope media before media work.')
    else:
        summary = 'Ready for core and media work.'
    return {'ok': not missing, 'scope': scope, 'summary': summary, 'required': required,
            'optional': optional, 'missing': [entry['name'] for entry in missing],
            'errors': errors, 'changes': 'none; this command inspects and installs nothing'}


def source_import_errors(path: Path, declared: dict, local_modules: set[str]) -> list[str]:
    """Check declared dependency ownership and the scope of each import statement."""
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    optional = {rule['import'] for rule in declared['media']['distributions'].values()}
    test_module = path.name.endswith('_smoke_test.py')
    errors = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name.split('.')[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module.split('.')[0]]
        else:
            continue
        for name in names:
            if name in sys.stdlib_module_names or name in local_modules:
                continue
            location = f'scripts/{path.name}:{node.lineno}'
            if name not in optional:
                errors.append(location + ': undeclared runtime dependency ' + repr(name))
                continue
            parent = parents.get(node)
            while parent is not None and not isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                parent = parents.get(parent)
            if parent is None and not test_module:
                errors.append(location + ': optional media dependency must be imported inside its operation: ' + name)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', choices=['core', 'media'], default='core')
    report_output.add_json_flag(parser)
    args = parser.parse_args()
    report_output.use_json(args.json)
    report = check(args.scope)
    report_output.emit(report)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
