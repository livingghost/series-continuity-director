#!/usr/bin/env python3
"""Report what a series declares against what its scenes cover.

Every other check in this suite reads one document. A narrative declares five
chapters and three arcs, a directory of scene plots covers some of them, and the
failure nobody notices is the one that leaves no trace in either file: a chapter
with no scene, an arc that no scene advances, a fact the narrative says a
character learned in a chapter where nothing teaches it.

This reads the narrative and every scene plot beside it and reports three
things.

- Contradictions, which are errors: a scene naming a chapter, an arc or a
  character the narrative does not carry, two scenes with the same id, a beat
  teaching someone who is not in the series, a relationship change between
  people the scene does not say are in it. Each plot is checked for all of them
  in one pass, and an unknown id is reported beside the declared id closest to it.
- Gaps, which are not errors: something declared and not yet covered. A series
  in progress has gaps by definition, and the point of the report is to name
  them rather than to refuse them.
- A table of what each chapter holds, in the units the series' medium breaks a
  scene into, so the shape of the series is readable without opening every file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from narrative import (  # noqa: E402
    AUDIENCE,
    content_sha256 as narrative_sha256,
    did_you_mean,
    persona_in_force,
    validate_narrative,
)
from narrative_index import SHIPPED, blank_gap, placeholder_details  # noqa: E402
from project_layout import read_document, shown  # noqa: E402
from scene_plot import REALIZATIONS, validate_scene_plot  # noqa: E402

# Delivery edges are diagnostic vocabulary, not a required dramatic pattern.
# A standalone short is already a complete delivery unit.
EDGE_ROLES = ("chapter_opening", "chapter_closing", "standalone_short")


def scene_paths(directory: Path) -> list[Path]:
    """Every JSON file under the scenes directory, in a stable order.

    An unreadable file is kept, so the report can say why it is not a plot.
    """

    if not directory.is_dir():
        return []
    return sorted(directory.rglob("*.json"))


def _known(value: Any, allowed: Any) -> bool:
    try:
        return value in allowed
    except TypeError:
        return False


def narrative_context(value: dict[str, Any], narrative_report: dict[str, Any],
                      series: Path | None) -> dict[str, Any]:
    """What a plot's references are checked against, read once from a valid narrative."""

    def by_id(key: str) -> dict[str, Any]:
        return {str(entry.get("id")): entry for entry in value.get(key) or []
                if isinstance(entry, dict)}

    characters = by_id("characters")
    return {
        "chapters": by_id("chapters"),
        "arcs": by_id("arcs"),
        "characters": characters,
        "themes": sorted(by_id("themes")),
        "knowers": sorted(characters) + [AUDIENCE],
        "medium": narrative_report["medium"],
        "realization": narrative_report["realization"],
        "numbers": narrative_report["chapter_numbers"],
        "spans": narrative_report["character_spans"],
        "series": series,
    }


