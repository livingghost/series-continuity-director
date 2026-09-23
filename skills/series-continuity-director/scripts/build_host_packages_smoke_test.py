#!/usr/bin/env python3
"""Exercise every way the host package build can refuse.

Each case builds a repository in a temporary directory, damages one thing, and
declares the substring the refusal must contain. Matching the message rather than
the count keeps a case from passing on a different rule. The first case damages
nothing and must be admitted.

The tree is built by generating into it, so a complete tree passes by
construction and every case below is a departure from one that did.

Usage:
  python <suite>/scripts/build_host_packages_smoke_test.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_host_packages import build_all, check_tree, load_manifest  # noqa: E402
from tree_layout import SUITE, require_repository_root  # noqa: E402

REPO = require_repository_root()


def build_tree(base: Path) -> Path:
    """A minimal repository that the builder can rebuild from end to end."""

    manifest = tomllib.loads((REPO / "package-manifest.toml").read_text(encoding="utf-8"))
    shutil.copyfile(REPO / "package-manifest.toml", base / "package-manifest.toml")
    shutil.copytree(REPO / "hosts", base / "hosts")
    suite = base / manifest["hosts"]["suite_root"]
    suite.mkdir(parents=True)
    shutil.copyfile(SUITE / "SKILL.md", suite / "SKILL.md")
    # Generated into the tree it describes, which is what a build does.
    build_all(manifest, base, base)
    return base


def rewrite(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"{path.name}: nothing to damage; {old!r} is not there")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")


def template_is_missing(root: Path) -> None:
    (root / "hosts/shared/repository-guide.md.template").unlink()


def hook_source_is_missing(root: Path) -> None:
    (root / "hosts/shared/hooks.json").unlink()


def a_generated_file_was_edited(root: Path) -> None:
    path = root / "CLAUDE.md"
    path.write_text(path.read_text(encoding="utf-8") + "\nEdited by hand.\n",
                    encoding="utf-8", newline="")


def a_generated_file_was_deleted(root: Path) -> None:
    (root / ".claude-plugin/plugin.json").unlink()


def a_host_declares_an_unknown_kind(root: Path) -> None:
    rewrite(root / "package-manifest.toml", 'kind = "entry-file"', 'kind = "sculpture"')


def hook_events_sit_at_the_top_level(root: Path) -> None:
    path = root / "hosts/shared/hooks.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(value["hooks"], indent=2) + "\n", encoding="utf-8", newline="")


def the_hook_source_names_no_plugin_root(root: Path) -> None:
    # Every occurrence: one left behind still renders, and the rule under test is
    # that a source naming none of them is refused.
    path = root / "hosts/shared/hooks.json"
    path.write_text(path.read_text(encoding="utf-8").replace("__PLUGIN_ROOT__", "/somewhere"),
                    encoding="utf-8", newline="")


def a_template_renders_to_invalid_json(root: Path) -> None:
    rewrite(root / "hosts/codex/plugin.json.template", '"skills": "./skills",', '"skills": "./skills"')


CASES: list[tuple[str, Callable[[Path], None] | None, str]] = [
    ("a complete tree", None, ""),
    ("a declared template is missing", template_is_missing, "not in this tree"),
    ("a declared hook source is missing", hook_source_is_missing, "not in this tree"),
    ("a generated file was edited by hand", a_generated_file_was_edited, "stale"),
    ("a generated file was deleted", a_generated_file_was_deleted, "missing"),
    ("a host declares an unknown kind", a_host_declares_an_unknown_kind, "has no builder"),
    ("hook events sit at the top level", hook_events_sit_at_the_top_level, "top level must carry"),
    ("the hook source names no plugin root", the_hook_source_names_no_plugin_root,
     "names no __PLUGIN_ROOT__"),
    ("a template renders to invalid JSON", a_template_renders_to_invalid_json,
     "rendered to invalid JSON"),
]


def refusals(root: Path) -> list[str]:
    """What the check reports, with a raised refusal read as one more of them.

    A damaged table or a damaged template stops the build rather than producing a
    finding. Both are refusals, and a caller cares which rule fired, not how the
    rule chose to say so.
    """

    try:
        return check_tree(root, load_manifest(root))
    except RuntimeError as error:
        return [str(error)]


def main() -> int:
    results = []
    failures = []
    for name, damage, expected in CASES:
        with tempfile.TemporaryDirectory(prefix="scd-build-case-") as directory:
            root = build_tree(Path(directory))
            if damage is not None:
                damage(root)
            errors = refusals(root)
        results.append({"case": name, "errors": errors})
        if damage is None:
            if errors:
                failures.append(f"{name}: a complete tree was refused: {errors}")
            continue
        if not errors:
            failures.append(f"{name}: nothing was refused")
        elif not any(expected in item for item in errors):
            failures.append(f"{name}: refused, but not for {expected!r}: {errors}")

    print(json.dumps({
        "ok": not failures,
        "checks": len(results),
        "results": results,
        "errors": failures,
    }, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
