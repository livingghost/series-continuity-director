#!/usr/bin/env python3
"""Exercise declared optional dependencies and real bare-interpreter core imports."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import dependencies as d


class DependencyTests(unittest.TestCase):
    def test_requirements_and_declaration_name_the_same_distributions(self):
        declared = json.loads((d.ROOT / 'config/dependencies.json').read_text(encoding='utf-8'))
        self.assertEqual(sorted(d.requirements()), sorted(declared['media']['distributions']))
        self.assertTrue(all(set(rule) == {'import'} for rule in declared['media']['distributions'].values()))

    def test_bounds_are_read_in_either_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'requirements-media.txt'
            path.write_text('Pillow>=12.3.0,<13\nresvg-py<0.6, >=0.5  # renderer\n', encoding='utf-8')
            with patch.object(d, 'REQUIREMENTS', path):
                bounds = d.requirements()
            self.assertEqual(bounds['Pillow']['minimum_release'], [12, 3, 0])
            self.assertEqual(bounds['resvg-py']['maximum_release_exclusive'], [0, 6])
            for broken in ('Pillow>=12', 'Pillow>=12,<13,<14', 'Pillow~=12.0', 'Pillow'):
                path.write_text(broken + '\n', encoding='utf-8')
                with self.subTest(line=broken), patch.object(d, 'REQUIREMENTS', path), self.assertRaises(ValueError):
                    d.requirements()

    def test_core_imports_on_bare_interpreter(self):
        for name in ('production_workflow', 'submission_gate', 'production_dispatch', 'production_inputs', 'route_reading'):
            process = subprocess.run([sys.executable, '-S', '-c',
                'import sys,importlib;sys.path.insert(0,sys.argv[1]);importlib.import_module(sys.argv[2])',
                str(d.ROOT / 'scripts'), name], capture_output=True, text=True, encoding='utf-8', timeout=30)
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

    def test_core_report_separates_required_from_optional(self):
        report = d.check('core')
        declared = d.declaration()['media']
        self.assertEqual([entry['name'] for entry in report['required']], ['Python'])
        self.assertEqual([entry['name'] for entry in report['optional']],
                         [*declared['distributions'], *declared['executables']])
        self.assertTrue(all(entry['status'] == 'not checked' for entry in report['optional']))
        self.assertIn('run --scope media', report['summary'])
        self.assertNotIn('installed', report)

    def test_every_media_requirement_says_what_it_enables(self):
        declared = d.declaration()['media']
        self.assertEqual(sorted(d.USES), sorted([*declared['distributions'], *declared['executables']]))

    def test_missing_media_names_what_it_affects(self):
        missing = d.importlib.metadata.PackageNotFoundError
        with patch.object(d.importlib.metadata, 'version', side_effect=missing('absent')), \
                patch.object(d.shutil, 'which', return_value=None):
            report = d.check('media')
        self.assertFalse(report['ok'])
        self.assertIn('Pillow', report['missing'])
        self.assertIn('ffprobe', report['missing'])
        self.assertTrue(any(message.startswith('ffprobe: missing') and 'affects probing audio' in message
                            for message in report['errors']), report['errors'])
        self.assertTrue(report['summary'].startswith('Not ready for media work'))

    def test_installed_distribution_that_does_not_import_is_not_ready(self):
        # Each distribution at its declared minimum, so the bounds can move without editing this test.
        versions = {name: '.'.join(map(str, rule['minimum_release']))
                    for name, rule in d.declaration()['media']['distributions'].items()}
        native = 'ImportError: DLL load failed while importing resvg_py'
        with patch.object(d.importlib.metadata, 'version', side_effect=versions.__getitem__), \
                patch.object(d, 'probe_error', side_effect=lambda name, module: native if name == 'resvg-py' else None), \
                patch.object(d.shutil, 'which', return_value=None):
            report = d.check('media')
        entry = next(item for item in report['required'] if item['name'] == 'resvg-py')
        self.assertEqual(entry['status'], 'installed, but does not work: ' + native)
        self.assertIn('resvg-py', report['missing'])
        self.assertNotIn('Pillow', report['missing'])

    def test_probe_error_names_the_failure(self):
        self.assertIsNone(d.probe_error('json', 'json'))
        self.assertIn('ModuleNotFoundError', d.probe_error('scd-missing', 'scd_module_that_does_not_exist'))

    def test_every_media_distribution_has_a_probe(self):
        self.assertEqual(sorted(d.PROBES), sorted(d.declaration()['media']['distributions']))

    def test_every_probe_passes_in_the_media_environment(self):
        for name, rule in d.declaration()['media']['distributions'].items():
            with self.subTest(distribution=name):
                self.assertIsNone(d.probe_error(name, rule['import']))

    def missing_report(self) -> dict:
        return {'ok': False, 'errors': [], 'required': [
            {'name': 'Python', 'kind': 'interpreter', 'status': 'ok'},
            {'name': 'resvg-py', 'kind': 'python distribution', 'status': 'missing; install requirements-media.txt'},
            {'name': 'ffmpeg', 'kind': 'executable', 'status': 'missing from the executable search path'},
            {'name': 'ffprobe', 'kind': 'executable', 'status': 'missing from the executable search path'}]}

    def test_plan_uses_pip_and_the_platform_package_manager(self):
        with patch.object(d.platform, 'system', return_value='Windows'), \
                patch.object(d, 'externally_managed', return_value=False), \
                patch.object(d.importlib.util, 'find_spec', return_value=object()), \
                patch.object(d.shutil, 'which', side_effect=lambda name: name if name == 'winget' else None):
            steps = d.install_plan(self.missing_report())
        self.assertEqual([step['manager'] for step in steps], ['pip', 'winget'])
        self.assertEqual(steps[0]['commands'], [[sys.executable, '-m', 'pip', 'install', '-r', str(d.REQUIREMENTS)]])
        self.assertIn('Gyan.FFmpeg', steps[1]['commands'][0])
        self.assertEqual(steps[1]['installs'], ['ffmpeg', 'ffprobe'])

    def test_system_managed_python_is_left_alone(self):
        with patch.object(d, 'externally_managed', return_value=True):
            step = d.python_step(['resvg-py'], None)
        self.assertEqual(step['commands'], [])
        self.assertIn('PEP 668', step['note'])
        self.assertIn('--venv', step['note'])

    def test_virtual_environment_is_created_then_filled(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / 'media-env'
            step = d.python_step(['resvg-py'], directory)
        target = str(d.venv_python(directory.absolute()))
        self.assertEqual(step['commands'], [[sys.executable, '-m', 'venv', str(directory.absolute())],
                                            [target, '-m', 'pip', 'install', '-r', str(d.REQUIREMENTS)]])
        self.assertEqual(step['interpreter'], target)

    def test_environment_without_pip_uses_uv(self):
        with patch.object(d, 'externally_managed', return_value=False), \
                patch.object(d.importlib.util, 'find_spec', return_value=None), \
                patch.object(d.shutil, 'which', side_effect=lambda name: name if name == 'uv' else None):
            step = d.python_step(['resvg-py'], None)
        self.assertEqual(step['commands'], [['uv', 'pip', 'install', '--python', sys.executable,
                                             '-r', str(d.REQUIREMENTS)]])

    def test_python_without_an_installer_is_named(self):
        with patch.object(d, 'externally_managed', return_value=False), \
                patch.object(d.importlib.util, 'find_spec', return_value=None), \
                patch.object(d.shutil, 'which', return_value=None):
            step = d.python_step(['resvg-py'], None)
        self.assertEqual(step['commands'], [])
        self.assertIn('no pip', step['note'])

    def test_system_package_manager_runs_through_sudo(self):
        with patch.object(d.platform, 'system', return_value='Linux'), \
                patch.object(d.shutil, 'which', side_effect=lambda name: name if name in {'apt-get', 'sudo'} else None), \
                patch.object(d.os, 'geteuid', return_value=1000, create=True):
            step = d.executable_step(['ffmpeg'])
        self.assertEqual(step['commands'], [['sudo', 'apt-get', 'install', '-y', 'ffmpeg']])

    def test_without_a_package_manager_the_plan_names_the_download(self):
        with patch.object(d.platform, 'system', return_value='Darwin'), \
                patch.object(d.shutil, 'which', return_value=None):
            step = d.executable_step(['ffmpeg', 'ffprobe'])
        self.assertEqual(step['commands'], [])
        self.assertIn('https://ffmpeg.org/download.html', step['note'])

    def test_install_without_confirmation_runs_nothing(self):
        steps = [{'installs': ['ffmpeg'], 'manager': 'brew', 'commands': [['brew', 'install', 'ffmpeg']]}]
        with patch.object(d.sys, 'stdin', SimpleNamespace(isatty=lambda: False)), \
                patch.object(d.subprocess, 'run', side_effect=AssertionError('a command ran unconfirmed')), \
                patch.object(d, 'check', side_effect=lambda scope: self.missing_report()):
            report = d.install(steps, assume_yes=False)
        self.assertTrue(any(message.startswith('nothing was installed') for message in report['errors']))

    def test_confirmed_install_runs_each_command_then_checks_again(self):
        steps = [{'installs': ['ffmpeg'], 'manager': 'brew', 'commands': [['brew', 'install', 'ffmpeg']]}]
        ran = []
        ready = {'ok': True, 'errors': [], 'required': [{'name': 'Python', 'kind': 'interpreter', 'status': 'ok'}]}
        with patch.object(d.subprocess, 'run', side_effect=lambda command, **_: ran.append(command) or SimpleNamespace(returncode=0)), \
                patch.object(d, 'check', side_effect=lambda scope: dict(ready)):
            report = d.install(steps, assume_yes=True)
        self.assertEqual(ran, [['brew', 'install', 'ffmpeg']])
        self.assertEqual(report['installed'], [{'run': d.shown(['brew', 'install', 'ffmpeg']), 'exit_status': 0}])
        self.assertTrue(report['ok'])

    def test_invalid_scope(self):
        with self.assertRaises(ValueError):
            d.check('other')

    def test_stable_numeric_release(self):
        self.assertEqual(d._release('2.9.0'), (2, 9, 0))
        with self.assertRaises(ValueError):
            d._release('2.9.0rc1')


if __name__ == '__main__':
    import stdio_utf8
    stdio_utf8.configure()
    unittest.main()