def plot_contradictions(plot: dict[str, Any], plot_report: dict[str, Any],
                        context: dict[str, Any]) -> list[str]:
    """Everything one plot names that the narrative does not declare, in one pass.

    The checks are independent. A chapter nobody declared does not hide an arc,
    a theme or a character that is also wrong, so one run finds every typo.
    """

    found: list[str] = []
    chapters, arcs, characters = context["chapters"], context["arcs"], context["characters"]
    chapter = plot_report["chapter"]
    if chapter and chapter not in chapters:
        found.append(f"names chapter {chapter!r}, which the narrative does not carry"
                     f"{did_you_mean(chapter, chapters)}")
    for arc in plot_report["arcs"]:
        if isinstance(arc, str) and arc.strip() and not _known(arc, arcs):
            found.append(f"names arc {arc!r}, which the narrative does not carry"
                         f"{did_you_mean(arc, arcs)}")
    for theme in plot_report["themes"]:
        if theme.strip() and theme not in context["themes"]:
            found.append(f"carries theme {theme!r}, which the narrative does not carry"
                         f"{did_you_mean(theme, context['themes'])}")
    wanted = context["realization"]
    if wanted and plot_report["realization"] and plot_report["realization"] != wanted:
        found.append(
            f"breaks into {plot_report['realization']!r} and the series is "
            f"{context['medium']!r}, which breaks into {wanted!r}"
        )
    for beat in plot.get("beats") if isinstance(plot.get("beats"), list) else []:
        if not isinstance(beat, dict) or not isinstance(beat.get("teaches"), list):
            continue
        for who in beat["teaches"]:
            if isinstance(who, str) and who.strip() and who not in context["knowers"]:
                found.append(
                    f"beat {beat.get('id')!r} teaches {who!r}, who is neither a character in "
                    f"the narrative nor the audience{did_you_mean(who, context['knowers'])}"
                )
    numbers = context["numbers"]
    at = numbers.get(chapter) if isinstance(chapter, str) else None
    for who in plot_report["characters"]:
        if not who.strip():
            continue
        if who not in characters:
            found.append(f"names character {who!r}, which the narrative does not carry"
                         f"{did_you_mean(who, characters)}")
            continue
        if at is None:
            continue
        first, last = (context["spans"].get(who) or [None, None])[:2]
        if _known(first, numbers) and at < numbers[first]:
            found.append(f"{who} is in this scene, in chapter {at}, and first appears in "
                         f"chapter {numbers[first]}")
        if _known(last, numbers) and at > numbers[last]:
            found.append(f"{who} is in this scene, in chapter {at}, and was written out in "
                         f"chapter {numbers[last]}")
    series = context["series"]
    scene_context = plot_report["setting"].get("scene_context")
    if series is not None and scene_context and not (series / scene_context).is_file():
        found.append(f"names the scene context {scene_context}, which does not exist")
    return found


