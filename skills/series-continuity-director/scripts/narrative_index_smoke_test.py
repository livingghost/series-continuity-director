#!/usr/bin/env python3
"""Check that the index and the entity commands reach the verdict each rule is for.

Each case builds a project in a temporary directory, changes one thing, and
names the message that has to come back. The commands are exercised the way a
session runs them, through their argument parsers, because an option that stops
parsing is a command nobody can run.
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import narrative_entity  # noqa: E402
from narrative import content_sha256 as narrative_sha  # noqa: E402
from narrative_index import scan  # noqa: E402
from scene_plot import content_sha256 as plot_sha  # noqa: E402

NL = chr(10)


def narrative(**edits: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_type": "narrative",
        "series_id": "index-smoke",
        "timeline_id": "main",
        "medium": "screen",
        "themes": [{"id": "t1", "statement": "What a person keeps back is what nobody reaches."}],
        "characters": [{"id": "C01", "name": "The subject",
                        "persona": "narrative/personas/c01.md"}],
        "arcs": [{"id": "a1", "name": "The arc", "type": "main", "status": "in-progress",
                  "themes": ["t1"], "characters": ["C01"],
                  "setup": "He is alone and it suits him.",
                  "rising": ["Someone waits."], "climax": "He speaks.",
                  "resolution": "The room is shared on other terms."}],
        "chapters": [{"id": "ch1", "number": 1, "title": "The first morning",
                      "status": "in-progress", "arcs": ["a1"],
                      "depicts": ["The boathouse before anyone speaks."],
                      "story_order_start": 0, "story_order_end": 100}],
        "promises": [], "questions": [], "knowledge": [],
    }
    value.update(edits)
    value["approved"] = {"by": "the case author", "at": "2026-09-11T00:00:00Z",
                         "content_sha256": narrative_sha(value)}
    return value


def scene(location: str = "the-boathouse") -> dict[str, Any]:
    value = {
        "artifact_type": "scene-plot", "scene_id": "sc01", "chapter": "ch1", "arcs": ["a1"],
        "narrative_sha256": "0" * 64, "order": 1, "themes": ["t1"],
        "characters": ["C01"],
        "focalization": {"kind": "external"},
        "turn": {"value": "the second lantern", "from": "unlit", "to": "burning on the bench"},
        "setting": {"interior_exterior": "interior", "location": location,
                    "where": "at the bench", "time_of_day": "early morning"},
        "scene_function": "entry", "delivery_role": "chapter_opening",
        "proposition": ("From an empty boathouse, he lights for two without saying so, leaving "
                        "the second lantern as the only thing that admits it."),
        "beats": [{"id": "b1", "beat": "He lights a second lantern on the bench.", "visibility": "visible"}],
        "placement": [{"statement": "he stands at the bench", "from": ["b1"]}],
        "must_preserve": [{"statement": "the leather apron", "from": ["b1"]}],
        "free": [{"statement": "the far wall"}],
        "state_changes": [{"target": "the second lantern", "change": "it is lit", "from": ["b1"]}],
        "relationship_delta": [],
        "realization": {"kind": "shots", "units": [
            {"id": "sc01-m01", "focal_beat": "b1",
             "shows": [{"statement": "two eggs in the pan", "from": ["b1"]}],
             "composition": [{"statement": "from the doorway", "from": ["b1"]}]},
        ]},
    }
    value["approved"] = {"by": "the case author", "at": "2026-09-11T00:00:00Z",
                         "content_sha256": plot_sha(value)}
    return value


def entity_file(path: Path, kind: str, identifier: str, *body: str,
                references: str = "references: []") -> None:
    """One entity file written by hand, in whatever form the case is about.

    The commands write one shape. The reader accepts more than one, and the
    cases below are about the forms it accepts and a command has to accept
    with it, so those have to be written rather than generated.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        NL.join(["---", f"kind: {kind}", f"id: {identifier}", f"name: The {identifier}",
                 references, "---", "", f"# The {identifier}", "", *body, ""]),
        encoding="utf-8", newline=NL)


def approved_scene(**edits: Any) -> dict[str, Any]:
    """A scene plot whose approval covers what it says after the edits."""

    value = scene()
    value.pop("approved")
    value.update(edits)
    value["approved"] = {"by": "the case author", "at": "2026-09-11T00:00:00Z",
                         "content_sha256": plot_sha(value)}
    return value


