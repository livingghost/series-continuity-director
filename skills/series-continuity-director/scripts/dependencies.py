#!/usr/bin/env python3
"""Inspect declared runtime requirements and isolate media imports from core readers.

`--scope media` also prints the commands that would install what is missing:
the installer of the running Python for the Python distributions, and the
platform's package manager for ffmpeg and ffprobe. `--install` runs them once
the user confirms, and `--venv DIR` puts the Python distributions in a virtual
environment instead of the running Python.
"""
from __future__ import annotations

import argparse
import ast
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import sysconfig

import report_output

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / 'requirements-media.txt'
# Package managers that install FFmpeg, which provides both ffmpeg and ffprobe,
# in the order they are tried on each platform. A manager is used only when it
# is on the executable search path; the first one found is chosen.
FFMPEG_MANAGERS = {
    'Windows': (
        ('winget', ['winget', 'install', '--exact', '--id', 'Gyan.FFmpeg',
                    '--accept-source-agreements', '--accept-package-agreements']),
        ('scoop', ['scoop', 'install', 'ffmpeg']),
        ('choco', ['choco', 'install', 'ffmpeg', '-y']),
    ),
    'Darwin': (('brew', ['brew', 'install', 'ffmpeg']),),
    'Linux': (
        ('apt-get', ['apt-get', 'install', '-y', 'ffmpeg']),
        ('pacman', ['pacman', '-S', '--noconfirm', 'ffmpeg']),
        ('apk', ['apk', 'add', 'ffmpeg']),
    ),
}
# Managers that install for the whole system and so run as root.
SYSTEM_MANAGERS = {'apt-get', 'pacman', 'apk'}


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
    'resvg-py': 'rendering an SVG reference to a raster',
    'defusedxml': 'parsing SVG sources safely before they are rendered',
    'tinycss2': 'checking the CSS inside SVG sources before they are rendered',
    'ffmpeg': 'rendering playable roughs and mixing audio for timed sequences',
    'ffprobe': 'probing audio and video files',
}


# The smallest operation each declared media distribution performs for the suite.
# It runs in a fresh interpreter, so a native part that imports but fails when
# used is found before a real operation depends on it.
PROBES = {
    'Pillow': ("import io\nfrom PIL import Image\nbuffer = io.BytesIO()\n"
               "Image.new('RGBA', (1, 1)).save(buffer, 'PNG')\n"
               "Image.open(io.BytesIO(buffer.getvalue())).load()\n"),
    'resvg-py': ("import resvg_py\n"
                 "drawn = bytes(resvg_py.svg_to_bytes(svg_string='<svg xmlns=\"http://www.w3.org/2000/svg\" "
                 "width=\"1\" height=\"1\"/>', width=1, height=1))\n"
                 "assert drawn.startswith(b'\\x89PNG'), 'resvg returned no PNG'\n"),
    'defusedxml': "from defusedxml.ElementTree import fromstring\nfromstring('<svg/>')\n",
    'tinycss2': "import tinycss2\ntinycss2.parse_declaration_list('fill: #000')\n",
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


def probe_error(distribution: str, module: str) -> str | None:
    """Why the distribution fails its smallest operation in a fresh interpreter, or None.

    A distribution can be installed while a native part it loads cannot be, or
    loads and then fails when used, so the version alone does not say the
    operation will run. The probe runs in its own process so a failed native
    load cannot affect this one.
    """
    code = PROBES.get(distribution, f'import {module}\n')
    try:
        process = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
                                 encoding='utf-8', errors='replace', timeout=120)
    except (OSError, subprocess.TimeoutExpired) as error:
        return str(error)
    if not process.returncode:
        return None
    lines = [line.strip() for line in process.stderr.splitlines() if line.strip()]
    reason = next((line for line in reversed(lines) if 'Error' in line.split(':', 1)[0]), lines[-1] if lines else '')
    return reason or f'exit status {process.returncode}'


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
        if not inside:
            entry['status'] = 'installed version does not satisfy ' + rule['requirement']
            return
        failure = probe_error(name, rule['import'])
        entry['status'] = 'ok' if failure is None else 'installed, but does not work: ' + failure
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


def externally_managed() -> bool:
    """Whether the system owns the running interpreter's packages (PEP 668).

    Debian, Ubuntu and Homebrew mark their Python this way, and pip refuses to
    install into it. A virtual environment made from it is not marked.
    """
    if sys.prefix != sys.base_prefix:
        return False
    return (Path(sysconfig.get_path('stdlib')) / 'EXTERNALLY-MANAGED').is_file()


def venv_python(directory: Path) -> Path:
    return directory / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def python_step(names: list[str], venv: Path | None) -> dict:
    """How the missing Python distributions reach the interpreter that will run the suite."""
    requirements = ['-r', str(REQUIREMENTS)]
    if venv is not None:
        target = venv_python(venv.absolute())
        commands = [] if target.is_file() else [[sys.executable, '-m', 'venv', str(venv.absolute())]]
        commands.append([str(target), '-m', 'pip', 'install', *requirements])
        return {'installs': names, 'manager': 'pip', 'commands': commands, 'interpreter': str(target)}
    if externally_managed():
        return {'installs': names, 'manager': None, 'commands': [],
                'note': "the system manages this Python's packages (PEP 668), so pip does not install into it; "
                        'pass --venv DIR to install them into a virtual environment, then run the suite with '
                        "that environment's Python"}
    if importlib.util.find_spec('pip') is not None:
        return {'installs': names, 'manager': 'pip',
                'commands': [[sys.executable, '-m', 'pip', 'install', *requirements]]}
    if shutil.which('uv') is not None:
        # A virtual environment uv creates carries no pip of its own.
        return {'installs': names, 'manager': 'uv',
                'commands': [['uv', 'pip', 'install', '--python', sys.executable, *requirements]]}
    return {'installs': names, 'manager': None, 'commands': [],
            'note': 'this Python has no pip and uv is not on the executable search path; install pip for it, '
                    'or pass --venv DIR to install into a virtual environment'}


