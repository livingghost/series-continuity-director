#!/usr/bin/env python3
"""Generate the host specific files from the single source tree.

The repository is laid out as a plugin, so there is no second copy of the suite
anywhere. `skills/series-continuity-director/` is the suite and also the skill a
plugin host loads; `.claude-plugin/`, `.codex-plugin/`, `.agents/`, `hooks/`,
`AGENTS.md` and `CLAUDE.md` sit beside it at the repository root and are generated
from `[hosts]` in package-manifest.toml.

The core is host neutral. Nothing under the suite root names a host, and nothing
in this file does either. It knows three `kind` values:

  plugin         the repository itself is the plugin, so this writes the plugin
                 manifest, the hook file the table names, and the marketplace
                 entry that points back at the same tree
  manifest-file  one manifest whose shape belongs to a host, from a template
  entry-file     one generated file, filled from a template under hosts/
  hooks-file     one hook file, rendered from the shared source for that host's
                 plugin-root variable

Adding a host that fits an existing kind is a table entry, and a template beside
it. Neither touches this code.

Every path in `[hosts]` is relative to the repository root, which is the plugin
root. `suite_root` says where this suite sits inside it, and a build reads only
from the tree it is given, never from wherever this file happens to be installed.

Usage:
  python scripts/build_host_packages.py [--check]

`--check` regenerates into a temporary directory and compares, so a generated
file that stopped matching the source fails before it is published.
"""
from __future__ import annotations

import argparse
import filecmp
import json
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tree_layout import SUITE, repository_root  # noqa: E402

MANIFEST_NAME = "package-manifest.toml"


def load_manifest(repo: Path) -> dict:
    return tomllib.loads((repo / MANIFEST_NAME).read_text(encoding="utf-8"))


def hosts(manifest: dict) -> dict[str, dict]:
    """The host tables, separated from the fields the hosts share."""

    return {name: value for name, value in manifest["hosts"].items() if isinstance(value, dict)}


def suite_of(manifest: dict, repo: Path) -> Path:
    return repo / manifest["hosts"]["suite_root"]


def entry_point_table(suite: Path) -> str:
    text = (suite / "SKILL.md").read_text(encoding="utf-8")
    section = text.split("## Entry points", 1)
    if len(section) < 2:
        return ""
    body = section[1].split("\n## ", 1)[0]
    return "\n".join(line for line in body.splitlines() if line.startswith("|"))


def fields(manifest: dict, repo: Path) -> dict[str, Any]:
    """What a template, a generated manifest, or a declared path may be filled from.

    Every value comes from the tree being built. A build that reached outside it
    for one of them would produce a different file depending on where the script
    was run from, and the check that compares them would be comparing two trees.
    """

    shared = {key: value for key, value in manifest["hosts"].items() if not isinstance(value, dict)}
    return {
        "name": manifest["package"]["name"],
        "version": manifest["package"]["version"],
        "entry_points": entry_point_table(suite_of(manifest, repo)),
        **shared,
    }


def output_path(manifest: dict, host: dict, repo: Path) -> str:
    """A declared output path, with the shared fields filled in.

    `suite_root` is declared once. A host that writes inside the suite composes
    its path from that value rather than repeating it, so moving the suite moves
    every output with it.
    """

    return host["output"].format(**fields(manifest, repo))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="")


PLUGIN_ROOT_PLACEHOLDER = "__PLUGIN_ROOT__"


def render_hooks(repo: Path, source: str, root_variable: str) -> dict:
    """One hook definition, written against one host's plugin-root variable.

    The source names the plugin root as a placeholder because no variable name is
    common to every host: Claude Code sets CLAUDE_PLUGIN_ROOT and no neutral
    equivalent, and Codex sets PLUGIN_ROOT and carries CLAUDE_PLUGIN_ROOT as a
    compatibility alias. Rendering the one source per host lets each read its own
    canonical name without a second definition to keep in step.
    """

    text = (repo / source).read_text(encoding="utf-8")
    if PLUGIN_ROOT_PLACEHOLDER not in text:
        raise RuntimeError(
            f"{source}: names no {PLUGIN_ROOT_PLACEHOLDER}, so a host would receive a command "
            "that resolves nothing"
        )
    hooks = json.loads(text.replace(PLUGIN_ROOT_PLACEHOLDER, "${" + root_variable + "}"))
    # The event names sit under `hooks`, or under `modules`. A file that puts
    # them at the top level parses, ships, and is ignored, and the only symptom
    # is a hook that never runs.
    if not ({"hooks", "modules"} & set(hooks)):
        raise RuntimeError(
            f"{source}: the top level must carry 'hooks' or 'modules'; found {sorted(hooks)}"
        )
    return hooks


def build_hooks_file(manifest: dict, host: dict, repo: Path, base: Path) -> list[str]:
    relative = output_path(manifest, host, repo)
    write_json(base / relative, render_hooks(repo, host["source"], host["root_variable"]))
    return [relative]


