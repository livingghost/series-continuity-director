"""Print a command's report for whoever reads it.

A program reads a report as JSON, and a person reads it as text. A command
prints JSON when its output goes to a pipe or a file, or when `--json` is given,
and readable text when its output is a terminal. An agent that runs a command
captures its output, so it always receives JSON.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

_force_json = False
FIRST = ("ok",)
LAST = ("next",)
PROBLEMS = (("error", "error"), ("errors", "error"), ("warnings", "warning"))


def add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true",
                        help="Print the report as JSON, as a pipe or a file receives it")


def use_json(value: bool) -> None:
    global _force_json
    _force_json = bool(value)


def emit(report: Any) -> None:
    """Print one report: JSON for a program, text for a person at a terminal."""
    if _force_json or not sys.stdout.isatty() or not isinstance(report, dict):
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    else:
        print(render(report))


def render(report: dict[str, Any]) -> str:
    lines: list[str] = []
    if isinstance(report.get("ok"), bool):
        lines.append("ok" if report["ok"] else "failed")
    for key, label in PROBLEMS:
        value = report.get(key)
        for item in value if isinstance(value, list) else ([value] if value else []):
            lines.append(f"{label}: {_inline(item)}")
    skipped = {"ok", "next", *(key for key, _ in PROBLEMS)}
    for key, value in report.items():
        if key not in skipped:
            lines.extend(_field(key, value, 0))
    lines.extend(_next(report.get("next")))
    return "\n".join(lines)


def _inline(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return "none" if value is None else str(value).lower() if isinstance(value, bool) else str(value)


def _field(key: str, value: Any, depth: int) -> list[str]:
    indent = "  " * depth
    if isinstance(value, dict):
        if not value:
            return [f"{indent}{key}: none"]
        lines = [f"{indent}{key}:"]
        for child, item in value.items():
            lines.extend(_field(str(child), item, depth + 1))
        return lines
    if isinstance(value, list):
        if not value:
            return [f"{indent}{key}: none"]
        if all(not isinstance(item, (dict, list)) for item in value):
            return [f"{indent}{key}: {', '.join(_inline(item) for item in value)}"]
        return [f"{indent}{key}:", *(f"{indent}  - {_inline(item)}" for item in value)]
    return [f"{indent}{key}: {_inline(value)}"]


def _next(value: Any) -> list[str]:
    if not value:
        return []
    items = value if isinstance(value, list) else [value]
    lines = ["next:"]
    for item in items:
        if isinstance(item, dict) and "run" in item:
            lines.append(f"  {item['run']}")
            if item.get("why"):
                lines.append(f"    {item['why']}")
        else:
            lines.append(f"  {_inline(item)}")
    return lines
