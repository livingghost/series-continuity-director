#!/usr/bin/env python3
"""Print what a session needs before it starts directing, and where it is reading it from.

Two things go unnoticed until they have already cost a run. The first is that the
suite a host reads is a copy, and a copy that was not updated stays behind while
the source moves on. The second is that a routing table cannot call itself: the
file that says which reference to open is a file somebody has to open.

This prints the installed location, the entry points, and, in
a project workspace, the roles whose asset is not settled. It is a plain command.
It writes to standard output and blocks nothing. It does not read standard input:
a host that sends JSON on the pipe and one that leaves the pipe open look the
same from here, and reading would hang on the second.

Usage:
  python scripts/session_entry_points.py [--project DIR]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_MANIFEST = "project-manifest.json"
PRODUCT = "series-continuity-director"



def entry_points() -> list[str]:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    section = text.split("## Entry points", 1)
    if len(section) < 2:
        return []
    body = section[1].split("\n## ", 1)[0]
    return [line for line in body.splitlines() if line.startswith("|")]


def project_root(start: Path) -> Path | None:
    for candidate in [start, *start.parents]:
        manifest = candidate / PROJECT_MANIFEST
        if not manifest.is_file():
            continue
        try:
            value = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if value.get("product") == PRODUCT:
            return candidate
    return None


def unsettled_roles(project: Path) -> list[str]:
    """Roles whose asset nobody has settled: no accepted member, or more than one."""

    registry = project / "asset-registry.md"
    if not registry.is_file():
        return []
    sys.path.insert(0, str(ROOT / "scripts"))
    from asset_registry import is_placeholder, parse  # noqa: PLC0415

    by_role: dict[str, list[str]] = {}
    for record in parse(registry.read_text(encoding="utf-8")):
        if is_placeholder(record):
            continue
        role = record["fields"].get("role")
        if role:
            by_role.setdefault(role, []).append(record["fields"].get("status", ""))
    unsettled = []
    for role, statuses in sorted(by_role.items()):
        accepted = statuses.count("accepted")
        if accepted == 1:
            continue
        unsettled.append(f"{role}: {accepted} accepted of {len(statuses)} records")
    return unsettled



def next_actions(project: Path) -> list[str]:
    """The next thing to do, in the order the layers depend on each other.

    There is no point reporting a scene with no shots while the narrative it
    hangs from is still a blank form, so the order is the order of the chain.
    """

    sys.path.insert(0, str(ROOT / "scripts"))
    from narrative import validate_narrative  # noqa: PLC0415
    from narrative_coverage import cover  # noqa: PLC0415
    # One reader for what a blank is. `narrative_index` owns it, the readme the
    # narrative directory ships says so, and a second copy here meant the same
    # blank was reported twice in one list of actions.
    from narrative_index import KINDS, entity_files, json_placeholders, placeholders, scan  # noqa: PLC0415
    from scene_plot import validate_scene_plot  # noqa: PLC0415

    entity = ROOT / "scripts" / "narrative_entity.py"
    actions: list[str] = []
    narrative_path = project / "narrative" / "narrative.json"
    if not narrative_path.is_file():
        # The narrative is the top of the chain; a directory without one is not a
        # project. init_project.py is what creates a project.
        return [
            f"{narrative_path} is missing, so this directory is not a project. "
            f"{ROOT / 'scripts' / 'init_project.py'} creates one."
        ]
    try:
        document = json.loads(narrative_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Repair {narrative_path}: {exc}"]

    report = validate_narrative(document)
    if not report["ok"]:
        shown = "; ".join(report["errors"])
        more = len(report["errors"]) - 3
        return [
            f"Answer the narrative's contract in {narrative_path}: {shown}"
            + (f" (and {more} more)" if more > 0 else "")
        ]

    blanks = json_placeholders(document)
    if blanks:
        more = len(blanks) - 3
        actions.append(
            f"Settle what the series is about: {narrative_path} still carries what "
            f"initialization wrote at {', '.join(blanks[:3])}"
            + (f" and {more} more" if more > 0 else "")
        )
    elif not report["approved"]:
        reason = "; ".join(report["approval_errors"]) or "it carries no approved block"
        actions.append(
            f"Approve the narrative: {reason}. "
            f"{ROOT / 'scripts' / 'narrative.py'} --content-sha256 prints the hash to record."
        )

    index = scan(project)
    for message in index["errors"]:
        actions.append(f"Repair a reference: {message}")
    for target, sources in list(index["dangling"].items())[:3]:
        actions.append(
            f"Write the file for {target!r}, named by {', '.join(sources)}: "
            f"{entity} --series {project} add <kind> {target}"
        )

    coverage = cover(narrative_path, project / "narrative" / "scenes", series=project)
    for message in coverage["errors"]:
        actions.append(f"Resolve a contradiction: {message}")

    for chapter in coverage["chapters"]:
        if not chapter["scenes"]:
            actions.append(
                f"Plan a scene for chapter {chapter['id']} ({chapter['title']}), which is "
                f"{chapter['status']} and has none: write a plot under "
                f"{project / 'narrative' / 'scenes'}"
            )
            break

    scenes = project / "narrative" / "scenes"
    if scenes.is_dir():
        for path in sorted(scenes.glob("*.json")):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(value, dict) or value.get("artifact_type") != "scene-plot":
                continue
            plot = validate_scene_plot(value)
            if plot["ok"] and not plot["approved"]:
                actions.append(
                    f"Approve the scene plot {path.name} before any shot text exists. "
                    f"{ROOT / 'scripts' / 'scene_plot.py'} --content-sha256 prints the hash."
                )
                break

    # `index["gaps"]` is one list of unlike findings: a file still carrying the
    # blank form, a persona document the narrative names and nobody wrote, and
    # an entity nothing in the series reaches. Only the last is a name it or
    # remove it, and the narrative's own blanks are already the first action
    # above, so reading the whole list under that one label reported those
    # blanks a second time and called them unnamed. Each kind is read here from
    # what the index states rather than from the sentence it wrote.
    for path in sorted(path for kind in KINDS for path in entity_files(project, kind)):
        count = placeholders(path.read_text(encoding="utf-8"))
        if count:
            actions.append(
                f"Fill in the form: {path.relative_to(project).as_posix()} still carries "
                f"{count} blank(s) nobody has filled"
            )
            break
    unreached = sorted(
        identifier for identifier in index["entities"] if identifier not in index["named"]
    )
    for identifier in unreached[:2]:
        record = index["entities"][identifier]
        actions.append(
            f"Name it or remove it: nothing in the series reaches {record['file']}, "
            f"the {record['kind']} {identifier!r}"
        )
    for message in coverage["gaps"][:3]:
        actions.append(f"Cover what the series declares: {message}")
    for role in unsettled_roles(project):
        actions.append(f"Settle the asset for {role}")
    return actions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Announce the suite and its entry points.")
    parser.add_argument("--project", type=Path, default=None)
    parser.add_argument(
        "--next", action="store_true",
        help="Print only the next deterministic actions for the project, one per line.",
    )
    arguments = parser.parse_args(argv)

    start = arguments.project or Path.cwd()
    if arguments.next:
        found = project_root(start.resolve())
        if found is None:
            print(
                "The working directory is not a project; "
                f"{ROOT / 'scripts' / 'init_project.py'} creates one."
            )
            return 1
        sys.path.insert(0, str(ROOT / "scripts"))
        import work_ledger  # noqa: PLC0415

        actions = next_actions(found)
        task = work_ledger.read_current(found)
        if task is not None:
            waiting = task.get("blocked_on")
            actions.insert(0, f"Continue the open task {task['task_id']} ({task['goal']}): "
                              + (f"it waits on: {waiting}" if waiting else f"{task.get('next')}"))
        print(chr(10).join(actions) if actions
              else "Nothing this command can read is unsettled.")
        return 0

    lines = [f"Series Continuity Director is installed at {ROOT}."]

    # Every path this prints is absolute. The reader's working directory is the
    # project, not the suite, so a bare `scripts/...` names nothing it can open.
    project = project_root(start.resolve())
    if project is None:
        # Outside a project there is nothing to route.
        print(
            f"{lines[0]} The working directory is not a project of this suite; "
            f"{ROOT / 'scripts' / 'init_project.py'} creates one."
        )
        return 0
    else:
        lines.append(f"Project workspace: {project}")
        # Where the work stands comes before everything else: a session that lost
        # its context continues the open task from here, not from memory.
        sys.path.insert(0, str(ROOT / "scripts"))
        import work_ledger  # noqa: PLC0415

        lines.append(work_ledger.show(project))
        roles = unsettled_roles(project)
        if roles:
            lines.append("Roles with no single accepted asset:")
            lines += [f"  {role}" for role in roles]
        else:
            lines.append("Every role in the registry has exactly one accepted asset.")
        actions = next_actions(project)
        if actions:
            lines.append("")
            lines.append("Next, in the order the layers depend on each other:")
            lines += [f"  {index}. {action}" for index, action in enumerate(actions, 1)]

    table = entry_points()
    if table:
        lines.append("")
        lines.append(f"Read these before performing the matching action. They are in {ROOT / 'references'}.")
        lines += table

    lines.append("")
    lines.append(
        "Before submitting any text to a generation surface, run "
        f"{ROOT / 'scripts' / 'submission_gate.py'} on it. It refuses what can be "
        "proved wrong without spending anything."
    )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
