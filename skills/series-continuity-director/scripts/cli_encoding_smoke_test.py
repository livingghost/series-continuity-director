#!/usr/bin/env python3
"""Commands write UTF-8 and finish cleanly when the console locale is not UTF-8.

The stream encoding is forced to a Western code page through PYTHONIOENCODING,
which reproduces a non-UTF-8 console on every platform. CI also runs this file on
Windows without UTF-8 mode, where the runner's own code page applies.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SUITE = SCRIPTS.parent
GUARD = re.compile(r"""^if\s+__name__\s*==\s*['"]__main__['"]\s*:""", re.MULTILINE)


def legacy_environment() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in {"PYTHONUTF8", "PYTHONIOENCODING"}}
    env["PYTHONIOENCODING"] = "cp1252"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([sys.executable, *args], capture_output=True, env=legacy_environment(), timeout=120)


class EncodingTests(unittest.TestCase):
    def test_text_outside_the_code_page_is_written_and_saved_once(self) -> None:
        # U+20BB7 is outside cp1252 and cp932, so a locale stream cannot encode it.
        goal = "\U00020bb7"
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            created = run(str(SCRIPTS / "init_project.py"), "--out", str(project),
                          "--series-id", "ENC-01", "--title", "Encoding")
            self.assertEqual(created.returncode, 0, created.stderr.decode("utf-8", "replace"))
            began = run(str(SCRIPTS / "work_ledger.py"), "--project", str(project),
                        "begin", "--goal", goal, "--step", "check")
            self.assertEqual(began.returncode, 0, began.stderr.decode("utf-8", "replace"))
            self.assertIn(goal, began.stdout.decode("utf-8"))
            shown = run(str(SCRIPTS / "work_ledger.py"), "--project", str(project), "show")
            self.assertEqual(shown.returncode, 0, shown.stderr.decode("utf-8", "replace"))
            self.assertIn(goal, shown.stdout.decode("utf-8"))

    def test_every_command_configures_its_streams(self) -> None:
        commands = [*sorted(SCRIPTS.glob("*.py")), *sorted(SUITE.glob("examples/*/*.py"))]
        missing = []
        for path in commands:
            text = path.read_text(encoding="utf-8")
            if GUARD.search(text) and "stdio_utf8.configure()" not in text:
                missing.append(path.relative_to(SUITE).as_posix())
        self.assertEqual(missing, [], "commands that do not call stdio_utf8.configure()")


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    unittest.main(verbosity=2)