def build(root: Path, *, document: dict[str, Any] | None = None,
          plot: dict[str, Any] | None = None) -> Path:
    """A project holding a narrative and one scene, with no entity files yet."""

    for relative in ("narrative/personas", "narrative/world/locations", "narrative/world/factions",
                     "narrative/world/systems", "narrative/world/artifacts", "narrative/glossary",
                     "narrative/scenes", "narrative/design"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    (root / "narrative/narrative.json").write_text(
        json.dumps(document if document is not None else narrative(), ensure_ascii=False, indent=2)
        + NL, encoding="utf-8", newline=NL)
    (root / "narrative/scenes/sc01-plot.json").write_text(
        json.dumps(plot if plot is not None else scene(), ensure_ascii=False, indent=2) + NL,
        encoding="utf-8", newline=NL)
    return root


def run(*argv: str) -> tuple[int, dict[str, Any]]:
    """One entity command, through its parser, with its report read back."""

    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = narrative_entity.main(list(argv))
    return code, json.loads(stream.getvalue())


def main() -> int:
    failures: list[str] = []
    results: list[dict[str, Any]] = []

    def expect(name: str, found: list[str], fragment: str | None) -> None:
        joined = "; ".join(found)
        results.append({"case": name, "messages": found})
        if fragment is None:
            if found:
                failures.append(f"{name}: expected nothing, got {joined}")
        elif not any(fragment in item for item in found):
            failures.append(f"{name}: expected {fragment!r}, got {joined or 'nothing'}")

    with tempfile.TemporaryDirectory(prefix="narrative-index-") as temporary:
        base = Path(temporary)

        # A project whose files the commands created answers every rule.
        settled = build(base / "settled")
        run("--series", str(settled), "add", "location", "the-boathouse", "--name", "The boathouse")
        run("--series", str(settled), "add", "persona", "c01", "--character", "C01")
        report = scan(settled)
        expect("a project the commands built", report["errors"], None)
        # Everything the commands write is a blank until somebody fills it, and that
        # is what a fresh series has to report: a file that validates while saying
        # nothing is the one kind of missing content nothing notices.
        expect("a project the commands built, gaps", report["gaps"],
               "blank(s) nobody has filled")

        # A place a scene names and no file describes.
        missing = build(base / "missing")
        run("--series", str(missing), "add", "persona", "c01", "--character", "C01")
        expect("a place nothing describes", scan(missing)["errors"],
               "'the-boathouse' is named by narrative/scenes/sc01-plot.json")

        # A file nothing names.
        orphan = build(base / "orphan")
        run("--series", str(orphan), "add", "location", "the-boathouse")
        run("--series", str(orphan), "add", "persona", "c01", "--character", "C01")
        run("--series", str(orphan), "add", "faction", "the-committee")
        expect("a file nothing names", scan(orphan)["gaps"],
               "nothing in the series names 'the-committee'")

        # Front matter that disagrees with the file it is in.
        renamed = build(base / "renamed")
        run("--series", str(renamed), "add", "location", "the-boathouse")
        run("--series", str(renamed), "add", "persona", "c01", "--character", "C01")
        path = renamed / "narrative/world/locations/the-boathouse.md"
        path.rename(path.with_name("the-galley.md"))
        expect("a file renamed by hand", scan(renamed)["errors"],
               "front matter id is 'the-boathouse' and the file is named 'the-galley'")

        # A file in the wrong directory.
        misplaced = build(base / "misplaced")
        run("--series", str(misplaced), "add", "location", "the-boathouse")
        run("--series", str(misplaced), "add", "persona", "c01", "--character", "C01")
        path = misplaced / "narrative/world/locations/the-boathouse.md"
        path.rename(misplaced / "narrative/world/factions/the-boathouse.md")
        expect("a file in the wrong directory", scan(misplaced)["errors"],
               "front matter says kind 'location' and the file sits where a 'faction' goes")

        # A persona whose front matter names another character.
        wrong = build(base / "wrong")
        run("--series", str(wrong), "add", "location", "the-boathouse")
        run("--series", str(wrong), "add", "persona", "c01", "--character", "C09")
        expect("a persona the narrative points at for somebody else", scan(wrong)["errors"],
               "front matter says character")

        # Renaming reaches the scene that happens there, and drops its approval.
        moving = build(base / "moving")
        run("--series", str(moving), "add", "location", "the-boathouse")
        run("--series", str(moving), "add", "persona", "c01", "--character", "C01")
        code, report = run("--series", str(moving), "rename", "the-boathouse", "the-galley")
        results.append({"case": "rename", "report": report})
        if code != 0 or not report.get("ok"):
            failures.append(f"rename: {report}")
        if not any("sc01-plot.json (approval dropped)" in item
                   for item in report.get("rewritten") or []):
            failures.append(f"rename: the scene was not rewritten: {report.get('rewritten')}")
        plot = json.loads((moving / "narrative/scenes/sc01-plot.json").read_text(encoding="utf-8"))
        if plot["setting"]["location"] != "the-galley":
            failures.append("rename: the scene still happens at the old id")
        if "approved" in plot:
            failures.append("rename: the scene kept an approval covering the old id")
        expect("after a rename", scan(moving)["errors"], None)

        # Removing something still named is refused.
        code, report = run("--series", str(moving), "remove", "the-galley")
        results.append({"case": "remove while named", "report": report})
        if code == 0 or report.get("ok"):
            failures.append("remove: a place a scene happens at was removed anyway")
        code, report = run("--series", str(moving), "remove", "the-galley", "--force")
        results.append({"case": "remove with force", "report": report})
        if code != 0 or not report.get("ok"):
            failures.append(f"remove --force: {report}")

        # A persona needs to say whose life it describes.
        code, report = run("--series", str(settled), "add", "persona", "c02")
        results.append({"case": "a persona with no character", "report": report})
        if code == 0:
            failures.append("add persona: a persona was created without a character")

        # An id is an id.
        code, report = run("--series", str(settled), "add", "term", "not an id")
        results.append({"case": "an id that is not an id", "report": report})
        if code == 0:
            failures.append("add: a name with spaces was accepted as an id")

        # A persona is created from the form the project holds, not from the headings.
        formed = build(base / "formed")
        (formed / "narrative/personas/persona-template.md").write_text(
            "---" + NL + "title: form" + NL + "---" + NL + NL + "## 0. META" + NL,
            encoding="utf-8", newline=NL)
        run("--series", str(formed), "add", "persona", "c01", "--character", "C01")
        written = (formed / "narrative/personas/c01.md").read_text(encoding="utf-8")
        results.append({"case": "a persona from the project's form",
                        "carries_the_form": "## 0. META" in written})
        if "## 0. META" not in written or "kind: persona" not in written:
            failures.append("add persona: the project's form was not used")

        # An id sits in the file's own front matter, in the references other
        # files declare, and in every scene plot that happens there. A rename
        # reaches all of them or it is worse than none, and none of the three
        # is written in only one place or in only one form: the reader strips
        # a line before reading it and strips one layer of quotes off the
        # value, and it walks the whole tree.
        deep = build(base / "deep")
        run("--series", str(deep), "add", "persona", "c01", "--character", "C01")
        run("--series", str(deep), "add", "location", "the-boathouse", "--name", "The boathouse")
        place = deep / "narrative/world/locations/the-boathouse.md"
        place.write_text(
            place.read_text(encoding="utf-8").replace("id: the-boathouse", 'id: "the-boathouse"'),
            encoding="utf-8", newline=NL)
        entity_file(deep / "narrative/world/artifacts/east/the-kettle.md", "artifact",
                    "the-kettle", references="  references: [the-boathouse]")
        buried = deep / "narrative/scenes/ch1/sc02-plot.json"
        buried.parent.mkdir(parents=True, exist_ok=True)
        buried.write_text(
            json.dumps(approved_scene(scene_id="sc02", order=2), ensure_ascii=False, indent=2)
            + NL, encoding="utf-8", newline=NL)
        expect("a tree the reader reads before a rename", scan(deep)["errors"], None)

        code, report = run("--series", str(deep), "rename", "the-boathouse", "the-galley")
        results.append({"case": "a rename across a tree", "report": report})
        if code != 0 or not report.get("ok"):
            failures.append(f"rename across a tree: {report}")
        # The whole rule at once: after a rename nothing under narrative/ still
        # says the old id. A rename that says ok and leaves one is the failure
        # the command exists to prevent.
        left = sorted(str(path.relative_to(deep)).replace("\\", "/")
                      for path in (deep / "narrative").rglob("*")
                      if path.is_file() and "the-boathouse" in path.read_text(encoding="utf-8"))
        results.append({"case": "nothing still names the old id", "files": left})
        if left:
            failures.append("a rename reported ok and left the old id in " + ", ".join(left))
        expect("the index agrees after a rename across a tree", scan(deep)["errors"], None)

        after = scan(deep)
        results.append({"case": "the renamed file carries the new id",
                        "registered": sorted(after["entities"])})
        if "the-galley" not in after["entities"]:
            failures.append(
                "a rename left the front matter id behind, so the file it renamed is registered "
                f"by nothing: {sorted(after['entities'])}")
        named_by = after["named"].get("the-galley") or []
        results.append({"case": "a reference below the top of a directory moved",
                        "named_by": named_by})
        if not any("artifacts/east/the-kettle.md" in item for item in named_by):
            failures.append(f"a rename missed a reference in a subdirectory: {named_by}")
        moved = json.loads(buried.read_text(encoding="utf-8"))
        results.append({"case": "a scene plot below the top of scenes/ moved",
                        "location": moved["setting"]["location"],
                        "approved": "approved" in moved})
        if moved["setting"]["location"] != "the-galley":
            failures.append("a rename missed a scene plot in a subdirectory")
        if "approved" in moved:
            failures.append("a rewritten scene plot kept an approval covering the old id")

        # A file below the top of its directory is a file the index registers,
        # so it is one the commands have to reach. A command that cannot see it
        # cannot rename it, cannot remove it, and writes a second file claiming
        # the same id.
        below = build(base / "below")
        run("--series", str(below), "add", "persona", "c01", "--character", "C01")
        run("--series", str(below), "add", "location", "the-boathouse")
        entity_file(below / "narrative/world/locations/east/the-annex.md", "location",
                    "the-annex")
        expect("an entity below the top of its directory", scan(below)["errors"], None)
        if "the-annex" not in scan(below)["entities"]:
            failures.append("the index did not register an entity in a subdirectory")
        code, report = run("--series", str(below), "add", "location", "the-annex")
        results.append({"case": "add refuses an id a subdirectory already holds", "report": report})
        if code == 0 or report.get("ok"):
            failures.append("add wrote a second file for an id a subdirectory already held")
        code, report = run("--series", str(below), "rename", "the-annex", "the-back-room")
        results.append({"case": "rename reaches a subdirectory", "report": report})
        if code != 0 or not report.get("ok"):
            failures.append(f"rename could not reach an entity in a subdirectory: {report}")
        elif not (below / "narrative/world/locations/east/the-back-room.md").is_file():
            failures.append("a renamed entity did not stay where it was written")
        code, report = run("--series", str(below), "remove", "the-back-room")
        results.append({"case": "remove reaches a subdirectory", "report": report})
        if code != 0 or not report.get("ok"):
            failures.append(f"remove could not reach an entity in a subdirectory: {report}")

        # Every path this report prints is a path somebody can open. The walk
        # reaches the whole tree, so naming the kind's directory and the file's
        # own name spells a path nothing sits at, and spells the same one twice
        # when two files collide.
        twice = build(base / "twice")
        run("--series", str(twice), "add", "persona", "c01", "--character", "C01")
        run("--series", str(twice), "add", "location", "the-boathouse")
        entity_file(twice / "narrative/world/locations/north/the-depot.md", "location",
                    "the-depot")
        entity_file(twice / "narrative/world/locations/south/the-depot.md", "location",
                    "the-depot")
        report = scan(twice)
        printed = sorted({found for message in report["errors"] + report["gaps"]
                          for found in re.findall(r"narrative/[A-Za-z0-9_./-]+\.md", message)})
        unopenable = [item for item in printed if not (twice / item).is_file()]
        results.append({"case": "every path the report prints exists",
                        "printed": printed, "unopenable": unopenable})
        if not printed:
            failures.append("two files claiming one id produced no report naming either")
        if unopenable:
            failures.append("the report named paths nothing sits at: " + ", ".join(unopenable))
        collisions = [message for message in report["errors"] if "is already used by" in message]
        results.append({"case": "a duplicate id names the other file", "messages": collisions})
        if not collisions:
            failures.append("two files claiming one id were not reported")
        for message in collisions:
            here, _, rest = message.partition(":")
            other = rest.partition("is already used by ")[2].strip()
            if here.strip() == other:
                failures.append("a duplicate id was reported against itself: " + message)

        # A blank is a decision nobody has made. A file that shows one of those
        # words as an example is showing it, not leaving it, and counting both
        # made the report say the same thing about a file somebody wrote and a
        # file nobody has started.
        shown = build(base / "shown")
        run("--series", str(shown), "add", "persona", "c01", "--character", "C01")
        entity_file(
            shown / "narrative/world/locations/the-boathouse.md", "location", "the-boathouse",
            "A place is written `name: [name]` until somebody fills it in:",
            "", "```", "name: [name]", "```", "",
            "<!-- {name} reads as the character's, not this room's -->", "",
            "It is the room he cooks in, and the second plate is left on the counter.")
        left_blank = shown / "narrative/world/locations/the-larder.md"
        left_blank.parent.mkdir(parents=True, exist_ok=True)
        left_blank.write_text(
            NL.join(["---", "kind: location", "id: the-larder", "name: [name]",
                     "references: []", "---", "", "# [name]", "", "undecided", ""]),
            encoding="utf-8", newline=NL)
        report = scan(shown)
        quoted_gaps = [gap for gap in report["gaps"]
                       if "the-boathouse.md" in gap and "blank(s)" in gap]
        real_gaps = [gap for gap in report["gaps"]
                     if "the-larder.md" in gap and "blank(s)" in gap]
        results.append({"case": "a token a file shows is not a blank", "gaps": quoted_gaps})
        if quoted_gaps:
            failures.append("a written file was reported as unfilled: " + "; ".join(quoted_gaps))
        results.append({"case": "a token standing where a decision goes is a blank",
                        "gaps": real_gaps})
        if not real_gaps:
            failures.append("a file left exactly as the blank form was reported as filled")

        # The narrative's own blanks. It is data rather than prose, so a blank
        # in it is a whole string value and not a line, and the walk over the
        # entity files cannot reach it.
        unsettled = build(base / "unsettled",
                          document=narrative(themes=[{"id": "t1", "statement": "undecided"}]))
        run("--series", str(unsettled), "add", "location", "the-boathouse")
        run("--series", str(unsettled), "add", "persona", "c01", "--character", "C01")
        told = [gap for gap in scan(unsettled)["gaps"]
                if "narrative/narrative.json" in gap and "blank(s)" in gap]
        results.append({"case": "the narrative's own blanks are reported", "gaps": told})
        if not told:
            failures.append("the narrative carries what initialization wrote and nothing said so")
        elif not any("themes[0].statement" in gap for gap in told):
            failures.append("the report does not say which decision is missing: " + "; ".join(told))
        expect("a narrative nobody left a blank in reports none",
               [gap for gap in scan(settled)["gaps"]
                if "narrative/narrative.json" in gap and "blank(s)" in gap], None)

        # `references` holds several ids and is written as a list. A string is
        # iterable, so a value that is not one was read one character at a time
        # and reported as that many names with nothing behind them.
        loose = build(base / "loose")
        run("--series", str(loose), "add", "persona", "c01", "--character", "C01")
        run("--series", str(loose), "add", "location", "the-boathouse")
        entity_file(loose / "narrative/world/artifacts/the-kettle.md", "artifact", "the-kettle",
                    references="references: the-boathouse")
        report = scan(loose)
        expect("a references value that is not a list", report["errors"], "is a list")
        letters = [message for message in report["errors"] if re.match(r"^'.' is named by", message)]
        results.append({"case": "an unbracketed id is not one id per letter", "messages": letters})
        if letters:
            failures.append("a references string was read one character at a time: "
                            + "; ".join(letters))

    print(json.dumps({
        "ok": not failures,
        "checks": len(results),
        "results": results,
        "errors": failures,
    }, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
