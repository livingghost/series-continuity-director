#!/usr/bin/env python3
"""Print what a session needs before it starts directing, and where it is reading it from.

Two things go unnoticed until they have already cost a run. The first is that the
suite a host reads is a copy, and a copy that was not updated stays behind while
the source moves on. The second is that a routing table cannot call itself: the
file that says which reference to open is a file somebody has to open.

This prints the version and location of the copy it runs from. When the working
directory is inside another copy of this product, such as its source checkout,
it compares the two versions and says which copy is behind; at one version it
compares their SKILL.md. `--compare DIR` compares with a copy named explicitly.
In a project workspace it then prints the open task, the roles whose asset is
not settled, the next actions and the entry points. Outside a project it prints
the first line alone.

It writes to standard output and blocks nothing. It does not read standard
input: a host that sends JSON on the pipe and one that leaves the pipe open look
the same from here, and reading would hang on the second.

`--hook` is the session hook's mode. Any failure prints one line naming the
problem and the file, and the exit status stays 0, so the hook's
`python3 ... || python ...` fallback runs only when python3 is absent.

Usage:
  python scripts/session_entry_points.py [--project DIR] [--compare DIR] [--next] [--hook]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
import traceback
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
PROJECT_MANIFEST = "project-manifest.json"
PRODUCT = "series-continuity-director"
PACKAGE_MANIFEST = "package-manifest.toml"


class Unreadable(Exception):
    """A file this command reads could not be read, named with the problem."""

    def __init__(self, path: Path, cause: BaseException) -> None:
        super().__init__(f"{path}: {type(cause).__name__}: {cause}")
        self.path = path


@contextmanager
def reading(path: Path) -> Iterator[None]:
    """Name `path` in any failure raised while it is read."""

    try:
        yield
    except Unreadable:
        raise
    except Exception as exc:
        raise Unreadable(path, exc) from exc


def copy_of_product(start: Path) -> tuple[Path, str] | None:
    """The repository root and version of the copy of this product holding `start`."""

    for candidate in (start, *start.parents):
        manifest = candidate / PACKAGE_MANIFEST
        if not manifest.is_file():
            continue
        with reading(manifest), manifest.open("rb") as handle:
            package = tomllib.load(handle).get("package", {})
        if package.get("name") == PRODUCT and isinstance(package.get("version"), str):
            return candidate, package["version"]
        return None
    return None


def comparison(this: tuple[Path, str], other: tuple[Path, str]) -> str:
    """Which of two copies is behind: by version, and by SKILL.md at one version."""

    sys.path.insert(0, str(ROOT / "scripts"))
    from release_contract import calver_parts  # noqa: PLC0415

    (_, mine), (where, theirs) = this, other
    if mine != theirs:
        try:
            behind = calver_parts(mine) < calver_parts(theirs)
        except ValueError:
            return f"The copy at {where} is version {theirs}, and this copy is version {mine}."
        if behind:
            return f"This copy is version {mine}, behind the copy at {where}, which is {theirs}. Update this copy."
        return f"The copy at {where} is version {theirs}, behind this copy, which is {mine}."
    # Both copies share this copy's layout, so the suite sits at the same place.
    suite = ROOT.relative_to(this[0])
    skills = []
    for root in (this[0], where):
        path = root / suite / "SKILL.md"
        with reading(path):
            skills.append(hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest())
    if skills[0] != skills[1]:
        return (
            f"The copy at {where} is version {theirs}, the same as this copy, and its SKILL.md "
            "differs; one of the two carries unreleased edits."
        )
    return f"The copy at {where} is version {theirs}, the same as this copy, with the same SKILL.md."



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


def registry_roles(project: Path) -> dict[str, list[str]]:
    """The status of every record under each role the registry names."""

    registry = project / "asset-registry.md"
    if not registry.is_file():
        return {}
    sys.path.insert(0, str(ROOT / "scripts"))
    from asset_registry import is_placeholder, parse  # noqa: PLC0415

    by_role: dict[str, list[str]] = {}
    with reading(registry):
        records = parse(registry.read_text(encoding="utf-8"))
    for record in records:
        if is_placeholder(record):
            continue
        role = record["fields"].get("role")
        if role:
            by_role.setdefault(role, []).append(record["fields"].get("status", ""))
    return by_role


def unsettled_roles(project: Path, by_role: dict[str, list[str]] | None = None) -> list[str]:
    """Roles whose asset nobody has settled: no accepted member, or more than one."""

    return [
        f"{role}: {statuses.count('accepted')} accepted of {len(statuses)} records"
        for role, statuses in sorted((registry_roles(project) if by_role is None else by_role).items())
        if statuses.count("accepted") != 1
    ]


def open_task(project: Path) -> dict | None:
    """The open task, with a failure naming the file it came from."""

    sys.path.insert(0, str(ROOT / "scripts"))
    import work_ledger  # noqa: PLC0415

    with reading(work_ledger.work_dir(project) / work_ledger.CURRENT):
        return work_ledger.read_current(project)


def task_summary(project: Path) -> str:
    """What work_ledger shows first, once each file it reads has been read here."""

    sys.path.insert(0, str(ROOT / "scripts"))
    import work_ledger  # noqa: PLC0415

    if open_task(project) is None:
        with reading(work_ledger.work_dir(project) / work_ledger.LEDGER):
            work_ledger.read_ledger(project)
    return work_ledger.show(project)



def identity_sheet_action(project: Path, plots: list[dict], roles: dict[str, list[str]]) -> str | None:
    """The identity sheets a shared frame waits on, once any approved scene holds two characters.

    A frame that shows a recurring character beside another subject binds an
    image adopted for that character's `ID/identity` role, so those sheets come
    before the first shared frame is written.
    """

    waiting: list[str] = []
    for plot in plots:
        cast = [c for c in plot.get("characters") or [] if isinstance(c, str)]
        if len(cast) < 2:
            continue
        for character in cast:
            if roles.get(f"{character}/identity", []).count("accepted") != 1 and character not in waiting:
                waiting.append(character)
    if not waiting:
        return None
    draft = ROOT / "scripts" / "submission_draft.py"
    first = waiting[0]
    return (
        f"Make and adopt the identity sheet of {', '.join(waiting)} before a frame shows two of them: "
        f"{draft} new --project {project} --kind asset --out media/characters/{first}-sheet.submission.json "
        f"--target <target> --purpose sheet-panel --basis character-profiles.md --basis-locator {first} "
        f"--subject {first} recurring {first} drafts one, and the "
        f"author adopts one returned image per character for the role ID/identity "
        f"({ROOT / 'references' / 'model-facing-artifacts.md'} section 12)"
    )


def shot_record_actions(project: Path, plots: list[dict]) -> list[str]:
    """The first shot of an approved screen plot that has no camera, and the first with no request."""

    held: dict[str, set[tuple[str, str]]] = {"shot-camera-spec": set(), "shot-request": set()}
    shots = project / "shots"
    for path in sorted(shots.rglob("*.json")) if shots.is_dir() else []:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("artifact_type") in held:
            held[value["artifact_type"]].add((str(value.get("scene_id")), str(value.get("shot_id"))))
    units = [(str(plot.get("scene_id")), str(unit.get("id"))) for plot in plots
             if (plot.get("realization") or {}).get("kind") == "shots"
             for unit in (plot.get("realization") or {}).get("units") or [] if isinstance(unit, dict)]
    actions: list[str] = []
    camera = next((unit for unit in units if unit not in held["shot-camera-spec"]), None)
    if camera:
        scene, shot = camera
        actions.append(
            f"Place the camera for {scene} {shot}: fill "
            f"{ROOT / 'protocols' / 'viewpoint' / 'templates' / 'shot-camera-spec.template.json'} as "
            f"shots/{scene}/{shot}.camera.json with scene_id {scene!r} and shot_id {shot!r}, then "
            f"{ROOT / 'scripts' / 'viewpoint_protocol.py'} seal it"
        )
    request = next((unit for unit in units if unit in held["shot-camera-spec"]
                    and unit not in held["shot-request"]), None)
    if request:
        scene, shot = request
        actions.append(
            f"Write the shot request for {scene} {shot} as shots/{scene}/{shot}.request.json, with its "
            f"shot projection and a chain file naming the state inputs; "
            f"{ROOT / 'scripts' / 'shot_chain.py'} CHAIN --project {project} builds the state, "
            "binds and seals the shot's records and checks them complete"
        )
    return actions


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
        shown = "; ".join(report["errors"][:3])
        more = len(report["errors"]) - 3
        return [
            f"Answer the narrative's contract in {narrative_path}: {shown}"
            + (f" (and {more} more)" if more > 0 else "")
        ]

    blanks = json_placeholders(document)
    if not any(document.get(key) for key in ("themes", "characters", "arcs", "chapters")):
        # A fresh narrative is empty tables, not blanks, and there is nothing to approve yet.
        actions.append(
            f"Write what the series is about in {narrative_path}: its themes, characters, arcs and "
            f"chapters, in the shape {ROOT / 'protocols' / 'narrative' / 'README.md'} gives, then have "
            "the author approve it"
        )
    elif blanks:
        more = len(blanks) - 3
        actions.append(
            f"Settle what the series is about: {narrative_path} still carries what "
            f"initialization wrote at {', '.join(blanks[:3])}"
            + (f" and {more} more" if more > 0 else "")
        )
    elif not report["approved"]:
        reason = "; ".join(report["approval_errors"]) or "it carries no approved block"
        actions.append(
            f"Approve the narrative: {reason}. Once the author approves it, "
            f"{ROOT / 'scripts' / 'narrative.py'} approve {narrative_path} --by <name> records that."
        )

    index = scan(project)
    for message in index["errors"]:
        actions.append(f"Repair a reference: {message}")
    for target, sources in list(index["dangling"].items())[:3]:
        actions.append(
            f"Write the file for {target!r}, named by {', '.join(sources)}: "
            f"{entity} --project {project} add <kind> {target}"
        )

    coverage = cover(narrative_path, project / "narrative" / "scenes", series=project)
    # The index and the coverage report share their wording, so a finding both
    # make, such as a file that does not parse, is listed once.
    for message in coverage["errors"]:
        if message not in index["errors"]:
            actions.append(f"Resolve a contradiction: {message}")

    for chapter in coverage["chapters"]:
        if not chapter["scenes"]:
            actions.append(
                f"Plan a scene for chapter {chapter['id']} ({chapter['title']}), which is "
                f"{chapter['status']} and has none: "
                f"{ROOT / 'scripts' / 'scene_plot.py'} draft --project {project} "
                f"--scene-id <id> --chapter {chapter['id']} writes a plot to fill in"
            )
            break

    scenes = project / "narrative" / "scenes"
    approved: list[dict] = []
    if scenes.is_dir():
        waiting = None
        for path in sorted(scenes.glob("*.json")):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(value, dict) or value.get("artifact_type") != "scene-plot":
                continue
            plot = validate_scene_plot(value)
            if plot["ok"] and plot["approved"]:
                approved.append(value)
            elif plot["ok"] and waiting is None:
                waiting = path
        if waiting is not None:
            actions.append(
                f"Approve the scene plot {waiting.name} before any shot text exists. Once the "
                f"author approves it, {ROOT / 'scripts' / 'scene_plot.py'} approve {waiting} "
                f"--by <name> records that."
            )
    sheets = identity_sheet_action(project, approved, registry_roles(project))
    if sheets:
        actions.append(sheets)
    actions.extend(shot_record_actions(project, approved))

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
                f"Fill in the form as far as its use needs: {path.relative_to(project).as_posix()} "
                f"still carries {count} blank(s); {ROOT / 'references' / 'scene-persona.md'} says how "
                "much of a persona a scene needs"
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
    gaps = coverage["gaps"]
    # An unapproved narrative is the coverage report's first gap, and the
    # narrative's own action above already asks for its blanks or approval.
    if not report["approved"]:
        gaps = gaps[1:]
    for message in gaps[:3]:
        actions.append(f"Cover what the series declares: {message}")
    for role in unsettled_roles(project):
        actions.append(f"Settle the asset for {role}")
    return actions


def announce(arguments: argparse.Namespace) -> int:
    start = arguments.project or Path.cwd()
    if arguments.next:
        found = project_root(start.resolve())
        if found is None:
            print(
                "The working directory is not a project; "
                f"{ROOT / 'scripts' / 'init_project.py'} creates one."
            )
            return 1
        actions = next_actions(found)
        task = open_task(found)
        if task is not None:
            waiting = task.get("blocked_on")
            actions.insert(0, f"Continue the open task {task['task_id']} ({task['goal']}): "
                              + (f"it waits on: {waiting}" if waiting else f"{task.get('next')}"))
        print(chr(10).join(actions) if actions
              else "Nothing this command can read is unsettled.")
        return 0

    this = copy_of_product(ROOT)
    version = f"version {this[1]}" if this else "an undeclared version"
    first = f"Series Continuity Director, {version}, is installed at {ROOT}."
    if arguments.compare is not None:
        other = copy_of_product(arguments.compare.resolve())
        if this is None or other is None:
            print(f"{arguments.compare} holds no copy of {PRODUCT} with a declared version.")
            return 1
        print(comparison(this, other))
        return 0
    # A session opened inside another copy, such as the source checkout, learns
    # whether the copy the host reads is behind it. A manifest above the working
    # directory may belong to anything, so a failure here stays one sentence.
    try:
        other = copy_of_product(start.resolve())
        if this is not None and other is not None and other[0] != this[0]:
            first += " " + comparison(this, other)
    except Unreadable as exc:
        first += f" The copy holding the working directory was not compared: {exc}."

    # Every path this prints is absolute. The reader's working directory is the
    # project, not the suite, so a bare `scripts/...` names nothing it can open.
    project = project_root(start.resolve())
    if project is None:
        # Outside a project there is nothing to route.
        print(
            f"{first} The working directory is not a project of this suite; "
            f"{ROOT / 'scripts' / 'init_project.py'} creates one."
        )
        return 0

    lines = [first, f"Project workspace: {project}"]
    # Where the work stands comes before everything else: a session that lost
    # its context continues the open task from here, not from memory.
    lines.append(task_summary(project))
    roles = registry_roles(project)
    unsettled = unsettled_roles(project, roles)
    if unsettled:
        lines.append("Roles with no single accepted asset:")
        lines += [f"  {role}" for role in unsettled]
    elif roles:
        lines.append(f"Every role in the registry ({len(roles)}) has exactly one accepted asset.")
    else:
        lines.append("The asset registry names no role yet.")
    actions = next_actions(project)
    if actions:
        lines.append("")
        lines.append("Next, in the order the layers depend on each other:")
        lines += [f"  {index}. {action}" for index, action in enumerate(actions, 1)]

    skill = ROOT / "SKILL.md"
    with reading(skill):
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


def where_raised(exc: BaseException) -> str:
    """The file and line of the innermost frame, for a failure no reader named."""

    frames = traceback.extract_tb(exc.__traceback__)
    return f"{frames[-1].filename}:{frames[-1].lineno}" if frames else "an unknown place"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Announce the suite and its entry points.")
    parser.add_argument("--project", type=Path, default=None)
    parser.add_argument(
        "--next", action="store_true",
        help="Print only the next deterministic actions for the project, one per line.",
    )
    parser.add_argument(
        "--compare", type=Path, default=None, metavar="DIR",
        help="Print whether the copy of the suite holding DIR is behind this copy, or ahead of it.",
    )
    parser.add_argument(
        "--hook", action="store_true",
        help="Session hook mode: any failure prints one line naming the problem and the file, and exits 0.",
    )
    arguments = parser.parse_args(argv)
    # A path or a record can hold characters the console cannot encode; they
    # print escaped instead of ending the command.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")

    # The hook's output is what the session reads, so its one line goes to
    # standard output; a person at a console reads it on standard error.
    stream = sys.stdout if arguments.hook else sys.stderr
    try:
        return announce(arguments)
    except Unreadable as exc:
        print(" ".join(f"Series Continuity Director could not read {exc}".split()), file=stream)
        return 0 if arguments.hook else 1
    except Exception as exc:
        if not arguments.hook:
            raise
        message = f"Series Continuity Director stopped at {where_raised(exc)}: {type(exc).__name__}: {exc}"
        print(" ".join(message.split()), file=stream)
        return 0


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
