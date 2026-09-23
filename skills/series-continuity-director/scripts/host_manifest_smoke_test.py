#!/usr/bin/env python3
"""Exercise every host manifest rule.

Each case builds a repository in a temporary directory, damages one thing, and
declares the substring the refusal must contain. Matching the message rather than
the count keeps a case from passing on a different rule. The first case damages
nothing and must be admitted.

Usage:
  python <suite>/scripts/host_manifest_smoke_test.py
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
from tree_layout import SUITE, require_repository_root  # noqa: E402
from validate_host_manifests import check_tree  # noqa: E402

REPO = require_repository_root()
GENERATED = (
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".codex-plugin/plugin.json",
    ".agents/plugins/marketplace.json",
    "hooks/hooks.json",
    "hooks/codex.json",
    "AGENTS.md",
    "CLAUDE.md",
    "package-manifest.toml",
)


def build_tree(base: Path) -> tuple[Path, dict]:
    """A minimal repository that satisfies every rule."""

    manifest = tomllib.loads((REPO / "package-manifest.toml").read_text(encoding="utf-8"))
    suite = base / manifest["hosts"]["suite_root"]
    (suite / "scripts").mkdir(parents=True)
    shutil.copyfile(SUITE / "SKILL.md", suite / "SKILL.md")
    shutil.copyfile(
        SUITE / "scripts" / "session_entry_points.py",
        suite / "scripts" / "session_entry_points.py",
    )
    for relative in GENERATED:
        target = base / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / relative, target)
    return base, manifest


def edit_json(root: Path, relative: str, change: Callable[[dict], None]) -> None:
    path = root / relative
    value = json.loads(path.read_text(encoding="utf-8"))
    change(value)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="")


def name_the_standard_hooks(root: Path) -> None:
    edit_json(root, ".claude-plugin/plugin.json", lambda v: v.update(hooks="./hooks/hooks.json"))


def events_at_top_level(root: Path) -> None:
    path = root / "hooks/hooks.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(value["hooks"], indent=2) + "\n", encoding="utf-8", newline="")


def hook_points_nowhere(root: Path) -> None:
    (root / "skills/series-continuity-director/scripts/session_entry_points.py").unlink()


def marketplace_source_is_not_a_directory(root: Path) -> None:
    def change(value: dict) -> None:
        value["plugins"][0]["source"] = "./nowhere"
    edit_json(root, ".claude-plugin/marketplace.json", change)


def codex_source_is_not_a_directory(root: Path) -> None:
    def change(value: dict) -> None:
        value["plugins"][0]["source"] = {"source": "local", "path": "./nowhere"}
    edit_json(root, ".agents/plugins/marketplace.json", change)


def marketplace_names_another_plugin(root: Path) -> None:
    def change(value: dict) -> None:
        value["plugins"][0]["name"] = "something-else"
    edit_json(root, ".claude-plugin/marketplace.json", change)


def plugin_version_drifts(root: Path) -> None:
    edit_json(root, ".codex-plugin/plugin.json", lambda v: v.update(version="1.0.999"))


def guide_missing(root: Path) -> None:
    (root / "CLAUDE.md").unlink()


def plugin_manifest_loses_a_field(root: Path) -> None:
    edit_json(root, ".codex-plugin/plugin.json", lambda v: v.pop("description"))


def the_skill_disappears(root: Path) -> None:
    (root / "skills/series-continuity-director/SKILL.md").unlink()


CASES: list[tuple[str, Callable[[Path], None] | None, str]] = [
    ("a complete tree", None, ""),
    ("plugin manifest names the standard hooks file", name_the_standard_hooks, "loads on its own"),
    ("hook events sit at the top level", events_at_top_level, "top level"),
    ("hook command points at a missing file", hook_points_nowhere, "does not carry"),
    ("marketplace source is not a directory", marketplace_source_is_not_a_directory, "not a directory"),
    ("codex marketplace source is not a directory", codex_source_is_not_a_directory, "not a directory"),
    ("marketplace names another plugin", marketplace_names_another_plugin, "while the plugin manifest"),
    ("plugin version drifts from the package", plugin_version_drifts, "differs from the package version"),
    ("a required guide is missing", guide_missing, "CLAUDE.md: missing"),
    ("plugin manifest loses a required field", plugin_manifest_loses_a_field, "description must be"),
    ("the skill disappears", the_skill_disappears, "no SKILL.md"),
]


def main() -> int:
    results = []
    failures = []
    for name, damage, expected in CASES:
        with tempfile.TemporaryDirectory(prefix="scd-host-case-") as directory:
            root, manifest = build_tree(Path(directory))
            if damage is not None:
                damage(root)
            errors = check_tree(root, manifest)
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