def cover(narrative_path: Path, scenes_directory: Path,
          series: Path | None = None) -> dict[str, Any]:
    """Compare one narrative against the scene plots that are supposed to cover it.

    `series` is the directory the paths inside those documents resolve from. It
    is what lets the report walk a join out of the narrative: a place named by a
    scene, a scene context named by a scene, a persona named by a character.
    Every path the report prints is POSIX and relative to it, which is the form
    `validate_project.py` and `narrative_index.py` print, so a report that merges
    theirs keeps one copy of a problem.
    """

    errors: list[str] = []
    gaps: list[str] = []
    report: dict[str, Any] = {
        "ok": False, "narrative": str(narrative_path), "scenes_directory": str(scenes_directory),
        "errors": errors, "gaps": gaps, "notices": [], "chapters": [], "scenes": 0,
        "realizations": [],
    }
    base = series if series is not None else scenes_directory.parent
    label = shown(narrative_path, base)

    value, problem = read_document(narrative_path, label)
    if problem:
        errors.append(problem)
        return report
    narrative_report = validate_narrative(value)
    if not narrative_report["ok"]:
        errors.extend(f"{label}: {message}" for message in narrative_report["errors"])
        return report
    report["notices"] = [f"{label}: {notice}" for notice in narrative_report["notices"]]
    if not narrative_report["approved"]:
        gaps.append(
            "the narrative is not approved, so everything below is measured against a document "
            "nobody has signed off"
        )

    current = narrative_sha256(value)
    context = narrative_context(value, narrative_report, series)
    # The columns the chapter table counts: the one kind the medium breaks a
    # scene into, or every kind for a mixed series.
    kinds = [narrative_report["realization"]] if narrative_report["realization"] else list(REALIZATIONS)
    report["realizations"] = kinds

    numbers: dict[str, int] = narrative_report["chapter_numbers"]
    chapters = context["chapters"]
    arcs = context["arcs"]
    characters = context["characters"]
    themes = context["themes"]

    # Read every scene once, check it whole, and count only the ones that can be.
    scenes: list[dict[str, Any]] = []
    seen_ids: dict[str, str] = {}
    for path in scene_paths(scenes_directory):
        where = shown(path, base)
        plot, problem = read_document(path, where)
        if problem:
            errors.append(problem)
            continue
        if not isinstance(plot, dict) or plot.get("artifact_type") != "scene-plot":
            continue
        plot_report = validate_scene_plot(plot)
        errors.extend(f"{where}: {message}" for message in plot_report["errors"])
        errors.extend(f"{where}: {message}"
                      for message in plot_contradictions(plot, plot_report, context))
        # Invariant: a change to the narrative invalidates what was approved
        # against the version before it. This is the check that makes that true.
        recorded = plot_report["narrative_sha256"]
        if recorded and recorded != current:
            errors.append(
                f"{where}: was written against narrative {recorded[:12]} and the narrative is now "
                f"{current[:12]}; once the author approves it against what the narrative now says, "
                "scene_plot.py approve records that, and scene_plot.py behind lists every such plot"
            )
        scene_id = plot_report["scene_id"]
        repeated = bool(scene_id) and scene_id in seen_ids
        if repeated:
            errors.append(f"{where}: scene_id {scene_id!r} is already used by {seen_ids[scene_id]}")
        elif scene_id:
            seen_ids[scene_id] = where
        chapter = plot_report["chapter"]
        if not plot_report["ok"] or repeated or chapter not in chapters:
            continue

        taught: dict[str, list[str]] = {}
        for beat in plot.get("beats") or []:
            if not isinstance(beat, dict):
                continue
            for who in beat.get("teaches") or []:
                if who in context["knowers"]:
                    taught.setdefault(str(who), []).append(str(beat.get("beat") or ""))
        scenes.append({
            "file": where,
            "scene_id": scene_id,
            "order": plot_report["order"],
            "themes": list(plot_report["themes"]),
            "focalization": plot_report["focalization"].get("kind", ""),
            "setting": plot_report["setting"],
            "chapter": chapter,
            "arcs": list(plot_report["arcs"]),
            "scene_function": plot.get("scene_function"),
            "delivery_role": plot.get("delivery_role"),
            "realization": plot_report["realization"],
            "units": plot_report["units"],
            "approved": plot_report["approved"],
            "teaches": taught,
            "characters": sorted(who for who in plot_report["characters"] if who in characters),
            "state_changes": plot_report["state_changes"],
        })
    report["scenes"] = len(scenes)

    # A place named by a scene and by no file is a place whose facts live in
    # whichever scene was written first.
    if series is not None:
        places = series / "narrative" / "world" / "locations"
        # Markdown only, and the whole tree, which is what the entity index
        # reads, kept as {id: the file it is in} so a gap names a file that exists.
        known = ({path.stem: path.relative_to(series).as_posix()
                  for path in sorted(places.rglob("*.md")) if path.name not in SHIPPED}
                 if places.is_dir() else {})
        for scene in scenes:
            location = scene["setting"].get("location")
            if location and location not in known:
                gaps.append(
                    f"{scene['file']}: happens at {location!r}, and no file under "
                    "narrative/world/locations describes it"
                )
        for location, where in sorted(known.items()):
            if not any(item["setting"].get("location") == location for item in scenes):
                gaps.append(f"{where}: no scene happens there")

    # A chapter the narrative declares and no scene covers. This is the whole
    # reason the report exists: the chapter list and the scenes directory are two
    # independent statements about the same series, and no single-document check
    # can compare them.
    by_chapter: dict[str, list[dict[str, Any]]] = {key: [] for key in chapters}
    for scene in scenes:
        by_chapter[scene["chapter"]].append(scene)

    # Read each selected persona once. A valid pointer string is not a written
    # or complete persona; fingerprints are review evidence, not approvals.
    persona_files: dict[str, dict[str, Any]] = {}

    def persona_file(pointer: str, who: str) -> dict[str, Any]:
        if pointer in persona_files:
            return persona_files[pointer]
        status: dict[str, Any] = {"file_sha256": None, "unfilled_count": None}
        persona_files[pointer] = status
        path = series / pointer
        if not path.is_file():
            # Worded as the index words it, so a report merging both keeps one.
            gaps.append(f"{label}: {who} names the persona document {pointer}, which nobody "
                        "has written")
            return status
        try:
            data = path.read_bytes()
            details = placeholder_details(data.decode("utf-8"))
        except (OSError, UnicodeError) as exc:
            errors.append(f"persona {pointer}: could not read the selected persona: {exc}")
            return status
        status.update(file_sha256=hashlib.sha256(data).hexdigest(), unfilled_count=len(details))
        if details:
            # Worded as the index words it, so a report merging both keeps one.
            gaps.append(blank_gap(shown(path, series), details))
        return status

    for chapter_id, chapter in sorted(chapters.items(), key=lambda item: numbers.get(item[0], 0)):
        held = by_chapter.get(chapter_id) or []
        functions = sorted({str(scene["scene_function"]) for scene in held})
        roles = sorted({str(scene["delivery_role"]) for scene in held})
        phases: dict[str, Any] = {}
        for character_id, character in characters.items():
            phase_id, document = persona_in_force(character, numbers.get(chapter_id, 0), numbers)
            phases[character_id] = {"phase": phase_id, "persona": document}
            if series is not None and document is not None:
                who = f"characters[{character_id}]" + (f".phases[{phase_id}]" if phase_id else "")
                phases[character_id].update(persona_file(document, who))
            if document is None:
                gaps.append(
                    f"chapter {chapter_id}: {character_id} has no persona document in force here; "
                    "every declared phase begins later"
                )
        report["chapters"].append({
            "id": chapter_id,
            "number": numbers.get(chapter_id),
            "story_order": [chapter.get("story_order_start"), chapter.get("story_order_end")],
            "focalization": sorted({scene["focalization"] for scene in held
                                    if scene["focalization"]}),
            "places": sorted({str(scene["setting"].get("location")) for scene in held
                              if scene["setting"].get("location")}),
            "title": chapter.get("title"),
            "status": chapter.get("status"),
            "arcs": list(chapter.get("arcs") or []),
            "scenes": [scene["scene_id"] for scene in held],
            "units": {kind: sum(scene["units"] for scene in held if scene["realization"] == kind)
                      for kind in kinds},
            "scene_functions": functions,
            "delivery_roles": roles,
            "unapproved_scenes": [scene["scene_id"] for scene in held if not scene["approved"]],
            "personas": phases,
        })
        if not held:
            gaps.append(
                f"chapter {chapter_id} ({chapter.get('status')}) is declared and no scene covers it"
            )
            continue
        if not any(role in EDGE_ROLES for role in roles):
            gaps.append(
                f"chapter {chapter_id} has {len(held)} scene(s) and none of them opens or closes it"
            )
    # A chapter's scenes come in an order, and the order is a run from 1. Two
    # scenes on one place are named, so the reader knows which files to open.
    for chapter_id, held in sorted(by_chapter.items()):
        places: dict[int, list[dict[str, Any]]] = {}
        for scene in held:
            places.setdefault(scene["order"], []).append(scene)
        clashes = {order: claimants for order, claimants in places.items() if len(claimants) > 1}
        for order, claimants in sorted(clashes.items()):
            named = ", ".join(f"{scene['file']} ({scene['scene_id']})" for scene in claimants)
            errors.append(
                f"chapter {chapter_id} has {len(claimants)} scenes claiming place {order} in it: "
                f"{named}"
            )
        orders = sorted(places)
        if not clashes and orders and orders != list(range(1, len(orders) + 1)):
            errors.append(
                f"chapter {chapter_id} orders its scenes {orders}, which is not a run from 1"
            )

    # A theme declared at the top and carried by no scene is the failure this
    # whole layer exists to catch.
    carried: set[str] = set()
    for scene in scenes:
        carried.update(scene["themes"])
    for theme in themes:
        if theme not in carried and scenes:
            gaps.append(f"theme {theme} is declared and no scene carries it")

    # An arc the narrative declares and no scene advances.
    advanced = {arc for scene in scenes for arc in scene["arcs"] if isinstance(arc, str)}
    for arc_id, arc in arcs.items():
        if arc_id not in advanced:
            gaps.append(
                f"arc {arc_id} ({arc.get('status')}) is declared and no scene advances it"
            )

    # The narrative says a fact was learned in a chapter. A scene in that chapter
    # has to be where it is learned, or the chapter order rests on nothing.
    for index, entry in enumerate(value.get("knowledge") or []):
        if not isinstance(entry, dict):
            continue
        learned = entry.get("learned_in")
        if learned is None:
            gaps.append(
                f"knowledge[{index}] names no chapter it was learned in, so nothing can cover it"
            )
            continue
        held = by_chapter.get(str(learned)) or []
        if not held:
            continue
        for who in entry.get("known_by") or []:
            if not any(str(who) in scene["teaches"] for scene in held):
                gaps.append(
                    f"knowledge[{index}] says {who} learns this in chapter {learned}, and no "
                    f"beat in that chapter's {len(held)} scene(s) teaches {who}"
                )

    # A character the series declares and no scene uses.
    used: set[str] = set()
    for scene in scenes:
        used.update(scene["characters"])
    for character_id, character in characters.items():
        if character_id not in used and scenes:
            gaps.append(
                f"character {character_id} ({character.get('name')}) appears in no scene"
            )

    # A promise or a question the narrative opened and the chapters ran past.
    for index, promise in enumerate(value.get("promises") or []):
        if isinstance(promise, dict) and promise.get("status") == "planned":
            gaps.append(f"promises[{index}] is planned and not yet planted in any chapter")
    last = max(numbers.values()) if numbers else 0
    for index, question in enumerate(value.get("questions") or []):
        if not isinstance(question, dict) or question.get("status") != "open":
            continue
        introduced = question.get("introduced")
        if introduced in numbers and numbers[introduced] < last:
            gaps.append(
                f"questions[{index}] was introduced in chapter {numbers[introduced]} and is "
                f"still open at chapter {last}"
            )

    report["ok"] = not errors
    return report