def executable_step(names: list[str]) -> dict:
    """How the platform's package manager would install the missing executables."""
    for manager, command in FFMPEG_MANAGERS.get(platform.system(), ()):
        if shutil.which(manager) is None:
            continue
        if manager in SYSTEM_MANAGERS and getattr(os, 'geteuid', lambda: 0)() != 0 and shutil.which('sudo'):
            command = ['sudo', *command]
        return {'installs': names, 'manager': manager, 'commands': [command]}
    return {'installs': names, 'manager': None, 'commands': [],
            'note': 'no supported package manager was found; install FFmpeg, which provides ffmpeg and '
                    'ffprobe, from https://ffmpeg.org/download.html and put it on the executable search path'}


def install_plan(report: dict, venv: Path | None = None) -> list[dict]:
    """The commands that would install what the checked scope is missing, in order."""
    missing = [entry for entry in report['required'] if entry['status'] != 'ok' and entry['name'] != 'Python']
    steps = []
    distributions = [entry['name'] for entry in missing if entry['kind'] == 'python distribution']
    if distributions:
        steps.append(python_step(distributions, venv))
    executables = [entry['name'] for entry in missing if entry['kind'] == 'executable']
    if executables:
        steps.append(executable_step(executables))
    return steps


def shown(command: list[str]) -> str:
    return subprocess.list2cmdline(command) if os.name == 'nt' else shlex.join(command)


def next_steps(steps: list[dict], venv: Path | None = None) -> list[dict]:
    rows = []
    for step in steps:
        installs = ', '.join(step['installs'])
        if not step['commands']:
            rows.append({'run': step['note'], 'why': 'installs ' + installs})
        for command in step['commands']:
            rows.append({'run': shown(command), 'why': f"installs {installs} with {step['manager']}"})
    if any(step['commands'] for step in steps):
        rerun = [sys.executable, str(Path(__file__).resolve()), '--scope', 'media', '--install']
        if venv is not None:
            rerun += ['--venv', str(venv.absolute())]
        rows.append({'run': shown(rerun), 'why': 'runs the commands above after you confirm them'})
    return rows


def check_with(interpreter: str) -> dict:
    """The media check as another interpreter sees it."""
    done = subprocess.run([interpreter, str(Path(__file__).resolve()), '--scope', 'media', '--json'],
                          capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
    try:
        report = json.loads(done.stdout)
    except ValueError:
        report = check('media')
        report['errors'].append(f'{interpreter} could not be checked: {done.stderr.strip()[-400:]}')
    report['interpreter'] = interpreter
    return report


def confirmed(assume_yes: bool) -> bool:
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        return False
    return input('Run these commands? [y/N] ').strip().lower() in {'y', 'yes'}


def install(steps: list[dict], assume_yes: bool, venv: Path | None = None) -> dict:
    """Run the plan once confirmed, then check again with the interpreter that received it."""
    commands = [command for step in steps for command in step['commands']]
    for command in commands:
        print('will run: ' + shown(command), file=sys.stderr)
    if commands and not confirmed(assume_yes):
        report = check('media')
        report['next'] = next_steps(steps, venv)
        report['errors'].append('nothing was installed: confirm the commands at a terminal, or pass --yes '
                                'once the user has approved them')
        return report
    ran = []
    for command in commands:
        # The installer's own output goes to standard error, so standard output
        # keeps only the report.
        done = subprocess.run(command, stdout=sys.stderr, stderr=sys.stderr, check=False)
        ran.append({'run': shown(command), 'exit_status': done.returncode})
        if done.returncode:
            break
    interpreter = next((step['interpreter'] for step in steps if step.get('interpreter')), None)
    report = check_with(interpreter) if interpreter else check('media')
    report['installed'] = ran
    remaining = install_plan(report, venv)
    if remaining:
        report['next'] = next_steps(remaining, venv)
        if platform.system() == 'Windows' and any(step['manager'] not in (None, 'pip', 'uv') for step in steps):
            report['errors'].append('an executable installed by a package manager may be found only in a new '
                                    'terminal, where the updated search path applies; open one and check again')
    if interpreter:
        report.setdefault('next', []).append({'run': interpreter + ' <script>',
                                              'why': "run the suite's media commands with this Python"})
    return report


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
    parser.add_argument('--install', action='store_true',
                        help='With --scope media, run the printed install commands after confirmation')
    parser.add_argument('--yes', action='store_true',
                        help='Confirm --install without asking. Pass it only after the user has approved the '
                             'printed commands.')
    parser.add_argument('--venv', type=Path, metavar='DIR',
                        help='With --scope media, install the Python distributions into a virtual environment '
                             'at DIR, created when absent, instead of the running Python')
    report_output.add_json_flag(parser)
    args = parser.parse_args()
    report_output.use_json(args.json)
    if args.install and args.scope != 'media':
        parser.error('--install applies to --scope media')
    if args.yes and not args.install:
        parser.error('--yes confirms --install')
    if args.venv is not None and args.scope != 'media':
        parser.error('--venv applies to --scope media')
    report = check(args.scope)
    if args.scope == 'media':
        steps = install_plan(report, args.venv)
        if args.install and steps:
            report = install(steps, args.yes, args.venv)
        elif steps:
            report['next'] = next_steps(steps, args.venv)
    report_output.emit(report)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
