#!/usr/bin/env python3
"""Inspect declared runtime requirements and isolate media imports from core readers."""
from __future__ import annotations

import argparse
import ast
import importlib.metadata
import json
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


def check(scope: str) -> dict:
    declared = declaration()
    issues, found = [], {'python': '.'.join(map(str, sys.version_info[:3]))}
    if scope not in {'core', 'media'}:
        raise ValueError('select the core or media runtime')
    if tuple(sys.version_info[:2]) < tuple(declared['python_minimum']):
        issues.append('Python does not meet the declared minimum')
    if scope == 'media':
        for name, rule in declared['media']['distributions'].items():
            try:
                version = importlib.metadata.version(name)
                found[name] = version
                release = _release(version)
                if not tuple(rule['minimum_release']) <= release < tuple(rule['maximum_release_exclusive']):
                    issues.append(name + ' does not satisfy ' + rule['requirement'])
            except importlib.metadata.PackageNotFoundError:
                issues.append(name + ' is missing; install requirements-media.txt')
            except ValueError as error:
                issues.append(name + ': ' + str(error))
        for tool in declared['media']['executables']:
            executable = shutil.which(tool)
            if executable is None:
                issues.append(tool + ' is missing')
                continue
            try:
                process = subprocess.run([executable, '-version'], capture_output=True,
                                         text=True, timeout=15)
                found[tool] = process.stdout.splitlines()[0] if process.stdout else ''
                if process.returncode:
                    issues.append(tool + ' did not run')
            except (OSError, subprocess.TimeoutExpired) as error:
                issues.append(tool + ': ' + str(error))
    return {'ok': not issues, 'scope': scope, 'found': found,
            'errors': issues, 'installed': False}


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
    args = parser.parse_args()
    report = check(args.scope)
    print(json.dumps(report, indent=2))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