def build_plugin(manifest: dict, host: dict, repo: Path, base: Path) -> list[str]:
    common = fields(manifest, repo)
    plugin = {
        "name": common["name"],
        "version": common["version"],
        "description": common["description"],
        "author": {"name": common["author"]},
        # A homepage is optional. The table either carries one or the manifest
        # does not claim one, rather than carrying an empty string.
        **({"homepage": common["homepage"]} if common.get("homepage") else {}),
        "license": common["license"],
    }
    written = [host["manifest"]]

    if "hooks_source" in host:
        hooks = render_hooks(repo, host["hooks_source"], host["hooks_root_variable"])
        write_json(base / host["hooks_output"], hooks)
        written.append(host["hooks_output"])
        # The standard hook path is loaded on its own, so the manifest does not
        # name it. The key is for hook files kept somewhere else, and this
        # package keeps none there.

    write_json(base / host["manifest"], plugin)

    if "marketplace" in host:
        write_json(base / host["marketplace"], {
            "name": common["marketplace_name"],
            "owner": {"name": common["author"]},
            "description": host["marketplace_description"],
            "plugins": [{
                "name": common["name"],
                "source": host["marketplace_source"],
                "description": common["description"],
            }],
        })
        written.append(host["marketplace"])
    return written


def build_entry_file(manifest: dict, host: dict, repo: Path, base: Path) -> list[str]:
    template = (repo / host["template"]).read_text(encoding="utf-8")
    relative = output_path(manifest, host, repo)
    out = base / relative
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(template.format(**fields(manifest, repo)), encoding="utf-8", newline="")
    return [relative]


def build_manifest_file(manifest: dict, host: dict, repo: Path, base: Path) -> list[str]:
    """A host manifest whose shape belongs to that host, so it comes from a template.

    The values are the same ones every other package carries; only the shape
    differs, and the shape is the host's business rather than this file's.
    """

    template = (repo / host["template"]).read_text(encoding="utf-8")
    rendered = template.format(**fields(manifest, repo))
    try:
        value = json.loads(rendered)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{host['template']}: rendered to invalid JSON: {error}") from None
    relative = output_path(manifest, host, repo)
    write_json(base / relative, value)
    return [relative]


BUILDERS: dict[str, Callable[[dict, dict, Path, Path], list[str]]] = {
    "entry-file": build_entry_file,
    "hooks-file": build_hooks_file,
    "manifest-file": build_manifest_file,
    "plugin": build_plugin,
}


def declared_hosts(manifest: dict) -> list[tuple[str, dict]]:
    declared = sorted(hosts(manifest).items())
    for name, host in declared:
        if host.get("kind") not in BUILDERS:
            raise RuntimeError(
                f"host {name!r} declares kind {host.get('kind')!r}, which has no builder"
            )
    return declared


def missing_sources(manifest: dict, repo: Path) -> list[str]:
    """Declared inputs this tree does not carry, so nothing can be rebuilt from it."""

    absent = {
        relative
        for _, host in declared_hosts(manifest)
        for relative in (host.get("template"), host.get("hooks_source"), host.get("source"))
        if relative and not (repo / relative).is_file()
    }
    return sorted(absent)


def build_all(manifest: dict, repo: Path, base: Path) -> list[str]:
    written: list[str] = []
    for _, host in declared_hosts(manifest):
        written += BUILDERS[host["kind"]](manifest, host, repo, base)
    return written


def check_tree(repo: Path, manifest: dict) -> list[str]:
    """Every generated file the table declares, against a fresh build from the sources.

    Rebuilding needs the sources the table names, and every tree that carries the
    manifest carries them too: they are release members. A tree holding one
    without the other is damaged, not a case this does not apply to, so it is
    reported here rather than reaching a builder and raising on the open.
    """

    absent = missing_sources(manifest, repo)
    if absent:
        return [f"{relative}: declared by [hosts] and not in this tree" for relative in absent]

    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="scd-hosts-") as directory:
        staging = Path(directory)
        for relative in build_all(manifest, repo, staging):
            current = repo / relative
            if not current.is_file():
                problems.append(relative + ": missing")
            elif not filecmp.cmp(staging / relative, current, shallow=False):
                problems.append(relative + ": stale, run scripts/build_host_packages.py")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the host specific files.")
    parser.add_argument("--check", action="store_true",
                        help="Compare what is on disk with a fresh build.")
    arguments = parser.parse_args(argv)
    repo = repository_root()
    if repo is None:
        reason = (
            f"no {MANIFEST_NAME} at or above {SUITE}, so the generated host files are not here"
        )
        if not arguments.check:
            print(reason, file=sys.stderr)
            return 2
        print(json.dumps({"ok": True, "errors": [], "unmeasured": [reason]},
                         ensure_ascii=False, indent=2))
        return 0
    manifest = load_manifest(repo)

    if suite_of(manifest, repo).resolve() != SUITE:
        print(f"hosts.suite_root does not lead from {repo} back to {SUITE}", file=sys.stderr)
        return 2

    if not arguments.check:
        absent = missing_sources(manifest, repo)
        if absent:
            print(f"{repo} does not carry {', '.join(absent)}, which [hosts] declares",
                  file=sys.stderr)
            return 2
        # Generated somewhere else and moved into place, so a build that fails
        # partway leaves the previous files intact.
        with tempfile.TemporaryDirectory(prefix="scd-hosts-") as directory:
            staging = Path(directory)
            written = build_all(manifest, repo, staging)
            for relative in written:
                target = repo / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(staging / relative, target)
        print(json.dumps({"ok": True, "written": written}, ensure_ascii=False, indent=2))
        return 0

    problems = check_tree(repo, manifest)
    print(json.dumps({"ok": not problems, "errors": problems}, ensure_ascii=False, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
