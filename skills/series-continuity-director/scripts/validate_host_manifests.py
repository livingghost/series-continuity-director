#!/usr/bin/env python3
"""Check the generated host manifests against what each host accepts.

Three shapes that cost a hook or a plugin:

  - A plugin manifest that names the standard hooks file declares the same file
    twice. The host loads that path on its own; the key is for hook files kept
    somewhere else, and this package keeps none there.
  - A hooks file with the event names at the top level is ignored, and the hook
    never runs.
  - A hook command pointing at a file the package does not carry fails when it is
    needed.

Nothing here calls a host's own tool, so the checks run wherever Python does.

Usage:
  python <suite>/scripts/validate_host_manifests.py [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tree_layout import SUITE, require_repository_root  # noqa: E402

STANDARD_HOOKS = "hooks/hooks.json"
# Each host reads its own file under its own plugin-root variable. A command
# written for one host and shipped to the other resolves nothing there.
HOOK_FILES = {
    STANDARD_HOOKS: "${CLAUDE_PLUGIN_ROOT}",
    "hooks/codex.json": "${PLUGIN_ROOT}",
}
HOOK_EVENTS = {
    "SessionStart", "SessionEnd", "UserPromptSubmit", "PreToolUse", "PostToolUse",
    "Notification", "Stop", "SubagentStop", "PreCompact",
}


def read_json(path: Path, errors: list[str]) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        errors.append(f"{path.name}: missing")
    except json.JSONDecodeError as error:
        errors.append(f"{path.name}: invalid JSON: {error}")
    return None


def check_plugin_manifest(repo: Path, relative: str, errors: list[str], *, hooks_key: bool) -> None:
    value = read_json(repo / relative, errors)
    if value is None:
        return
    for field in ("name", "version", "description"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            errors.append(f"{relative}: {field} must be a non-empty string")
    author = value.get("author")
    if not isinstance(author, dict) or not isinstance(author.get("name"), str):
        errors.append(f"{relative}: author must be an object carrying a name")
    if hooks_key and value.get("hooks") == "./" + STANDARD_HOOKS:
        errors.append(
            f"{relative}: names {STANDARD_HOOKS}, which the host loads on its own. "
            "The key is for hook files kept somewhere else, and this package keeps none there."
        )


def check_marketplace(
    repo: Path, relative: str, plugin_name: str, errors: list[str], *, owner_required: bool
) -> None:
    value = read_json(repo / relative, errors)
    if value is None:
        return
    if not isinstance(value.get("name"), str) or not value["name"].strip():
        errors.append(f"{relative}: name must be a non-empty string")
    owner = value.get("owner")
    if owner_required and (not isinstance(owner, dict) or not isinstance(owner.get("name"), str)):
        errors.append(f"{relative}: owner must be an object carrying a name")
    plugins = value.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        errors.append(f"{relative}: plugins must be a non-empty array")
        return
    for entry in plugins:
        if not isinstance(entry, dict):
            errors.append(f"{relative}: every plugins entry must be an object")
            continue
        if not isinstance(entry.get("name"), str) or not entry["name"].strip():
            errors.append(f"{relative}: plugins entry needs a non-empty name")
        # One host writes the source as a path, the other as an object carrying
        # the kind and the path.
        source = entry.get("source")
        path = source.get("path") if isinstance(source, dict) else source
        if not isinstance(path, str) or not path.strip():
            errors.append(f"{relative}: plugins entry needs a source path")
        elif not path.startswith(("http://", "https://")) and not (repo / path).resolve().is_dir():
            errors.append(f"{relative}: plugins source {path!r} is not a directory in this repository")
        if entry.get("name") != plugin_name:
            errors.append(
                f"{relative}: plugins entry names {entry.get('name')!r} while the plugin manifest "
                f"names {plugin_name!r}"
            )


def check_hooks(repo: Path, relative: str, root_variable: str, errors: list[str]) -> None:
    value = read_json(repo / relative, errors)
    if value is None:
        return
    stray = sorted(set(value) & HOOK_EVENTS)
    if stray:
        errors.append(
            f"{relative}: event names {stray} sit at the top level, where the host ignores them. "
            "They belong under 'hooks'."
        )
    if not ({"hooks", "modules"} & set(value)):
        errors.append(f"{relative}: the top level must carry 'hooks' or 'modules'; found {sorted(value)}")
        return
    for event, matchers in (value.get("hooks") or {}).items():
        if event not in HOOK_EVENTS:
            errors.append(f"{relative}: {event!r} is not a hook event this suite knows about")
        for matcher in matchers if isinstance(matchers, list) else []:
            for hook in (matcher.get("hooks") or []) if isinstance(matcher, dict) else []:
                command = hook.get("command", "") if isinstance(hook, dict) else ""
                if root_variable not in command:
                    errors.append(
                        f"{relative}: the {event} command does not name {root_variable}, "
                        "which is the only plugin root this host expands"
                    )
                for target in re.findall(re.escape(root_variable) + r"/([^\"' ]+)", command):
                    if not (repo / target).is_file():
                        errors.append(
                            f"{relative}: the {event} command points at {target}, "
                            "which this package does not carry"
                        )


def check_version_alignment(repo: Path, manifest: dict, errors: list[str]) -> None:
    version = manifest["package"]["version"]
    for relative in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        value = read_json(repo / relative, errors)
        if value is not None and value.get("version") != version:
            errors.append(
                f"{relative}: version {value.get('version')!r} differs from the package version {version!r}"
            )
    for relative in ("AGENTS.md", "CLAUDE.md"):
        path = repo / relative
        if not path.is_file():
            errors.append(f"{relative}: missing")


def check_tree(repo: Path, manifest: dict, *, suite: Path | None = None) -> list[str]:
    """Every host rule, against one tree."""

    errors: list[str] = []
    name = manifest["package"]["name"]

    check_plugin_manifest(repo, ".claude-plugin/plugin.json", errors, hooks_key=True)
    check_plugin_manifest(repo, ".codex-plugin/plugin.json", errors, hooks_key=False)
    check_marketplace(repo, ".claude-plugin/marketplace.json", name, errors, owner_required=True)
    check_marketplace(repo, ".agents/plugins/marketplace.json", name, errors, owner_required=False)
    for relative, root_variable in HOOK_FILES.items():
        check_hooks(repo, relative, root_variable, errors)
    check_version_alignment(repo, manifest, errors)

    declared = (repo / manifest["hosts"]["suite_root"]).resolve()
    if suite is not None and declared != suite:
        errors.append(f"hosts.suite_root does not lead from {repo} back to {suite}")
    if not (declared / "SKILL.md").is_file():
        errors.append("the skill a host loads has no SKILL.md")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the generated host manifests.")
    parser.add_argument("--json", action="store_true")
    parser.parse_args(argv)

    repo = require_repository_root()
    manifest = tomllib.loads((repo / "package-manifest.toml").read_text(encoding="utf-8"))
    errors = check_tree(repo, manifest, suite=SUITE)

    print(json.dumps({"ok": not errors, "checks": 7, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
