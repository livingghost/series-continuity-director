#!/usr/bin/env python3
"""Check that the narrative reader reaches the verdict each rule is for.

Each case takes a narrative that answers the contract, changes one thing in it,
and declares what has to come back. A case that declares an error names the
fragment the message has to carry, so a rule that stops firing is caught by the
case that was written for it rather than by a count that still adds up.

The contract is published in `protocols/narrative/README.md`, and every rule
it states has a case here, so a rule that stops firing is caught by the case
written for it rather than by a count that still adds up.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import narrative as narrative_module  # noqa: E402
from narrative import (  # noqa: E402
    content_sha256,
    content_sha256 as narrative_sha256,
    persona_in_force,
    validate_narrative,
)


def base() -> dict[str, Any]:
    """A narrative that answers the contract, for a case to change one thing in."""

    return {
        "artifact_type": "narrative",
        "series_id": "smoke",
        "timeline_id": "main",
        "medium": "screen",
        "themes": [{"id": "t1", "statement": "What a person owes the people who wait for them."}],
        "characters": [
            {
                "id": "C01",
                "name": "The first",
                "persona": "narrative/personas/c01.md",
                "prohibitions": [
                    {"kind": "surface", "surface": "never say this"},
                    {"kind": "judgement", "statement": "Does not explain himself while working."},
                ],
            },
            {"id": "C02", "name": "The second", "persona": "narrative/personas/c02.md"},
        ],
        "arcs": [{
            "id": "a1", "name": "The main arc", "type": "main", "status": "in-progress",
            "themes": ["t1"], "characters": ["C01", "C02"],
            "setup": "Two people share a room and not much else.",
            "rising": ["One of them is asked for something.", "The asking becomes a habit."],
            "climax": "The habit is refused.",
            "resolution": "What replaces it is chosen rather than fallen into.",
        }],
        "chapters": [
            {"id": "ch1", "number": 1, "title": "First", "status": "complete", "arcs": ["a1"],
             "depicts": ["The room before anything is asked for."],
             "story_order_start": 0, "story_order_end": 100},
            {"id": "ch2", "number": 2, "title": "Second", "status": "in-progress", "arcs": ["a1"],
             "depicts": ["The first refusal."],
             "story_order_start": 100, "story_order_end": 200},
        ],
        "promises": [{
            "id": "p1", "statement": "The debt is named out loud.", "status": "planted",
            "planted": "ch1", "arcs": ["a1"], "characters": ["C01"],
        }],
        "questions": [{
            "id": "q1", "statement": "Who asked first.", "status": "open",
            "introduced": "ch1", "arcs": ["a1"],
        }],
        "knowledge": [{
            "id": "k1", "fact": "The debt exists.", "known_by": ["C01", "audience"],
            "learned_in": "ch1",
        }],
    }


def approve(value: dict[str, Any]) -> dict[str, Any]:
    value["approved"] = {"by": "the case author", "at": "2026-09-11T00:00:00Z",
                         "content_sha256": content_sha256(value)}
    return value


def change(**edits: Any) -> dict[str, Any]:
    """The base narrative with top-level keys replaced."""

    value = base()
    value.update(copy.deepcopy(edits))
    return value


def character(index: int, **edits: Any) -> dict[str, Any]:
    value = base()
    value["characters"][index].update(copy.deepcopy(edits))
    return value


def promise(**edits: Any) -> dict[str, Any]:
    value = base()
    value["promises"][0].update(copy.deepcopy(edits))
    return value


def question(**edits: Any) -> dict[str, Any]:
    value = base()
    value["questions"][0].update(copy.deepcopy(edits))
    return value


def knowledge(**edits: Any) -> dict[str, Any]:
    value = base()
    value["knowledge"][0].update(copy.deepcopy(edits))
    return value


PHASES = [
    {"id": "before", "persona": "narrative/personas/c01.md", "from_chapter": "ch1"},
    {"id": "after", "persona": "narrative/personas/c01-after.md", "from_chapter": "ch2",
     "changed": "He stops answering on the first ask.", "held": "He still answers."},
]

CASES: list[dict[str, Any]] = [
    {"name": "an explicitly empty persona phase list",
     "value": character(0, phases=[]),
     "error": ".phases must be a non-empty array when it is present"},
    {"name": "persona phases supplied as text instead of an array",
     "value": character(0, phases="before"),
     "error": ".phases must be a non-empty array when it is present"},
    {"name": "the contract answered", "value": base(), "error": None},
    {"name": "an unknown key", "value": change(notes="something"),
     "error": "unknown keys"},
    {"name": "the narrative names a target", "value": change(target="some-model"),
     "error": "the interface is chosen much later"},
    {"name": "theme removed while an arc still references it", "value": change(themes=[]),
     "error": "arcs[0].themes[0] names something that does not exist"},
    {"name": "an arc naming a theme that does not exist",
     "value": change(arcs=[{**base()["arcs"][0], "themes": ["t9"]}]),
     "error": "arcs[0].themes[0] names something that does not exist"},
    {"name": "an arc without escalating development",
     "value": change(arcs=[{**base()["arcs"][0], "rising": []}]),
     "error": None},
    {"name": "a chapter number missing from the run",
     "value": change(chapters=[{**base()["chapters"][0], "number": 1},
                               {**base()["chapters"][1], "number": 3}]),
     "error": "chapter numbers must run from 1 without gaps"},
    {"name": "two chapters with the same number",
     "value": change(chapters=[{**base()["chapters"][0], "number": 1},
                               {**base()["chapters"][1], "number": 1}]),
     "error": "repeats 1"},
    {"name": "a chapter that says nothing it depicts",
     "value": change(chapters=[{**base()["chapters"][0], "depicts": []},
                               base()["chapters"][1]]),
     "error": "depicts must name what this chapter presents or holds"},
    {"name": "no timeline", "value": change(timeline_id=None),
     "error": "timeline_id must name the timeline these chapters are ordered on"},
    {"name": "a timeline id that is not an id", "value": change(timeline_id="the main one"),
     "error": "timeline_id must name the timeline these chapters are ordered on"},
    {"name": "a chapter that covers no story order",
     "value": change(chapters=[{key: item for key, item in base()["chapters"][0].items()
                                if key != "story_order_start"},
                               base()["chapters"][1]]),
     "error": "chapters[0].story_order_start must say which story order this chapter covers"},
    {"name": "a chapter that ends before it begins",
     "value": change(chapters=[{**base()["chapters"][0], "story_order_end": 0,
                                "story_order_start": 50},
                               base()["chapters"][1]]),
     "error": "ends at story order 0 and begins at 50"},
    {"name": "an act holding its chapters out of order",
     "value": change(acts=[{"id": "act1", "number": 1, "name": "The only act",
                            "does": "Holds both chapters.", "chapters": ["ch2", "ch1"]}]),
     "error": "acts[0].chapters are not in chapter order: [2, 1]"},
    {"name": "an act numbered from two",
     "value": change(acts=[{"id": "act1", "number": 2, "name": "The only act",
                            "does": "Holds both chapters.", "chapters": ["ch1", "ch2"]}]),
     "error": "act numbers must run from 1 without gaps"},
    {"name": "a chapter in no act while the series declares acts",
     "value": change(acts=[{"id": "act1", "number": 1, "name": "The only act",
                            "does": "Holds one chapter.", "chapters": ["ch1"]}]),
     "error": "the series declares acts and these chapters are in none: ['ch2']"},
    {"name": "acts that hold every chapter in order",
     "value": change(acts=[{"id": "act1", "number": 1, "name": "The only act",
                            "does": "Holds both chapters.", "chapters": ["ch1", "ch2"]}]),
     "error": None},
    {"name": "a relationship with somebody the series does not carry",
     "value": change(relationships=[{"id": "r1", "from": "C01", "to": "C09",
                                     "bond_type": "friendship", "at_start": "unclear"}]),
     "error": "names somebody the series does not carry: 'C09'"},
    {"name": "a relationship of no known bond",
     "value": change(relationships=[{"id": "r1", "from": "C01", "to": "C02",
                                     "bond_type": "acquaintance", "at_start": "unclear"}]),
     "error": None},
    {"name": "a relationship from somebody to themselves",
     "value": change(relationships=[{"id": "r1", "from": "C01", "to": "C01",
                                     "bond_type": "friendship", "at_start": "unclear"}]),
     "error": "is from C01 to themselves"},
    {"name": "a character arc that says what it wants and not what it needs",
     "value": change(arcs=[{**base()["arcs"][0], "type": "character", "want": "to be left alone"}]),
     "error": None},
    {"name": "a main arc that claims a want",
     "value": change(arcs=[{**base()["arcs"][0], "want": "to be left alone"}]),
     "error": None},
    {"name": "a series with no declared medium", "value": change(medium=None),
     "error": "medium must be one of"},
    {"name": "a character written out before they appear",
     "value": character(0, first_appears="ch2", written_out_in="ch1"),
     "error": "is written out in chapter 1 and first appears in chapter 2"},
    {"name": "a character written out of a chapter that does not exist",
     "value": character(0, written_out_in="ch9"),
     "error": "written_out_in names a chapter that does not exist"},
    {"name": "a character with a span", "value": character(0, first_appears="ch1",
                                                           written_out_in="ch2"),
     "error": None},
    {"name": "a promise paid off before it is planted",
     "value": promise(status="paid-off", planted="ch2", payoff="ch1"),
     "error": "before it is planted"},
    {"name": "a promise still planned that names a planted chapter",
     "value": promise(status="planned"),
     "error": "still planned and already names a planted chapter"},
    {"name": "a promise paid off with no payoff chapter",
     "value": promise(status="paid-off", payoff=None),
     "error": "names no chapter it was paid off in"},
    {"name": "a question resolved before it is introduced",
     "value": question(status="resolved", introduced="ch2", resolved="ch1"),
     "error": "before it is introduced"},
    {"name": "a question answered with no chapter that raised it",
     "value": question(status="answered", introduced=None, resolved="ch2"),
     "error": "names no chapter it was introduced in"},
    {"name": "a question still open that names a resolved chapter",
     "value": question(resolved="ch2"),
     "error": "still open and already names a resolved chapter"},
    {"name": "a fact known by someone who is not in the series",
     "value": knowledge(known_by=["C09"]),
     "error": "known_by[0] names something that does not exist"},
    {"name": "a fact learned in a chapter that does not exist",
     "value": knowledge(learned_in="ch9"),
     "error": "learned_in names a chapter that does not exist"},
    {"name": "a fact the audience holds", "value": knowledge(known_by=["audience"]),
     "error": None},
    {"name": "a surface prohibition carrying a statement",
     "value": character(0, prohibitions=[{"kind": "surface", "surface": "no",
                                          "statement": "also no"}]),
     "error": "statement does not belong to a surface prohibition"},
    {"name": "a judgement prohibition carrying a surface",
     "value": character(0, prohibitions=[{"kind": "judgement", "statement": "no",
                                          "surface": "also no"}]),
     "error": "surface does not belong to a judgement prohibition"},
    {"name": "a prohibition of neither kind",
     "value": character(0, prohibitions=[{"kind": "vibe", "statement": "no"}]),
     "error": "kind must be one of"},
    {"name": "a persona document outside the project",
     "value": character(0, persona="../elsewhere/c01.md"),
     "error": "must be a path inside the project"},
    {"name": "a character with no persona document",
     "value": character(0, persona=""),
     "error": "must name the persona document"},
    {"name": "phases in chapter order",
     "value": character(0, phases=copy.deepcopy(PHASES),
                        persona="narrative/personas/c01-after.md"),
     "error": None},
    {"name": "phases out of chapter order",
     "value": character(0,
                        phases=[{**copy.deepcopy(PHASES[0]), "from_chapter": "ch2"},
                                {**copy.deepcopy(PHASES[1]), "from_chapter": "ch1"}],
                        persona="narrative/personas/c01-after.md"),
     "error": "must run in chapter order"},
    {"name": "two phases beginning in the same chapter",
     "value": character(0,
                        phases=[copy.deepcopy(PHASES[0]),
                                {**copy.deepcopy(PHASES[1]), "from_chapter": "ch1"}],
                        persona="narrative/personas/c01-after.md"),
     "error": "begins two phases in the same chapter"},
    {"name": "the character's persona is not the last phase's",
     "value": character(0, phases=copy.deepcopy(PHASES)),
     "error": "must be the document of the last phase"},
    {"name": "a phase beginning in a chapter that does not exist",
     "value": character(0,
                        phases=[{**copy.deepcopy(PHASES[0]), "from_chapter": "ch9"},
                                copy.deepcopy(PHASES[1])],
                        persona="narrative/personas/c01-after.md"),
     "error": "from_chapter names a chapter that does not exist"},
    {"name": "a later phase that does not say what held",
     "value": character(0,
                        phases=[copy.deepcopy(PHASES[0]),
                                {k: v for k, v in PHASES[1].items() if k != "held"}],
                        persona="narrative/personas/c01-after.md"),
     "error": "phases[1].held must be a non-empty string"},
    {"name": "a first phase that says what changed",
     "value": character(0,
                        phases=[{**copy.deepcopy(PHASES[0]), "changed": "something"},
                                copy.deepcopy(PHASES[1])],
                        persona="narrative/personas/c01-after.md"),
     "error": "has no earlier phase to compare against"},
]

# A promise planted long enough ago with no payoff is reported and is not an
# error, because a series may hold one deliberately.
UNFIRED = base()
UNFIRED["chapters"] = [
    {"id": f"ch{index}", "number": index, "title": f"Chapter {index}", "status": "complete",
     "arcs": ["a1"], "depicts": [f"What chapter {index} shows."],
     "story_order_start": index * 100, "story_order_end": index * 100 + 99}
    for index in range(1, 6)
]



CONTAINERS: dict[str, dict[str, Any]] = {
    "themes": {"id": "tX", "statement": "Something else the series is about."},
    "characters": {"id": "CX", "name": "The third", "persona": "narrative/personas/cx.md"},
    "arcs": {"id": "aX", "name": "Another arc", "type": "subplot", "status": "planned",
             "themes": ["t1"], "characters": ["C01"], "setup": "s",
             "rising": ["r"], "climax": "c", "resolution": "r"},
    "chapters": {"id": "chX", "number": 3, "title": "Third", "status": "planned",
                 "arcs": ["a1"], "depicts": ["What chapter three shows."],
                 "story_order_start": 200, "story_order_end": 300},
    "acts": {"id": "actX", "number": 1, "name": "The only act", "does": "Holds every chapter.",
             "chapters": ["ch1", "ch2"]},
    "relationships": {"id": "rX", "from": "C01", "to": "C02", "bond_type": "working",
                      "at_start": "They work the same shift."},
    "promises": {"id": "pX", "statement": "Another debt.", "status": "planned", "arcs": ["a1"]},
    "questions": {"id": "qX", "statement": "Another question.", "status": "open",
                  "arcs": ["a1"]},
    "knowledge": {"id": "kX", "fact": "Another fact.", "known_by": ["audience"],
                  "learned_in": "ch1"},
}
# A container that already carries an entry in the base narrative, so a repeated
# id has something to repeat.
OCCUPIED = {"themes", "characters", "arcs", "promises", "questions", "knowledge"}


def with_container(name: str, entries: Any) -> dict[str, Any]:
    """The base narrative with one container replaced."""

    value = base()
    # A second character the relationship entries can point at.
    value["characters"] = value["characters"] + [
        {"id": "C03", "name": "The third", "persona": "narrative/personas/c03.md"}]
    value[name] = entries
    return value


def generated_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for name, entry in CONTAINERS.items():
        existing = base().get(name) or []
        if name == "characters":
            existing = []
        cases.append({
            "name": f"{name}: an entry that is not an object",
            "value": with_container(name, [*existing, "not an object"]),
            "error": f"{name}[{len(existing)}] must be an object",
        })
        cases.append({
            "name": f"{name}: an entry with no id",
            "value": with_container(name, [*existing,
                                           {k: v for k, v in entry.items() if k != "id"}]),
            "error": f"{name}[{len(existing)}].id must be a non-empty string",
        })
        cases.append({
            "name": f"{name}: an entry with an unknown key",
            "value": with_container(name, [*existing, {**entry, "notes": "something"}]),
            "error": "has unknown keys",
        })
        if name in OCCUPIED:
            # The base entries stay, so the rest of the narrative still refers to
            # things that exist and the case is about the repeat and nothing else.
            held = base().get(name) or []
            first = held[0] if held and isinstance(held[0], dict) else {}
            if first.get("id"):
                cases.append({
                    "name": f"{name}: two entries with one id",
                    "value": with_container(name, [*held, {**entry, "id": first["id"]}]),
                    "error": f"repeats {first['id']!r}",
                })
        cases.append({
            "name": f"{name}: not an array at all",
            "value": with_container(name, "not an array"),
            "error": f"{name} must be an array",
        })

    # Every closed list the narrative constrains.
    for container, field, wrong in (
        ("arcs", "status", "ongoing"),
        ("chapters", "status", "drafted"),
        ("promises", "status", "kept"),
        ("questions", "status", "asked"),
    ):
        existing = base().get(container) or []
        entry = {**CONTAINERS[container], field: wrong}
        cases.append({
            "name": f"{container}[].{field}: a word that is not one of the list",
            "value": with_container(container, [*existing, entry]),
            "error": f".{field} must be one of",
        })

    return cases


def chapter(index: int, **edits: Any) -> dict[str, Any]:
    value = base()
    value["chapters"][index].update(copy.deepcopy(edits))
    return value


def without(container: str, index: int, key: str) -> dict[str, Any]:
    value = base()
    value[container][index].pop(key, None)
    return value


ACT = {"id": "act1", "number": 1, "name": "The only act", "does": "Holds every chapter.",
       "chapters": ["ch1", "ch2"]}
BOND = {"id": "r1", "from": "C01", "to": "C02", "bond_type": "working",
        "at_start": "They work the same shift."}

# One question whose status is a misspelling and whose three other fields are
# wrong as well. The three cases below read this one document, each for a
# different refusal, so that the unknown word is shown not to hide the rest.
MISSPELLED_QUESTION_STATUS = question(status="opne", arcs=["no-such-arc"],
                                      introduced="no-such-chapter", resolved="also-missing")

# One case per refusal the reader can make that no other case names, so that
# deleting the refusal turns a case red. `notice` cases assert what the reader
# reports without refusing.
UNNAMED_CASES: list[dict[str, Any]] = [
    {"name": "a narrative that is not an object", "value": "not an object",
     "error": "narrative root must be an object"},
    {"name": "the wrong artifact type", "value": change(artifact_type="scene-plot"),
     "error": "artifact_type must be"},
    {"name": "a chapter that names no arcs at all", "value": without("chapters", 0, "arcs"),
     "error": "chapters[0].arcs is required"},
    {"name": "a chapter numbered zero", "value": chapter(0, number=0),
     "error": ".number must be a positive integer"},
    {"name": "two chapters with one number", "value": chapter(1, number=1),
     "error": ".number repeats 1"},
    {"name": "a chapter with no story order",
     "value": without("chapters", 0, "story_order_start"),
     "error": "must say which story order this chapter covers"},
    {"name": "a chapter with a negative story order", "value": chapter(0, story_order_start=-1),
     "error": "must be a story order, a non-negative integer"},
    {"name": "a chapter told out of order",
     "value": change(chapters=[
         {**base()["chapters"][0], "story_order_start": 200, "story_order_end": 300},
         {**base()["chapters"][1], "story_order_start": 100, "story_order_end": 150},
     ]),
     "notice": "it is told out of order"},
    {"name": "an act numbered zero", "value": change(acts=[{**ACT, "number": 0}]),
     "error": "acts[0].number must be a positive integer"},
    {"name": "two acts with one number",
     "value": change(acts=[{**ACT, "chapters": ["ch1"]},
                           {**ACT, "id": "act2", "chapters": ["ch2"]}]),
     "error": "acts[1].number repeats 1"},
    {"name": "an act that groups nothing", "value": change(acts=[{**ACT, "chapters": []}]),
     "error": ".chapters must name the chapters this act groups"},
    {"name": "a chapter held by two acts",
     "value": change(acts=[{**ACT, "chapters": ["ch1", "ch2"]},
                           {**ACT, "id": "act2", "number": 2, "chapters": ["ch1"]}]),
     "error": "which act act1 already holds"},
    {"name": "one relationship declared twice",
     "value": change(relationships=[BOND, {**BOND, "id": "r2"}]),
     "error": "repeats the relationship from C01 to C02"},
    {"name": "a relationship with no way back", "value": change(relationships=[BOND]),
     "notice": "and not the one from C02 to C01"},
    {"name": "a planted promise with no chapter", "value": promise(planted=None),
     "error": "and names no chapter it was planted in"},
    {"name": "a planned promise naming its payoff",
     "value": promise(status="planned", planted=None, payoff="ch2"),
     "error": "is still planned and already names a payoff chapter"},
    {"name": "an answered question with no answer", "value": question(status="answered"),
     "error": "and names no chapter it was answered in"},
    {"name": "a misspelled question status does not hide an arc that does not exist",
     "value": copy.deepcopy(MISSPELLED_QUESTION_STATUS),
     "error": "questions[0].arcs[0] names something that does not exist"},
    {"name": "a misspelled question status does not hide an introducing chapter that does not exist",
     "value": copy.deepcopy(MISSPELLED_QUESTION_STATUS),
     "error": "questions[0].introduced names a chapter that does not exist"},
    {"name": "a misspelled question status does not hide a resolving chapter that does not exist",
     "value": copy.deepcopy(MISSPELLED_QUESTION_STATUS),
     "error": "questions[0].resolved names a chapter that does not exist"},
    {"name": "prohibitions that are not a list", "value": character(0, prohibitions="never"),
     "error": ".prohibitions must be an array"},
    {"name": "two phases with one id",
     "value": character(0, phases=[PHASES[0], {**PHASES[1], "id": "before"}],
                        persona="narrative/personas/c01-after.md"),
     "error": ".phases[1].id repeats 'before'"},
    {"name": "a phase naming no persona",
     "value": character(0, phases=[{**PHASES[0], "persona": ""}], persona=""),
     "error": ".persona must name this phase's persona document"},
]


# The approval block, one case per way an approval can fail to hold.
NARRATIVE_APPROVAL_CASES: list[dict[str, Any]] = [
    {"name": "an approval that is not an object",
     "value": {**base(), "approved": "yesterday"},
     "approved": False, "error": "approved must be an object"},
    {"name": "an approval with an unknown key",
     "value": {**base(), "approved": {"by": "someone", "at": "2026-09-11T00:00:00Z",
                                      "content_sha256": "0" * 64, "scope": "all"}},
     "approved": False, "error": "approved has unknown keys"},
    {"name": "an approval that names nobody",
     "value": {**base(), "approved": {"by": "  ", "at": "2026-09-11T00:00:00Z",
                                      "content_sha256": "0" * 64}},
     "approved": False, "error": "approved.by must be a non-empty string"},
    {"name": "an approval with a loose time",
     "value": {**base(), "approved": {"by": "someone", "at": "yesterday",
                                      "content_sha256": "0" * 64}},
     "approved": False, "error": "must be an RFC3339 UTC timestamp"},
    {"name": "an approval with no content hash",
     "value": {**base(), "approved": {"by": "someone", "at": "2026-09-11T00:00:00Z"}},
     "approved": False, "error": "must be the sha256 of the narrative without its"},
]


# Shared neutral-format cases are also exported into narrative_corpus.json.
from narrative_test_support import minimal_narrative  # noqa: E402

CASES.extend([
    {"name": "neutral authoring workspace", "value": minimal_narrative(chapter=False), "error": None},
    {"name": "unpeopled work without explicit themes or arcs", "value": minimal_narrative(), "error": None},
    {"name": "one agent does not imply a relationship arc", "value": minimal_narrative(1), "error": None},
    {"name": "seventeen agents do not select a genre", "value": minimal_narrative(17), "error": None},
])
for _field in ("themes", "characters", "arcs", "chapters"):
    _missing = minimal_narrative(); _missing.pop(_field)
    CASES.append({"name": f"neutral shape still requires {_field} array", "value": _missing,
                  "error": f"{_field} must be an array"})
_thread = minimal_narrative()
_thread["arcs"] = [{"id": "a1", "name": "Cycle", "type": "main", "status": "resolved",
                    "themes": [], "characters": []}]
CASES.append({"name": "non-agent thread without mandatory climax", "value": _thread, "error": None})
_bad_stage = copy.deepcopy(_thread); _bad_stage["arcs"][0]["rising"] = [""]
CASES.append({"name": "a supplied development stage cannot be blank", "value": _bad_stage,
              "error": "rising[0] must be a non-empty string"})
_bad_stage_type = copy.deepcopy(_thread); _bad_stage_type["arcs"][0]["rising"] = "none"
CASES.append({"name": "supplied development stages must be an array", "value": _bad_stage_type,
              "error": "rising must be an array"})

# The public contract represents authored organization, not a compulsory plot.
_clockless = base()
_clockless['timeline_id'] = None
for _chapter in _clockless['chapters']:
    _chapter.pop('story_order_start'); _chapter.pop('story_order_end')
CASES.append({'name': 'chapter presentation without a story clock', 'value': _clockless, 'error': None})
CASES.append({'name': 'a freely named observational thread',
              'value': change(arcs=[{**base()['arcs'][0], 'type': 'observational-pattern'}]), 'error': None})
for _invalid_type in ('', None, [], {}):
    CASES.append({'name': 'arc type still needs text ' + repr(_invalid_type),
                  'value': change(arcs=[{**base()['arcs'][0], 'type': _invalid_type}]),
                  'error': '.type must be a non-empty string'})


from narrative_coverage import cover
from scene_plot import content_sha256 as plot_sha256

# What a scene becomes, per medium. A shot has a camera, a page has panels and an
# edge the reader turns, a passage is shown or told.
REALIZATIONS = {
    "shots": lambda scene_id: {"kind": "shots", "units": [
        {"id": f"{scene_id}-m01", "focal_beat": "b1",
         "shows": [{"statement": "the two of them", "from": ["b1"]}],
         "composition": [{"statement": "a wide, waist level", "from": ["b1"]}]},
    ]},
    "pages": lambda scene_id: {"kind": "pages", "units": [
        {"id": f"{scene_id}-p01", "focal_beat": "b1", "panels": 4,
         "shows": [{"statement": "the two of them", "from": ["b1"]}]},
    ]},
    "passages": lambda scene_id: {"kind": "passages", "units": [
        {"id": f"{scene_id}-s01", "focal_beat": "b1", "mode": "scene",
         "covers": [{"statement": "the two of them", "from": ["b1"]}]},
    ]},
}


def stamped(value: dict[str, Any], digest: str) -> dict[str, Any]:
    """One plot, written against the narrative it sits beside."""

    value = copy.deepcopy(value)
    signature = value.pop("approved", None)
    value["narrative_sha256"] = digest
    if signature is not None:
        signature["content_sha256"] = plot_sha256(value)
        value["approved"] = signature
    return value


def plot(scene_id: str, chapter: str, teaches: list[str] | None = None,
         role: str = "chapter_opening", function: str = "entry",
         cast: list[str] | None = None, order: int = 1,
         themes: list[str] | None = None, kind: str = "shots") -> dict[str, Any]:
    beat: dict[str, Any] = {"id": "b1", "beat": "The thing this scene is for happens.",
                            "visibility": "visible"}
    if teaches:
        beat["teaches"] = list(teaches)
    present = list(cast) if cast is not None else ["C01", "C02"]
    value = {
        "artifact_type": "scene-plot",
        "scene_id": scene_id,
        "narrative_sha256": "0" * 64,
        "order": order,
        "themes": list(themes) if themes is not None else ["t1"],
        "focalization": {"kind": "external"},
        "turn": {"value": "what the room holds", "from": "one of them",
                 "to": "both of them"},
        "chapter": chapter,
        "arcs": ["a1"],
        "characters": present,
        "setting": {"interior_exterior": "interior",
                    "location": "riverside-boathouse",
                    "where": "at the bench, the hatch behind him",
                    "time_of_day": "early, before either of them has spoken"},
        "scene_function": function,
        "delivery_role": role,
        "proposition": ("From a settled room, the thing this scene is for happens, "
                        "leaving the room changed."),
        "beats": [beat, {"id": "b2", "beat": "The rest of it goes on around them.",
                         "visibility": "context"}],
        "placement": [{"statement": "the two of them are in the room", "from": ["b1"]}],
        "must_preserve": [{"statement": "who is holding what", "from": ["b1"]}],
        "free": [{"statement": "the weather"}],
        "state_changes": [{"target": "the room", "change": "it is no longer shared the same way",
                           "from": ["b1"]}],
        # A scene with one person in it has nobody to change a relationship with.
        "relationship_delta": ([{"channel": "initiates-contact", "between": ["C01", "C02"],
                                 "change": "the first one speaks first now", "from": ["b1"]}]
                               if len(present) > 1 else []),
        "realization": REALIZATIONS[kind](scene_id),
    }
    value["approved"] = {"by": "the case author", "at": "2026-09-11T00:00:00Z",
                         "content_sha256": plot_sha256(value)}
    return value


def elsewhere(value: dict[str, Any]) -> dict[str, Any]:
    """A scene at a place nobody wrote a file for."""

    value = copy.deepcopy(value)
    signature = value.pop("approved")
    value["setting"] = {**value["setting"], "location": "a-place-nobody-wrote-down"}
    signature["content_sha256"] = plot_sha256(value)
    value["approved"] = signature
    return value


def with_context(value: dict[str, Any]) -> dict[str, Any]:
    """A scene that names a measured context nobody derived."""

    value = copy.deepcopy(value)
    signature = value.pop("approved")
    value["setting"] = {**value["setting"],
                        "scene_context": "state/scene-contexts/missing.json"}
    signature["content_sha256"] = plot_sha256(value)
    value["approved"] = signature
    return value


def stale(value: dict[str, Any]) -> dict[str, Any]:
    """A plot written against a narrative that has since been rewritten."""

    value = copy.deepcopy(value)
    signature = value.pop("approved", None)
    value["narrative_sha256"] = "f" * 64
    if signature is not None:
        signature["content_sha256"] = plot_sha256(value)
        value["approved"] = signature
    return value


def build(directory: Path, value: dict[str, Any], plots: list[dict[str, Any]]) -> Path:
    narrative_path = directory / "narrative" / "narrative.json"
    scenes = directory / "narrative" / "scenes"
    scenes.mkdir(parents=True, exist_ok=True)
    # The place every case's scenes happen at, so a case that is not about the
    # place does not report a missing one.
    places = directory / "narrative" / "world" / "locations"
    places.mkdir(parents=True, exist_ok=True)
    (places / "riverside-boathouse.md").write_text(
        "# The riverside boathouse" + chr(10) * 2 + "One bench, one window, one hatch." + chr(10),
        encoding="utf-8", newline="\n")
    for person in value.get("characters", []):
        if person.get("persona"):
            persona = directory / person["persona"]
            persona.parent.mkdir(parents=True, exist_ok=True)
            persona.write_text("# Test persona\n\nDetailed fixture, not a genre or performance default.\n", encoding="utf-8")
    narrative_path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8", newline="\n")
    # Every plot is written against the narrative in the same directory, so the
    # case does not have to carry a hash the narrative decides.
    digest = narrative_sha256(value)
    plots = [item if item.get("narrative_sha256") == "f" * 64 else stamped(item, digest)
             for item in plots]
    # Named by position, not by scene id, so that a case can put the same id in
    # two files and have the reader be the thing that catches it.
    for index, item in enumerate(plots):
        (scenes / f"plot-{index}.json").write_text(
            json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return narrative_path


def coverage_base() -> dict[str, Any]:
    """A narrative whose only gaps are the one each case introduces.

    The base narrative carries a complete chapter and a question left open
    behind the last one, both of which the report names. Those are their own
    cases; here they would land in every result and hide what is being tested.
    """

    value = base()
    value["chapters"][0]["status"] = "in-progress"
    value["questions"][0]["introduced"] = "ch2"
    return value


COVERAGE_CASES = [
    {
        "name": "every chapter covered",
        "narrative": approve(coverage_base()),
        "plots": [plot("s1", "ch1", teaches=["C01", "audience"]),
                  plot("s2", "ch2", role="chapter_closing", function="turn-trigger")],
        "errors": [],
        "gaps": [],
    },
    {
        "name": "a chapter no scene covers",
        "narrative": approve(coverage_base()),
        "plots": [plot("s1", "ch1", teaches=["C01", "audience"])],
        "errors": [],
        "gaps": ["chapter ch2 (in-progress) is declared and no scene covers it"],
    },
    {
        "name": "a scene naming a chapter the narrative does not carry",
        "narrative": approve(coverage_base()),
        "plots": [plot("s1", "ch1", teaches=["C01", "audience"]), plot("s2", "ch9")],
        "errors": ["which the narrative does not carry"],
        "gaps": ["chapter ch2 (in-progress) is declared and no scene covers it"],
    },
    {
        "name": "two scenes with the same id",
        "narrative": approve(coverage_base()),
        "plots": [plot("s1", "ch1", teaches=["C01", "audience"]),
                  {**plot("s2", "ch2"), "scene_id": "s1"}],
        "errors": ["is already used by"],
        "gaps": ["chapter ch2 (in-progress) is declared and no scene covers it"],
    },
    {
        "name": "a beat teaching someone who is not in the series",
        "narrative": approve(coverage_base()),
        "plots": [plot("s1", "ch1", teaches=["C09"]),
                  plot("s2", "ch2", role="chapter_closing")],
        "errors": ["neither a character in the narrative nor the audience"],
        "gaps": ["and no beat in that chapter's 1 scene(s) teaches C01",
                 "and no beat in that chapter's 1 scene(s) teaches audience"],
    },
    {
        "name": "a fact learned in a chapter where nothing teaches it",
        "narrative": approve(coverage_base()),
        "plots": [plot("s1", "ch1"), plot("s2", "ch2", role="chapter_closing")],
        "errors": [],
        "gaps": ["and no beat in that chapter's 1 scene(s) teaches C01",
                 "and no beat in that chapter's 1 scene(s) teaches audience"],
    },
    {
        "name": "a chapter with scenes that neither open nor close it",
        "narrative": approve(coverage_base()),
        "plots": [plot("s1", "ch1", teaches=["C01", "audience"]),
                  plot("s2", "ch2", role="interior_segment", function="build")],
        "errors": [],
        "gaps": ["chapter ch2 has 1 scene(s) and none of them opens or closes it"],
    },
    {
        "name": "a complete chapter may hold rather than turn",
        "narrative": approve(base()),
        "plots": [plot("s1", "ch1", teaches=["C01", "audience"]),
                  plot("s2", "ch2", role="chapter_closing", function="turn-trigger")],
        "errors": [],
        "gaps": ["questions[0] was introduced in chapter 1 and is still open at chapter 2"],
    },
    {
        "name": "a scene naming a character the narrative does not carry",
        "narrative": approve(coverage_base()),
        "plots": [plot("s1", "ch1", teaches=["C01", "audience"], cast=["C01", "C09", "C02"]),
                  plot("s2", "ch2", role="chapter_closing")],
        "errors": ["names character 'C09', which the narrative does not carry"],
        "gaps": [],
    },
    {
        "name": "a character who is in no scene",
        "narrative": approve(coverage_base()),
        "plots": [plot("s1", "ch1", teaches=["C01", "audience"], cast=["C01"]),
                  plot("s2", "ch2", role="chapter_closing", cast=["C01"])],
        "errors": [],
        "gaps": ["character C02 (The second) appears in no scene"],
    },
    {
        "name": "a scene happening somewhere no file describes",
        "narrative": approve(coverage_base()),
        "plots": [elsewhere(plot("s1", "ch1", teaches=["C01", "audience"])),
                  plot("s2", "ch2", role="chapter_closing")],
        "errors": [],
        "gaps": ["happens at 'a-place-nobody-wrote-down', and no file under "
                 "narrative/world/locations describes it"],
    },
    {
        "name": "a character in a scene after they were written out",
        "narrative": approve({**coverage_base(), "characters": [
            {**coverage_base()["characters"][0], "written_out_in": "ch1"},
            coverage_base()["characters"][1],
        ]}),
        "plots": [plot("s1", "ch1", teaches=["C01", "audience"]),
                  plot("s2", "ch2", role="chapter_closing")],
        "errors": ["C01 is in this scene, in chapter 2, and was written out in chapter 1"],
        "gaps": [],
    },
    {
        "name": "a character in a scene before they first appear",
        "narrative": approve({**coverage_base(), "characters": [
            coverage_base()["characters"][0],
            {**coverage_base()["characters"][1], "first_appears": "ch2"},
        ]}),
        "plots": [plot("s1", "ch1", teaches=["C01", "audience"]),
                  plot("s2", "ch2", role="chapter_closing")],
        "errors": ["C02 is in this scene, in chapter 1, and first appears in chapter 2"],
        "gaps": [],
    },
    {
        "name": "a scene naming a scene context that is not there",
        "narrative": approve(coverage_base()),
        "plots": [with_context(plot("s1", "ch1", teaches=["C01", "audience"])),
                  plot("s2", "ch2", role="chapter_closing")],
        "errors": ["names the scene context state/scene-contexts/missing.json, which does not exist"],
        "gaps": [],
    },
    {
        "name": "a scene written against an older narrative",
        "narrative": approve(coverage_base()),
        "plots": [stale(plot("s1", "ch1", teaches=["C01", "audience"])),
                  plot("s2", "ch2", role="chapter_closing")],
        "errors": ["scene_plot.py approve records that"],
        "gaps": [],
    },
    {
        "name": "two scenes claiming the same place in a chapter",
        "narrative": approve(coverage_base()),
        "plots": [plot("s1", "ch1", teaches=["C01", "audience"]),
                  plot("s1b", "ch1"), plot("s2", "ch2", role="chapter_closing")],
        "errors": ["chapter ch1 has 2 scenes claiming place 1 in it: "
                   "narrative/scenes/plot-0.json (s1), narrative/scenes/plot-1.json (s1b)"],
        "gaps": [],
    },
    {
        "name": "a chapter whose scenes start at two",
        "narrative": approve(coverage_base()),
        "plots": [plot("s1", "ch1", teaches=["C01", "audience"], order=2),
                  plot("s2", "ch2", role="chapter_closing")],
        "errors": ["chapter ch1 orders its scenes [2], which is not a run from 1"],
        "gaps": [],
    },
    {
        "name": "a scene carrying a theme the narrative does not carry",
        "narrative": approve(coverage_base()),
        "plots": [plot("s1", "ch1", teaches=["C01", "audience"], themes=["t9"]),
                  plot("s2", "ch2", role="chapter_closing")],
        "errors": ["carries theme 't9', which the narrative does not carry"],
        "gaps": [],
    },
    {
        "name": "a theme no scene carries",
        "narrative": approve({**coverage_base(), "themes": [
            coverage_base()["themes"][0],
            {"id": "t2", "statement": "What waiting costs the one who waits."},
        ]}),
        "plots": [plot("s1", "ch1", teaches=["C01", "audience"]),
                  plot("s2", "ch2", role="chapter_closing")],
        "errors": [],
        "gaps": ["theme t2 is declared and no scene carries it"],
    },
    {
        "name": "a prose series whose scene breaks into shots",
        "narrative": approve({**coverage_base(), "medium": "prose"}),
        "plots": [plot("s1", "ch1", teaches=["C01", "audience"]),
                  plot("s2", "ch2", role="chapter_closing")],
        "errors": ["breaks into 'shots' and the series is 'prose', which breaks into 'passages'"],
        "gaps": [],
    },
    {
        "name": "a prose series whose scenes break into passages",
        "narrative": approve({**coverage_base(), "medium": "prose"}),
        "plots": [plot("s1", "ch1", teaches=["C01", "audience"], kind="passages"),
                  plot("s2", "ch2", role="chapter_closing", kind="passages")],
        "errors": [],
        "gaps": [],
    },
    {
        # Three typos in one plot are three errors in one run, each beside the
        # declared id it most resembles.
        "name": "a scene with three id typos",
        "narrative": approve(coverage_base()),
        "plots": [{**plot("s1", "ch01", teaches=["C01", "audience"]), "arcs": ["a01"],
                   "characters": ["C01", "c02"]},
                  plot("s2", "ch2", role="chapter_closing")],
        "errors": ["names chapter 'ch01', which the narrative does not carry; did you mean 'ch1'?",
                   "names arc 'a01', which the narrative does not carry; did you mean 'a1'?",
                   "names character 'c02', which the narrative does not carry; did you mean 'C02'?"],
        "gaps": ["chapter ch1 (in-progress) is declared and no scene covers it"],
    },
    {
        # A plot that breaks its own contract still has its ids checked.
        "name": "an invalid scene with an unknown character",
        "narrative": approve(coverage_base()),
        "plots": [{**plot("s1", "ch1", teaches=["C01", "audience"], cast=["C01", "C09"]),
                   "proposition": ""},
                  plot("s2", "ch2", role="chapter_closing")],
        "errors": ["narrative/scenes/plot-0.json: proposition must be a non-empty string",
                   "narrative/scenes/plot-0.json: names character 'C09', which the narrative "
                   "does not carry"],
        "gaps": ["chapter ch1 (in-progress) is declared and no scene covers it"],
    },
    {
        "name": "an unapproved narrative",
        "narrative": coverage_base(),
        "plots": [plot("s1", "ch1", teaches=["C01", "audience"]),
                  plot("s2", "ch2", role="chapter_closing")],
        "errors": [],
        "gaps": ["nobody has signed off"],
    },
]



def run_command(*argv: Any) -> tuple[int, dict[str, Any]]:
    """One narrative command, through its parser, with its JSON report read back."""

    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = narrative_module.main([str(item) for item in argv])
    return code, json.loads(stream.getvalue())


def approval_checks(failures: list[str], results: list[dict[str, Any]]) -> None:
    """`narrative.py approve` records what the author approved, and refuses what it cannot."""

    with tempfile.TemporaryDirectory(prefix="narrative-approve-") as temporary:
        project = Path(temporary)
        path = build(project, base(), [])
        code, report = run_command("approve", path, "--by", "The author", "--at", "2026-09-23T09:00:00Z")
        written = json.loads(path.read_text(encoding="utf-8"))
        results.append({"case": "approve records the author's approval", "report": report})
        if code != 0 or not validate_narrative(written)["approved"]:
            failures.append(f"approve did not record an approval that holds: {report}")
        if written.get("approved", {}).get("content_sha256") != narrative_sha256(written):
            failures.append("approve recorded a hash other than the narrative's content hash")

        # A plot written against the version before it is listed as behind.
        (project / "narrative/scenes/plot.json").write_text(
            json.dumps(stale(plot("s1", "ch1"))), encoding="utf-8")
        code, report = run_command("approve", path, "--by", "The author")
        results.append({"case": "approve lists the plots behind", "report": report})
        if [item.get("plot") for item in report.get("plots_behind", [])] != ["narrative/scenes/plot.json"]:
            failures.append(f"approve did not list the plot behind the narrative: {report}")

        invalid = {**base(), "chapters": [], "medium": "film"}
        path.write_text(json.dumps(invalid), encoding="utf-8")
        before = path.read_bytes()
        code, report = run_command("approve", path, "--by", "", "--at", "yesterday")
        results.append({"case": "approve refuses every reason at once", "report": report})
        joined = "; ".join(report.get("errors", []))
        for fragment in ("--by must name who approved it", "--at must be an RFC3339 UTC time",
                         "medium must be one of"):
            if fragment not in joined:
                failures.append(f"approve refused without {fragment!r}: {joined}")
        if code == 0 or path.read_bytes() != before:
            failures.append("approve wrote a narrative it refused")

        code, report = run_command(project)
        results.append({"case": "a directory where the narrative goes", "report": report})
        if "expects the narrative file; did you mean" not in "; ".join(report.get("errors", [])) \
                or "narrative/narrative.json" not in "; ".join(report.get("errors", [])):
            failures.append(f"a directory argument was not explained: {report}")

    code, report = run_command("approve", ROOT / "examples" / "narrative.json", "--by", "The author")
    results.append({"case": "approve refuses the installed suite", "report": report})
    if code == 0 or "inside the installed suite" not in "; ".join(report.get("errors", [])):
        failures.append(f"approve wrote inside the installed suite: {report}")


def main() -> int:
    failures: list[str] = []
    results: list[dict[str, Any]] = []

    for case in CASES:
        report = validate_narrative(case["value"])
        joined = "; ".join(report["errors"])
        expected = case["error"]
        results.append({"case": case["name"], "ok": report["ok"], "errors": report["errors"]})
        if expected is None:
            if not report["ok"]:
                failures.append(f"{case['name']}: expected no error, got {joined}")
        elif expected not in joined:
            failures.append(f"{case['name']}: expected {expected!r}, got {joined or 'no error'}")

    for case in generated_cases():
        report = validate_narrative(case["value"])
        joined = "; ".join(report["errors"])
        results.append({"case": case["name"], "ok": report["ok"]})
        if case["error"] not in joined:
            failures.append(
                f"{case['name']}: expected {case['error']!r}, got {joined or 'no error'}"
            )

    for case in UNNAMED_CASES:
        report = validate_narrative(case["value"])
        joined = "; ".join(report["errors"])
        results.append({"case": case["name"], "ok": report["ok"], "errors": report["errors"],
                        "notices": report["notices"]})
        if "notice" in case:
            noticed = "; ".join(report["notices"])
            if not report["ok"]:
                failures.append(f"{case['name']}: expected no error, got {joined}")
            if case["notice"] not in noticed:
                failures.append(
                    f"{case['name']}: expected the notice {case['notice']!r}, got {noticed or 'none'}"
                )
        elif case["error"] not in joined:
            failures.append(
                f"{case['name']}: expected {case['error']!r}, got {joined or 'no error'}"
            )

    for case in NARRATIVE_APPROVAL_CASES:
        report = validate_narrative(case["value"])
        joined = "; ".join(report["approval_errors"])
        results.append({"case": f"narrative approval: {case['name']}",
                        "approved": report["approved"]})
        if case["error"] not in joined:
            failures.append(
                f"narrative approval: {case['name']}: expected {case['error']!r}, "
                f"got {joined or 'no error'}"
            )
        if report["approved"] != case["approved"]:
            failures.append(
                f"narrative approval: {case['name']}: expected approved={case['approved']}"
            )

    # A promise planted and unpaid for long enough is a notice, not an error.
    report = validate_narrative(UNFIRED)
    results.append({"case": "an unfired promise", "ok": report["ok"], "notices": report["notices"]})
    if not report["ok"]:
        failures.append(f"an unfired promise: expected no error, got {report['errors']}")
    if not any("still unpaid" in notice for notice in report["notices"]):
        failures.append(f"an unfired promise: expected a notice, got {report['notices']}")

    # An approval binds the content it was given, and nothing else.
    signed = approve(base())
    report = validate_narrative(signed)
    results.append({"case": "an approval that holds", "approved": report["approved"]})
    if not report["approved"]:
        failures.append(f"an approval that holds: {report['approval_errors']}")
    edited = copy.deepcopy(signed)
    edited["themes"][0]["statement"] = "Something else entirely."
    report = validate_narrative(edited)
    results.append({"case": "an approval after an edit", "approved": report["approved"]})
    if report["approved"]:
        failures.append("an approval after an edit: the approval still held")

    # Which persona describes a character during a given chapter.
    phased = character(0, phases=copy.deepcopy(PHASES), persona="narrative/personas/c01-after.md")
    numbers = validate_narrative(phased)["chapter_numbers"]
    for chapter_number, expected in ((1, "before"), (2, "after")):
        found, document = persona_in_force(phased["characters"][0], chapter_number, numbers)
        results.append({"case": f"the persona in force in chapter {chapter_number}",
                        "phase": found, "persona": document})
        if found != expected:
            failures.append(
                f"the persona in force in chapter {chapter_number}: expected {expected!r}, got {found!r}"
            )
    found, _ = persona_in_force(phased["characters"][1], 1, numbers)
    results.append({"case": "the persona of a character with no phases", "phase": found})
    if found is not None:
        failures.append(f"a character with no phases reported the phase {found!r}")
    late = copy.deepcopy(phased["characters"][0])
    late["phases"] = [{**copy.deepcopy(PHASES[1]), "from_chapter": "ch2"}]
    late["phases"][0].pop("changed", None)
    late["phases"][0].pop("held", None)
    found, document = persona_in_force(late, 1, numbers)
    results.append({"case": "a chapter before every declared phase", "persona": document})
    if document is not None:
        failures.append(f"a chapter before every phase named {document!r} rather than nothing")

    # An unknown id is reported beside the declared id closest to it.
    report = validate_narrative(change(chapters=[{**base()["chapters"][0], "arcs": ["a01"]},
                                                 base()["chapters"][1]]))
    results.append({"case": "an arc typo names the arc it resembles", "errors": report["errors"]})
    if not any("'a01'; did you mean 'a1'?" in message for message in report["errors"]):
        failures.append(f"an arc typo named no close match: {report['errors']}")

    approval_checks(failures, results)

    with tempfile.TemporaryDirectory() as temporary:
        for index, case in enumerate(COVERAGE_CASES):
            directory = Path(temporary) / f"case-{index}"
            path = build(directory, case["narrative"], case["plots"])
            report = cover(path, directory / "narrative" / "scenes", series=directory)
            results.append({"case": case["name"], "ok": report["ok"],
                            "errors": report["errors"], "gaps": report["gaps"]})
            joined_errors = "; ".join(report["errors"])
            joined_gaps = "; ".join(report["gaps"])
            for fragment in case["errors"]:
                if fragment not in joined_errors:
                    failures.append(
                        f"{case['name']}: expected the error {fragment!r}, got {joined_errors or 'none'}"
                    )
            if not case["errors"] and report["errors"]:
                failures.append(f"{case['name']}: expected no error, got {joined_errors}")
            for fragment in case["gaps"]:
                if fragment not in joined_gaps:
                    failures.append(
                        f"{case['name']}: expected the gap {fragment!r}, got {joined_gaps or 'none'}"
                    )
            if not case["gaps"] and report["gaps"]:
                failures.append(f"{case['name']}: expected no gap, got {joined_gaps}")

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
