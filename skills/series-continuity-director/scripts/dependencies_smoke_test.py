#!/usr/bin/env python3
"""Exercise declared optional dependencies and real bare-interpreter core imports."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import dependencies as d


class DependencyTests(unittest.TestCase):
    def test_requirements_match_declared_distributions(self):
        lines = (d.ROOT / 'requirements-media.txt').read_text().splitlines()
        self.assertEqual(lines, [rule['requirement'] for rule in d.declaration()['media']['distributions'].values()])

    def test_core_imports_on_bare_interpreter(self):
        for name in ('production_workflow', 'submission_gate', 'production_dispatch', 'production_inputs', 'route_reading'):
            process = subprocess.run([sys.executable, '-S', '-c',
                'import sys,importlib;sys.path.insert(0,sys.argv[1]);importlib.import_module(sys.argv[2])',
                str(d.ROOT / 'scripts'), name], capture_output=True, text=True, timeout=30)
            self.assertEqual(process.returncode, 0, name + ': ' + process.stderr)

    def test_all_source_imports_are_declared_and_isolated(self):
        files = list((d.ROOT / 'scripts').glob('*.py'))
        local = {path.stem for path in files}
        errors = [error for path in files for error in d.source_import_errors(path, d.declaration(), local)]
        self.assertEqual(errors, [])

    def inspect_source(self, source, name='operation.py'):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / name
            path.write_text(source, encoding='utf-8')
            return d.source_import_errors(path, d.declaration(), {'execution_contract'})

    def test_declared_function_import(self):
        self.assertEqual(self.inspect_source('def render():\n    from PIL import Image\n    return Image\n'), [])

    def test_declared_module_import_is_not_core_safe(self):
        self.assertTrue(self.inspect_source('from PIL import Image\n'))

    def test_unrelated_package_does_not_become_optional(self):
        self.assertTrue(self.inspect_source('def run():\n    import undeclared_dependency\n'))

    def test_test_module_can_require_its_media_environment(self):
        self.assertEqual(self.inspect_source('from PIL import Image\n', 'render_smoke_test.py'), [])

    def test_core_check_does_not_probe_media(self):
        with patch.object(d.importlib.metadata, 'version', side_effect=AssertionError('media dependency queried')):
            self.assertTrue(d.check('core')['ok'])

    def test_invalid_scope(self):
        with self.assertRaises(ValueError):
            d.check('other')

    def test_stable_numeric_release(self):
        self.assertEqual(d._release('2.9.0'), (2, 9, 0))
        with self.assertRaises(ValueError):
            d._release('2.9.0rc1')


if __name__ == '__main__':
    unittest.main()
