#!/usr/bin/env python3
"""A report reaches a program as JSON and a person at a terminal as text."""
from __future__ import annotations

import io
import json
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import report_output

SCRIPTS = Path(__file__).resolve().parent
# Commands whose report a person runs directly; each takes --json.
COMMANDS = ("init_project.py", "init_line.py", "validate_project.py", "dependencies.py", "narrative.py",
            "scene_plot.py", "narrative_entity.py add", "submission_draft.py new", "visual_continuity.py build",
            "observe_schema.py schema")
REPORT = {"ok": False, "errors": ["names chapter 'ch01'; did you mean 'ch1'?"], "warnings": [],
          "project": "fixture", "plots": [{"plot": "sc01", "approved": True}],
          "next": [{"run": "python scripts/session_entry_points.py --project fixture --next",
                    "why": "lists what to settle next"}]}


class Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True


class ReportTests(unittest.TestCase):
    def tearDown(self) -> None:
        report_output.use_json(False)

    def printed(self, stream: io.StringIO) -> str:
        with redirect_stdout(stream):
            report_output.emit(REPORT)
        return stream.getvalue()

    def test_a_pipe_receives_json(self) -> None:
        self.assertEqual(json.loads(self.printed(io.StringIO())), REPORT)

    def test_a_terminal_receives_text(self) -> None:
        text = self.printed(Terminal())
        self.assertEqual(text.splitlines()[:2], ["failed", "error: names chapter 'ch01'; did you mean 'ch1'?"])
        self.assertIn("project: fixture", text)
        self.assertIn("next:\n  python scripts/session_entry_points.py --project fixture --next\n"
                      "    lists what to settle next", text)
        self.assertNotIn("warnings", text)

    def test_json_flag_wins_at_a_terminal(self) -> None:
        report_output.use_json(True)
        self.assertEqual(json.loads(self.printed(Terminal())), REPORT)

    def test_every_listed_command_takes_the_flag(self) -> None:
        for command in COMMANDS:
            script, *operation = command.split()
            done = subprocess.run([sys.executable, str(SCRIPTS / script), *operation, "--help"],
                                  capture_output=True, text=True, encoding="utf-8", timeout=60)
            with self.subTest(command=command):
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertIn("--json", done.stdout)


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    unittest.main(verbosity=2)