def render(report: dict[str, Any]) -> str:
    """The same report as lines, for reading rather than for a machine.

    The count columns are the units the series' medium has: shots for screen,
    pages for comics, passages for prose, and all three for a mixed series.
    """

    kinds = report.get("realizations") or []
    out: list[str] = []
    out.append(f"scenes: {report['scenes']}   chapters: {len(report['chapters'])}")
    out.append("")
    counts = " ".join(f"{kind:>{max(len(kind), 5)}}" for kind in kinds)
    header = f"{'ch':<6} {'#':>2} {'story order':<13} {'status':<12} {'scenes':>6} {counts}  places"
    out.append(header)
    out.append("-" * len(header))
    for chapter in report["chapters"]:
        first, last = chapter["story_order"]
        span = f"{first} to {last}" if first is not None else "-"
        places = ",".join(chapter["places"]) or "-"
        numbers = " ".join(f"{chapter['units'].get(kind, 0):>{max(len(kind), 5)}}" for kind in kinds)
        out.append(
            f"{chapter['id']:<6} {chapter['number'] or '':>2} {span:<13} "
            f"{str(chapter['status']):<12} {len(chapter['scenes']):>6} {numbers}  {places}"
        )
        functions = ",".join(chapter["scene_functions"]) or "-"
        roles = ",".join(chapter["delivery_roles"]) or "-"
        blank = " ".join(f"{'':>{max(len(kind), 5)}}" for kind in kinds)
        out.append(f"{'':<6} {'':>2} {'':<13} {'':<12} {'':>6} {blank}  {functions} / {roles}")
    for label, key in (("errors", "errors"), ("gaps", "gaps"), ("notices", "notices")):
        items = report.get(key) or []
        out.append("")
        out.append(f"{label}: {len(items)}")
        for message in items:
            out.append(f"  {message}")
    return "\n".join(out)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report what a series declares against what its scenes cover.")
    parser.add_argument("series", type=Path, help="The series directory, or the narrative itself")
    parser.add_argument("--scenes", type=Path, default=None,
                        help="Where the scene plots are, when they are not in narrative/scenes")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON")
    parser.add_argument("--strict", action="store_true",
                        help="Exit non-zero when anything is declared and not covered")
    args = parser.parse_args(argv)

    if args.series.is_dir():
        narrative_path = args.series / "narrative" / "narrative.json"
        scenes = args.scenes or (args.series / "narrative" / "scenes")
    else:
        narrative_path = args.series
        scenes = args.scenes or (narrative_path.parent / "scenes")

    # A series directory is the one holding `narrative/`, so a narrative inside
    # one sits two levels down from it. A narrative named anywhere else is still
    # a narrative and simply has no series to walk out of. The path is made
    # absolute and not resolved: a bare file name has to become one before it
    # has a parent to read, and following a link through `narrative/` to
    # wherever it really stores its files answered the store's name instead.
    absolute = narrative_path.absolute()
    if args.series.is_dir():
        series = args.series
    elif absolute.parent.name == "narrative":
        series = absolute.parent.parent
    else:
        series = None
    report = cover(narrative_path, scenes, series=series)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render(report))
    if not report["ok"]:
        return 1
    return 1 if args.strict and report["gaps"] else 0


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
