#!/usr/bin/env python3
"""Validate source approvals, literal contracts, media inputs and request constraints.

The author or delegated reviewer assesses meaning against the recorded requirements.
`submission_draft.py` writes a submission skeleton that this gate then checks.
See examples/submission-gate for synthetic requests and observed reports.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import traceback
from collections.abc import Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILES = ROOT / "protocols" / "target" / "profiles"

RULES = {
    'ROUTE_READING_INVALID': 'SUB-17', 'VISUAL_CONTINUITY_INVALID': 'SUB-18',
    'LOCK_SURFACE_ABSENT': 'SUB-01', 'LOCK_SURFACE_GLUED': 'SUB-02', 'INPUT_MODE_CONFLICT': 'SUB-07',
    'INPUT_MODE_LIMIT': 'SUB-07',
    'IDENTITY_REFERENCE_TOO_SMALL': 'SUB-08', 'SUBMISSION_KIND_UNDECLARED': 'SUB-15',
    'SCENE_PLOT_MISSING': 'SUB-15', 'SCENE_PLOT_OUTSIDE_ROOT': 'SUB-15', 'SCENE_PLOT_INVALID': 'SUB-15',
    'SCENE_PLOT_UNAPPROVED': 'SUB-15', 'SCENE_PLOT_EDITED_AFTER_APPROVAL': 'SUB-15',
    'SCENE_ID_MISMATCH': 'SUB-15', 'UNIT_NOT_IN_SCENE_PLOT': 'SUB-15', 'CHARACTER_NOT_IN_SCENE': 'SUB-15',
    'FIELD_OF_ANOTHER_KIND': 'SUB-15', 'SCENE_PLOT_BEHIND_NARRATIVE': 'SUB-15',
    'NARRATIVE_OUTSIDE_ROOT': 'SUB-16', 'NARRATIVE_INVALID': 'SUB-16', 'CHARACTER_NOT_IN_NARRATIVE': 'SUB-16',
    'PROHIBITED_SURFACE': 'SUB-16', 'DURATION_NOT_INTEGER': 'SUB-09', 'DURATION_OUT_OF_BAND': 'SUB-09',
    'SCHEMA_REFUSAL': 'SUB-10',
}
# A submission carrying no text at all, or a placeholder nobody filled, fails
# before any numbered rule applies, so it carries no id rather than an empty
# one: a reader of `rule` gets a rule or nothing, and never a third thing that
# has to be told apart from both.
UNNUMBERED = frozenset({"TEXT_MISSING", "PLACEHOLDER_UNFILLED"})

# What a submission is. A scene-linked kind depicts one unit of the realization
# its approved scene plot declares, and names that unit in its own field. An
# asset belongs to no scene: a reference, a sheet panel, a plate or a probe.
SCENE_KINDS = {
    "shot": {"realization": "shots", "unit": "shot_id"},
    "page": {"realization": "pages", "unit": "page_id"},
    "passage": {"realization": "passages", "unit": "passage_id"},
}
KINDS = (*SCENE_KINDS, "asset")
# A page submission may narrow itself to one panel of that page.
SCENE_FIELDS = ("scene_plot", "scene_id", "shot_id", "page_id", "panel", "passage_id")

# The fields the gate refuses a submission without. `scripts/README.md` lists
# the same table, and submission_gate_smoke_test.py compares the two.
REQUIRED_EVERY_KIND = ("kind", "text", "route_reading", "visual_continuity",
                       "visual_continuity_sha256")
REQUIRED_BY_KIND = {
    "shot": ("scene_plot", "scene_id", "shot_id"),
    "page": ("scene_plot", "scene_id", "page_id"),
    "passage": ("scene_plot", "scene_id", "passage_id"),
    "asset": (),
}
# Every top-level field the gate reads. The optional ones are read when present,
# and an absent one is reported as unmeasured where a rule needed it.
FIELDS = (
    "submission_id", "kind", "target", "service", "text", "text_form", "negative_text",
    "dialogue", "inputs", "parameters", "obligations", "output_kind", "narrative",
    "characters", *SCENE_FIELDS, "route_reading", "visual_continuity",
    "visual_continuity_sha256",
)
# The code that refuses each required field when it is absent.
MISSING_CODES = {
    "kind": "SUBMISSION_KIND_UNDECLARED",
    "text": "TEXT_MISSING",
    "route_reading": "ROUTE_READING_INVALID",
    "visual_continuity": "VISUAL_CONTINUITY_INVALID",
    "visual_continuity_sha256": "VISUAL_CONTINUITY_INVALID",
    "scene_plot": "SCENE_PLOT_MISSING",
    "scene_id": "SCENE_ID_MISMATCH",
    "shot_id": "UNIT_NOT_IN_SCENE_PLOT",
    "page_id": "UNIT_NOT_IN_SCENE_PLOT",
    "passage_id": "UNIT_NOT_IN_SCENE_PLOT",
}
# What each required field carries, and the command that writes it where one does.
MISSING_HELP = {
    "kind": (
        "shot, page or passage for a submission that depicts part of a scene plot, asset for a "
        "reference, a sheet panel, a plate or a probe"
    ),
    "text": "the model-facing text",
    "route_reading": (
        "the record of reading the media route; read it with scripts/execution_routes.py "
        "read media --root PROJECT, then attach it with scripts/submission_draft.py reading"
    ),
    "visual_continuity": "the visual continuity block; write it with scripts/visual_continuity.py build",
    "visual_continuity_sha256": (
        "the hash of the visual continuity block; scripts/visual_continuity.py build writes it"
    ),
    "scene_plot": "the project-relative path of the approved scene plot",
    "scene_id": "the id of the scene the plot covers",
    "shot_id": "the shot of the scene plot this submission depicts",
    "page_id": "the page of the scene plot this submission depicts",
    "passage_id": "the passage of the scene plot this submission illustrates",
}

# A draft marks every field its author still has to decide with this key, and
# the gate refuses the submission until none is left.
PLACEHOLDER = "placeholder"


def placeholder(asks: str) -> dict[str, str]:
    """A value nobody has decided yet, saying what it asks for."""

    return {PLACEHOLDER: asks}


def placeholders(value: Any, path: str = "") -> list[tuple[str, str]]:
    """Every placeholder in a document, by the path of the field that holds it."""

    if isinstance(value, dict):
        if set(value) == {PLACEHOLDER}:
            return [(path or "the submission", str(value[PLACEHOLDER]))]
        found: list[tuple[str, str]] = []
        for key, item in value.items():
            found += placeholders(item, f"{path}.{key}" if path else str(key))
        return found
    if isinstance(value, list):
        found = []
        for index, item in enumerate(value):
            found += placeholders(item, f"{path}[{index}]")
        return found
    return []


def submission_bytes(value: dict[str, Any]) -> bytes:
    """A submission document as the draft and the block builders write it."""

    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def absent(value: Any) -> bool:
    """A field that is not there, is null, or holds only whitespace."""

    return value is None or (isinstance(value, str) and not value.strip())


def required_fields(kind: Any) -> tuple[str, ...]:
    """The fields a submission of this kind must carry."""

    return REQUIRED_EVERY_KIND + REQUIRED_BY_KIND.get(kind, ()) if isinstance(kind, str) else REQUIRED_EVERY_KIND


def missing(field: str, detail: str = "") -> dict[str, Any]:
    """The refusal for one required field that is absent."""

    message = f"missing required field {field!r}: {MISSING_HELP[field]}"
    return finding(MISSING_CODES[field], message + (f"; {detail}" if detail else ""), field=field)


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    if code not in RULES and code not in UNNUMBERED:
        raise KeyError(f"{code} implements no rule in references/prompt-composition.md section 18")
    item: dict[str, Any] = {"code": code, "severity": "error", "message": message}
    if code in RULES:
        item["rule"] = RULES[code]
    item.update(extra)
    return item


def shape(value: Any) -> str:
    """What a refusal calls a value that arrived in the wrong shape.

    A submission is a JSON document somebody wrote, so a line about it is
    written in the words of that document -- a number, a list, a piece of text
    -- and not in the name of the Python object the parser happened to build.
    `type(value).__name__` is the wrong thing twice over: `int` and `str` are
    not words the writer used, and no article agrees with them, so the gate
    says `a int`. The article is part of the answer here, which is why it is
    returned with the noun rather than written at each call site.
    """

    if value is None:
        return "nothing"
    if isinstance(value, bool):
        return "a true/false"
    if isinstance(value, (int, float)):
        return "a number"
    if isinstance(value, str):
        return "a piece of text"
    if isinstance(value, list):
        return "a list"
    if isinstance(value, dict):
        return "a block of named fields"
    return "something JSON does not write"


def png_size(data: bytes) -> tuple[int, int] | None:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def jpeg_size(data: bytes) -> tuple[int, int] | None:
    if data[:2] != b"\xff\xd8":
        return None
    offset = 2
    while offset + 9 < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            offset += 2
            continue
        length = int.from_bytes(data[offset + 2:offset + 4], "big")
        # The start-of-frame markers carry the dimensions. DHP and EXP share the
        # 0xC4, 0xC8, 0xCC range's shape but are not frames.
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height = int.from_bytes(data[offset + 5:offset + 7], "big")
            width = int.from_bytes(data[offset + 7:offset + 9], "big")
            return width, height
        offset += 2 + length
    return None


def gif_size(data: bytes) -> tuple[int, int] | None:
    if data[:6] not in (b"GIF87a", b"GIF89a") or len(data) < 10:
        return None
    return int.from_bytes(data[6:8], "little"), int.from_bytes(data[8:10], "little")


def bmp_size(data: bytes) -> tuple[int, int] | None:
    if data[:2] != b"BM" or len(data) < 26:
        return None
    header = int.from_bytes(data[14:18], "little")
    if header == 12:
        return int.from_bytes(data[18:20], "little"), int.from_bytes(data[20:22], "little")
    if header >= 40:
        # A negative height means the rows are stored top down. The picture is
        # the same size either way.
        return (
            abs(int.from_bytes(data[18:22], "little", signed=True)),
            abs(int.from_bytes(data[22:26], "little", signed=True)),
        )
    return None


def webp_size(data: bytes) -> tuple[int, int] | None:
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP" or len(data) < 30:
        return None
    chunk = data[12:16]
    if chunk == b"VP8X":
        return (
            int.from_bytes(data[24:27], "little") + 1,
            int.from_bytes(data[27:30], "little") + 1,
        )
    if chunk == b"VP8 ":
        if data[23:26] != b"\x9d\x01\x2a":
            return None
        return (
            int.from_bytes(data[26:28], "little") & 0x3FFF,
            int.from_bytes(data[28:30], "little") & 0x3FFF,
        )
    if chunk == b"VP8L":
        if data[20] != 0x2F:
            return None
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


def tiff_size(data: bytes) -> tuple[int, int] | None:
    if data[:4] == b"II*\x00":
        order = "little"
    elif data[:4] == b"MM\x00*":
        order = "big"
    else:
        return None
    directory = int.from_bytes(data[4:8], order)
    if directory + 2 > len(data):
        return None
    width = height = None
    for index in range(int.from_bytes(data[directory:directory + 2], order)):
        entry = directory + 2 + index * 12
        if entry + 12 > len(data):
            return None
        tag = int.from_bytes(data[entry:entry + 2], order)
        if tag not in (256, 257):
            continue
        kind = int.from_bytes(data[entry + 2:entry + 4], order)
        if kind == 3:
            value = int.from_bytes(data[entry + 8:entry + 10], order)
        elif kind == 4:
            value = int.from_bytes(data[entry + 8:entry + 12], order)
        else:
            return None
        if tag == 256:
            width = value
        else:
            height = value
    if width is None or height is None:
        return None
    return width, height


# Every still format the asset registry treats as media and whose dimensions sit
# in a header. A format the registry accepts but this list does not read would
# make the resolution rule unmeasurable for a file the project considers ordinary.
IMAGE_READERS = (png_size, jpeg_size, gif_size, bmp_size, webp_size, tiff_size)

# A working read chunk, not a maximum header/file size. Continue to EOF when a
# supported format has not exposed its dimensions in the first chunk.
HEADER_CHUNK_BYTES = 4 * 1024 * 1024


def image_size(path: Path) -> tuple[int, int] | None:
    """Read available header dimensions without treating a buffer as a file cap."""
    with path.open("rb") as handle:
        data = bytearray()
        while chunk := handle.read(HEADER_CHUNK_BYTES):
            data.extend(chunk)
            for reader in IMAGE_READERS:
                size = reader(data)
                if size is not None:
                    return size
    return None




def profile_directories(profiles: Path | str | Sequence[Path | str]) -> list[Path]:
    """The profile directories to search, in the order they are searched."""

    if isinstance(profiles, (str, Path)):
        return [Path(profiles)]
    return [Path(item) for item in profiles]


def _profiles(profiles: Path | str | Sequence[Path | str]):
    for directory in profile_directories(profiles):
        for path in sorted(directory.glob("*.json")):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if isinstance(value, dict):
                yield path, value


def load_profile(target: str, profiles: Path | str | Sequence[Path | str]) -> dict[str, Any] | None:
    """The first profile for a target, searching the directories in order.

    A project's own profile directory comes before the suite's, so a project
    that records its own observation of a target reads that one.
    """

    for path, value in _profiles(profiles):
        if value.get("target_id") == target or path.stem == target:
            return value
    return None


def profile_targets(profiles: Path | str | Sequence[Path | str]) -> list[str]:
    """The target ids the profiles in these directories record."""

    targets = [value["target_id"] for _, value in _profiles(profiles) if isinstance(value.get("target_id"), str)]
    return list(dict.fromkeys(targets))


def inside_project(declared: Any, root: Path, label: str, code: str,
                   errors: list[dict]) -> Path | None:
    """One project-relative path, or a refusal that says why it is not one."""

    if not isinstance(declared, str) or not declared.strip():
        return None
    candidate = Path(declared)
    if candidate.is_absolute() or ".." in candidate.parts:
        errors.append(finding(code, f"the {label} path must stay inside the project: {declared}"))
        return None
    path = (root / candidate).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        errors.append(finding(code, f"the {label} resolves outside the project: {declared}"))
        return None
    return path


def check_kind(submission: Any, errors: list[dict]) -> str | None:
    """The kind a submission declares, or a refusal saying why there is none.

    Not every submission depicts part of a scene. A reference-set image, a sheet
    panel, a location plate and a probe belong to no scene, so a submission says
    which it is. Saying nothing is refused rather than treated as the exempt case.
    """

    if not isinstance(submission, dict):
        errors.append(finding(
            "SUBMISSION_KIND_UNDECLARED",
            "a submission is an object naming what it is and what it carries, and this is "
            f"{shape(submission)}",
        ))
        return None
    kind = submission.get("kind")
    if absent(kind):
        # The required-field check reports the absence.
        return None
    if not isinstance(kind, str) or kind not in KINDS:
        shown = repr(kind) if isinstance(kind, str) else shape(kind)
        errors.append(finding(
            "SUBMISSION_KIND_UNDECLARED",
            f"the submission declares kind {shown}, which is none of {', '.join(KINDS)}: "
            "shot, page or passage for a submission that depicts part of a scene plot, "
            "asset for a reference, a sheet panel, a plate or a probe",
            field="kind",
        ))
        return None
    return kind


def plural(count: int, noun: str) -> str:
    return f"{count} {noun}" + ("" if count == 1 else "s")


def declared_units(value: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The units a valid plot's realization declares, by id."""

    return {unit["id"]: unit for unit in value["realization"]["units"]}


def describe_units(realization: str, units: dict[str, dict[str, Any]]) -> str:
    """The units a plot declares, as a reader of a refusal needs them listed."""

    if realization == "pages":
        return ", ".join(f"{name} ({plural(unit['panels'], 'panel')})" for name, unit in units.items())
    return ", ".join(units)


def read_scene_plot(declared: str, root: Path,
                    errors: list[dict]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """The approved plot a scene-linked submission names, or refusals saying why not.

    A scene proposition and a blocking table say what happens and where people
    stand; neither records which beat put a given thing in a given frame, and
    neither is agreed before the text exists. Without that stop the first thing
    anyone sees is a finished submission, and every correction after it is made
    one unit at a time.
    """

    from scene_plot import validate_scene_plot

    path = inside_project(declared, root, "scene plot", "SCENE_PLOT_OUTSIDE_ROOT", errors)
    if path is None:
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(finding("SCENE_PLOT_INVALID", f"the scene plot could not be read: {declared}: {exc}"))
        return None

    report = validate_scene_plot(value)
    if not report["ok"]:
        errors.append(finding(
            "SCENE_PLOT_INVALID", f"the scene plot is invalid: {declared}: " + "; ".join(report["errors"])))
        return None
    if not report["approved"]:
        reason = "; ".join(report["approval_errors"]) or "it carries no approved block"
        code = (
            "SCENE_PLOT_EDITED_AFTER_APPROVAL"
            if any("changed after it was approved" in item for item in report["approval_errors"])
            else "SCENE_PLOT_UNAPPROVED"
        )
        errors.append(finding(code, f"the scene plot is not approved: {declared}: {reason}"))
        return None
    return value, report


def check_unit(submission: dict[str, Any], kind: str, value: dict[str, Any],
               report: dict[str, Any], declared: str, errors: list[dict]) -> None:
    """The unit a scene-linked submission depicts is one its approved plot declares.

    A shot names a shot of the plot. A page names a page, and may narrow itself
    to one panel within that page's declared panel count. A passage names the
    passage it illustrates. Every refusal lists what the plot does declare, so
    the next attempt is a choice from that list rather than a guess.
    """

    wanted = SCENE_KINDS[kind]
    units = declared_units(value)
    listing = describe_units(report["realization"], units)
    if report["realization"] != wanted["realization"]:
        other = next(name for name, spec in SCENE_KINDS.items()
                     if spec["realization"] == report["realization"])
        errors.append(finding(
            "UNIT_NOT_IN_SCENE_PLOT",
            f"the submission declares kind {kind!r} and the scene plot {declared} is realized as "
            f"{report['realization']}: {listing}; a submission depicting one of them declares kind "
            f"{other!r} and names it as {SCENE_KINDS[other]['unit']!r}",
            realization=report["realization"], declared=list(units),
        ))
        return
    field = wanted["unit"]
    unit = submission.get(field)
    if absent(unit):
        errors.append(missing(field, f"the scene plot {declared} declares {report['realization']} {listing}"))
        return
    if not isinstance(unit, str):
        errors.append(finding(
            "UNIT_NOT_IN_SCENE_PLOT",
            f"{field!r} carries {shape(unit)} rather than the id of the {kind} it depicts; the "
            f"scene plot {declared} declares {report['realization']} {listing}",
            field=field, declared=list(units),
        ))
        return
    if unit not in units:
        errors.append(finding(
            "UNIT_NOT_IN_SCENE_PLOT",
            f"{kind} {unit!r} is not in the approved scene plot {declared}, which declares "
            f"{report['realization']} {listing}",
            field=field, declared=list(units),
        ))
        return
    panel = submission.get("panel")
    if kind == "page" and panel is not None:
        count = units[unit]["panels"]
        if isinstance(panel, bool) or not isinstance(panel, int) or not 1 <= panel <= count:
            shown = str(panel) if isinstance(panel, int) and not isinstance(panel, bool) else shape(panel)
            errors.append(finding(
                "UNIT_NOT_IN_SCENE_PLOT",
                f"panel {shown} is not on page {unit!r}, which the scene plot {declared} declares "
                f"with {plural(count, 'panel')}; "
                + ("name panel 1, or leave 'panel' out for the whole page" if count == 1
                   else f"name a panel from 1 to {count}, or leave 'panel' out for the whole page"),
                field="panel", page_id=unit, panels=count,
            ))


def check_scene_plot(submission: dict[str, Any], kind: str, root: Path, errors: list[dict],
                     unmeasured: list[str], shown: dict[str, list[str]] | None = None) -> None:
    """A scene-linked submission depicts a unit of a scene whose plot was approved first.

    `shown` maps each character the submission depicts to the fields that name
    them: `characters`, and the visual subjects that carry a character id.
    """

    fields = {name for name in SCENE_FIELDS if not absent(submission.get(name))}
    if kind == "asset":
        # An asset belongs to no scene, so the plot rules do not apply to it.
        # That is also the way around them, and the way around is a lie the gate
        # cannot catch from the submission alone: nothing in a text says whether
        # it depicts part of a scene. What it can catch is the lie that forgot to
        # tidy up, and what it must not do is let the skipped rules pass in silence.
        if fields:
            errors.append(finding(
                "FIELD_OF_ANOTHER_KIND",
                "the submission declares itself an asset and carries " + ", ".join(sorted(fields))
                + ", which belong to a submission that depicts part of a scene; an asset belongs "
                "to no scene",
                fields=sorted(fields),
            ))
            return
        unmeasured.append(
            "scene plot: the submission declares itself an asset, so the rules about a scene "
            "plot, the unit it declares, and who is in the scene were not applied"
        )
        return

    own = {"scene_plot", "scene_id", SCENE_KINDS[kind]["unit"]} | ({"panel"} if kind == "page" else set())
    foreign = sorted(fields - own)
    if foreign:
        errors.append(finding(
            "FIELD_OF_ANOTHER_KIND",
            f"the submission declares kind {kind!r} and carries " + ", ".join(foreign)
            + ("; it names" if len(foreign) == 1 else "; they name")
            + f" the unit of another kind, and a {kind} submission names its unit as "
            f"{SCENE_KINDS[kind]['unit']!r}" + (" and may name a 'panel'" if kind == "page" else ""),
            fields=foreign,
        ))

    declared = submission.get("scene_plot")
    if absent(declared) or not isinstance(declared, str):
        errors.append(missing("scene_plot"))
        return
    plot = read_scene_plot(declared, root, errors)
    if plot is None:
        return
    value, report = plot

    scene_id = submission.get("scene_id")
    if absent(scene_id):
        errors.append(missing("scene_id", f"the scene plot {declared} covers {report['scene_id']!r}"))
    elif scene_id != report["scene_id"]:
        errors.append(finding(
            "SCENE_ID_MISMATCH",
            f"the submission names scene {scene_id!r} and the plot covers {report['scene_id']!r}",
            field="scene_id",
        ))
        return

    # A submission depicting somebody the scene does not contain belongs to a
    # different scene, or its plot omits who was there. Either way the two
    # documents disagree and neither one is the answer.
    for who, sources in (shown or {}).items():
        if who not in report["characters"]:
            errors.append(finding(
                "CHARACTER_NOT_IN_SCENE",
                f"the submission names character {who!r} in {', '.join(sources)}, and the scene "
                f"plot {declared} carries {report['characters']}",
                character=who,
            ))

    # The narrative this plot was approved against. A change above a plot
    # invalidates what was approved below it, and a gate that does not look is a
    # gate that spends on a plan whose premises moved.
    from narrative import content_sha256 as narrative_content_sha256

    declared_narrative = submission.get("narrative")
    if not isinstance(declared_narrative, str) or not declared_narrative.strip():
        unmeasured.append(
            "scene plot: the submission names no narrative, so the plot's "
            "narrative_sha256 could not be compared with what the narrative now says"
        )
    else:
        narrative_path = inside_project(declared_narrative, root, "narrative",
                                        "NARRATIVE_OUTSIDE_ROOT", errors)
        if narrative_path is not None:
            try:
                document = json.loads(narrative_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append(finding(
                    "NARRATIVE_INVALID",
                    f"the narrative could not be read: {declared_narrative}: {exc}",
                ))
            else:
                if not isinstance(document, dict):
                    errors.append(finding(
                        "NARRATIVE_INVALID",
                        f"the narrative is not an object: {declared_narrative}",
                    ))
                    return
                current = narrative_content_sha256(document)
                if report["narrative_sha256"] != current:
                    errors.append(finding(
                        "SCENE_PLOT_BEHIND_NARRATIVE",
                        f"the scene plot {declared} was approved against narrative "
                        f"{report['narrative_sha256'][:12]} and the narrative is now "
                        f"{current[:12]}; approve the plot against what the narrative now says",
                        scene_plot=declared,
                    ))

    check_unit(submission, kind, value, report, declared, errors)


def shown_characters(submission: dict[str, Any], visual: Any) -> dict[str, list[str]]:
    """Each character a submission depicts, with the fields that name them."""

    shown: dict[str, list[str]] = {}
    present = submission.get("characters")
    if isinstance(present, list):
        for who in present:
            shown.setdefault(str(who), []).append("characters")
    subjects = visual.get("subjects") if isinstance(visual, dict) else None
    if isinstance(subjects, dict):
        for subject in subjects.values():
            who = subject.get("character_id") if isinstance(subject, dict) else None
            if isinstance(who, str) and who.strip():
                where = "visual_continuity.subjects"
                if where not in shown.setdefault(who, []):
                    shown[who].append(where)
    return shown


def check_prohibitions(submission: dict[str, Any], root: Path, errors: list[dict],
                       unmeasured: list[str]) -> None:
    """A shot's text does not break what its characters are declared never to do.

    Lock surfaces and permanent features are about what the frame shows. A
    persona also declares what a person would never say or do, and a gate that
    reads only the visual obligations admits a line in which a guarded character
    accounts for himself.

    A `surface` prohibition names a phrase and is refused when the text carries
    it. A `judgement` prohibition names a behaviour, which no string search
    settles, so it is reported with the text for a person to answer.
    """

    from narrative import validate_narrative

    if not isinstance(submission, dict):
        return
    declared = submission.get("narrative")
    if not isinstance(declared, str) or not declared.strip():
        unmeasured.append(
            "character prohibitions: the submission names no narrative, so what these "
            "characters never do could not be read"
        )
        return
    candidate = Path(declared)
    if candidate.is_absolute() or ".." in candidate.parts:
        errors.append(finding(
            "NARRATIVE_OUTSIDE_ROOT",
            f"the narrative path must stay inside the project: {declared}",
        ))
        return
    path = (root / candidate).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        errors.append(finding(
            "NARRATIVE_OUTSIDE_ROOT",
            f"the narrative resolves outside the project: {declared}",
        ))
        return
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(finding("NARRATIVE_INVALID", f"the narrative could not be read: {declared}: {exc}"))
        return
    report = validate_narrative(value)
    if not report["ok"]:
        shown = report["errors"]
        elided = len(report["errors"]) - len(shown)
        detail = "; ".join(shown) + (f"; and {elided} more" if elided else "")
        errors.append(finding("NARRATIVE_INVALID", f"the narrative is invalid: {declared}: {detail}"))
        return

    present = submission.get("characters")
    if not isinstance(present, list) or not present:
        unmeasured.append(
            "character prohibitions: the submission declares no 'characters', so the gate "
            "could not tell whose rules apply to this text"
        )
        return

    declared_ids = {str(entry.get("id")): entry for entry in value.get("characters") or []
                    if isinstance(entry, dict)}
    for character_id in present:
        entry = declared_ids.get(str(character_id))
        if entry is None:
            errors.append(finding(
                "CHARACTER_NOT_IN_NARRATIVE",
                f"the submission names character {character_id!r}, which the narrative does not carry",
            ))
            continue
        for ban in entry.get("prohibitions") or []:
            if not isinstance(ban, dict):
                continue
            if ban.get("kind") == "surface":
                surface = str(ban.get("surface") or "")
                # On a word boundary, the way the lock check in this same file
                # reads one. Without it "unI am sorryX" counts as the line.
                pattern = re.compile(rf"(?<!\w){re.escape(surface)}(?!\w)") if surface else None
                if pattern is not None and pattern.search(text_of(submission)):
                    errors.append(finding(
                        "PROHIBITED_SURFACE",
                        f"{character_id} is declared never to say {surface!r} and the text carries it"
                        + (f": {ban['note']}" if ban.get("note") else ""),
                        character=str(character_id),
                        surface=surface,
                    ))
            else:
                unmeasured.append(
                    f"character prohibition for {character_id}, which no string search settles: "
                    + str(ban.get("statement") or "")
                )


def text_of(submission: dict[str, Any]) -> str:
    """Every string this submission asks the surface to render.

    The negative field is not one of them. It says what to keep out, so a
    character's forbidden line placed there is the way to comply with the rule,
    and refusing it refuses the remedy.
    """

    if not isinstance(submission, dict):
        return ""
    parts = [str(submission.get("text") or "")]
    dialogue = submission.get("dialogue")
    if isinstance(dialogue, list):
        parts.extend(str(line) for line in dialogue)
    elif isinstance(dialogue, str):
        parts.append(dialogue)
    return chr(10).join(parts)


def check_locks(text: str, locks: list[str], errors: list[dict]) -> None:
    """A lock surface is carried verbatim or it is not carried.

    A garment named from memory instead of copied replaces the approved one, and
    it does so in every take, because the reference is still visibly doing its
    job on everything else.
    """

    for surface in locks:
        if surface not in text:
            errors.append(finding(
                "LOCK_SURFACE_ABSENT",
                f"declared lock surface is missing from the text: {surface!r}",
                surface=surface,
            ))
            continue
        # A match glued to a longer word is not the phrase. `chipped white
        # enamel mug` is not satisfied by `unchipped white enamel mug`.
        for match in re.finditer(re.escape(surface), text):
            before = text[match.start() - 1] if match.start() else " "
            after = text[match.end()] if match.end() < len(text) else " "
            if not (before.isalnum() or before == "-") and not (after.isalnum() or after == "-"):
                break
        else:
            errors.append(finding(
                "LOCK_SURFACE_GLUED",
                f"lock surface appears only inside a longer word: {surface!r}",
                surface=surface,
            ))












def check_input_modes(
    inputs: list[dict],
    profile: dict[str, Any] | None,
    offering: dict[str, Any] | None,
    errors: list[dict],
    unmeasured: list[str],
) -> list[str | None]:
    """The mode each input occupies, and the model's rules about modes.

    A mode is the model's name for what an input supplies, such as reference
    images or frame images. An input names its `mode`. Where a service is named,
    it may name the `request_key` it occupies instead, and the offering says
    which mode that key carries. Where it names neither, the role is matched
    against the modes that take media, and a role more than one mode could hold
    is reported rather than charged. A submission carrying one reference is not
    carrying every channel the model exposes, and refusing it for a conflict
    between two channels it never used would refuse a submission that is fine.

    Exclusivity and counts are properties of the model, so they are checked
    with or without a service.
    """

    none: list[str | None] = [None] * len(inputs)
    if profile is None:
        unmeasured.append("input modes: no target profile was read, so the modes were not compared")
        return none
    modes = {mode["mode"]: mode for mode in profile.get("input_modes") or []
             if isinstance(mode, dict) and isinstance(mode.get("mode"), str)}
    if not modes:
        unmeasured.append("input modes: the profile declares none, so the modes were not compared")
        return none
    keys = (offering or {}).get("request_keys") or {}
    by_key = {key: mode for mode, values in keys.items() if isinstance(values, list) for key in values}
    service = (offering or {}).get("service")
    # The modes that take media: the ones the offering maps, or without a
    # service, the ones whose count the model states.
    media_modes = sorted(keys) if offering else sorted(name for name, mode in modes.items() if mode.get("max_inputs"))

    resolved: list[str | None] = []
    for index, item in enumerate(inputs):
        mode = item.get("mode")
        if mode is not None and (not isinstance(mode, str) or mode not in modes):
            shown = repr(mode) if isinstance(mode, str) else shape(mode)
            unmeasured.append(
                f"input modes: input {index} names mode {shown}, which the profile does not record; "
                f"it records {', '.join(repr(name) for name in sorted(modes))}"
            )
            resolved.append(None)
            continue
        key = item.get("request_key")
        if key is not None and not isinstance(key, str):
            unmeasured.append(
                f"input modes: input {index} names a request key that is not a name but {shape(key)}, "
                "so the mode it occupies was not read from it"
            )
        elif key is not None and offering is not None:
            if key not in by_key:
                unmeasured.append(
                    f"input modes: input {index} names request key {key!r}, which the offering on "
                    f"{service!r} does not record; it records {', '.join(sorted(by_key)) or 'none'}"
                )
            elif mode is not None and mode != by_key[key]:
                errors.append(finding(
                    "INPUT_MODE_CONFLICT",
                    f"input {index} names mode {mode!r} and request key {key!r}, which the offering on "
                    f"{service!r} gives to mode {by_key[key]!r}",
                    input=index, mode=mode, request_key=key,
                ))
            else:
                mode = by_key[key]
        if mode is None:
            role = item.get("role", "reference")
            if not isinstance(role, str):
                unmeasured.append(
                    f"input modes: input {index} names a role that is not a name but {shape(role)}, "
                    "so the mode it occupies was not read"
                )
                resolved.append(None)
                continue
            wants_frame = role in {"first_frame", "last_frame"}
            candidates = [name for name in media_modes if ("frame" in name.lower()) == wants_frame]
            if len(candidates) == 1:
                mode = candidates[0]
            elif not candidates:
                unmeasured.append(
                    f"input modes: input {index} has the role {role!r}, and the profile declares no mode that carries it"
                )
            else:
                where = ", ".join(repr(name) for name in candidates)
                also = (f", or one of the request keys {', '.join(key for name in candidates for key in keys[name])}"
                        if offering else "")
                unmeasured.append(
                    f"input modes: input {index} has the role {role!r}, which could occupy any of the modes "
                    f"{where}; name mode on the input{also} to settle it"
                )
        resolved.append(mode)

    used = [mode for mode in resolved if mode is not None]
    for name in sorted(set(used)):
        limit = modes[name].get("max_inputs")
        count = used.count(name)
        if isinstance(limit, int) and not isinstance(limit, bool) and count > limit:
            errors.append(finding(
                "INPUT_MODE_LIMIT",
                f"the profile records that mode {name!r} takes at most {plural(limit, 'input')}, and this "
                f"submission sends {count}",
                mode=name, limit=limit, count=count,
            ))
    # One finding per excluded pair. The profile states an exclusion from both
    # sides, and reporting it twice says the submission has two problems.
    reported: set[tuple[str, str]] = set()
    for name in sorted(set(used)):
        for excluded in modes[name].get("excludes") or []:
            if excluded not in used:
                continue
            pair = (min(name, excluded), max(name, excluded))
            if pair in reported:
                continue
            reported.add(pair)
            errors.append(finding(
                "INPUT_MODE_CONFLICT",
                f"the profile records that mode {pair[0]!r} excludes mode {pair[1]!r}, and this submission uses both",
                mode=pair[0], excluded=pair[1],
            ))
    return resolved


def minimum_shorter_side(
    profile: dict[str, Any] | None, obligations: dict[str, Any]
) -> tuple[int | None, str]:
    """The pixel floor to apply to an identity reference, and where it came from.

    Nobody should have to guess which number a refusal used. A target profile
    records the floor its surface documents; a submission states the floor this
    run wants; no floor is invented when neither supplies one. Where
    a profile and a submission both speak, the stricter number stands: the
    profile's is a property of the surface, and raising it is the submission's to
    do, not lowering it.
    """

    recorded = None
    if isinstance(profile, dict):
        value = (profile.get("identity_reference") or {}).get("minimum_shorter_side")
        if isinstance(value, int) and not isinstance(value, bool):
            recorded = value
    declared = obligations.get("identity_reference_minimum_shorter_side")
    if not isinstance(declared, int) or isinstance(declared, bool):
        declared = None

    if recorded is not None and declared is not None:
        return ((recorded, "the target profile") if recorded >= declared
                else (declared, "this submission"))
    if recorded is not None:
        return recorded, "the target profile"
    if declared is not None:
        return declared, "this submission"
    return None, "no documented or operator-declared floor"


def check_identity_resolution(
    inputs: list[dict],
    identity_roles: list[str],
    root: Path,
    minimum: int | None,
    source: str,
    errors: list[dict],
    unmeasured: list[str],
) -> None:
    """A reference's resolution is not the number in its file name.

    A full length figure spends nearly all of its pixels on the body, so the face
    inside it can be a fraction of the frame even in a large file. What matters is
    how many pixels sit on the feature that has to survive, and the only honest
    stand-in this file has for that is the shorter side of the image.

    The floor itself is not this file's to choose. It arrives from the profile,
    or the submission, and every refusal names its source. Without a recorded
    requirement this check remains unmeasured, rather than inventing a floor.
    """

    if minimum is None:
        unmeasured.append("identity reference resolution: no documented or operator-declared floor; no guessed minimum is applied")
        return
    candidates = [item for item in inputs if item.get("role") in identity_roles]
    if not candidates:
        unmeasured.append("identity reference resolution: no input carries an identity role")
        return

    for item in candidates:
        declared = item.get("path") if isinstance(item, dict) else None
        if not isinstance(declared, str) or not declared.strip():
            unmeasured.append("identity reference resolution: an input names no file")
            continue
        path = Path(declared)
        if not path.is_absolute():
            path = root / path
        if not path.is_file():
            unmeasured.append(f"identity reference resolution: {declared} is not on disk")
            continue
        try:
            size = image_size(path)
        except OSError as error:
            unmeasured.append(f"identity reference resolution: {item['path']} did not open: {error}")
            continue
        if size is None:
            unmeasured.append(
                f"identity reference resolution: {item['path']} is not a still image this gate "
                "can measure, so its resolution is not settled here"
            )
            continue
        width, height = size
        if min(width, height) < minimum:
            errors.append(finding(
                "IDENTITY_REFERENCE_TOO_SMALL",
                f"{item['path']} is {width}x{height}. The shorter side is under {minimum}, the "
                f"floor {source} sets, so it does not satisfy that declared requirement",
                path=item["path"],
                width=width,
                height=height,
                minimum=minimum,
                minimum_source=source,
            ))


def check_identity_carrier(inputs: list[dict], obligations: dict, unmeasured: list[str]) -> None:
    """A sheet reaches a surface only as an image.

    A submission that declares lock surfaces or permanent features is a submission
    about a recurring character. When it carries no input at all, nothing of that
    character's registered appearance reaches the surface: the text and a seed
    number do not carry a sheet. This file cannot know whether the run was meant to
    compose without one, so it reports the absence instead of refusing it.
    """

    if inputs:
        return
    if not (obligations.get("locks") or obligations.get("permanent_features")):
        return
    unmeasured.append(
        "identity carrier absent: the submission names a character's locks or features "
        "but sends no reference and no seed image, so nothing of the registered appearance "
        "reaches the surface; a text and a seed alone do not carry a sheet"
    )


def select_offering(profile: dict[str, Any] | None, service: Any, unmeasured: list[str]) -> dict[str, Any] | None:
    """The offering of the service the submission names, and no other.

    An offering is the model as one service exposes it: its request keys, its
    limits and its schema. A submission that names no service is checked against
    the model alone, and each rule that belongs to a service says it was not
    applied. An offering is never chosen for a submission that did not choose it.
    """

    if profile is None:
        return None
    offerings = [item for item in (profile.get("offerings") or []) if isinstance(item, dict)]
    services = ", ".join(str(item.get("service")) for item in offerings) or "none"
    if absent(service):
        for rule, effect in (("request keys", "no request key was read"),
                             ("service limits", "no offering limit was applied"),
                             ("parameter schema", "no service schema was evaluated")):
            unmeasured.append(f"{rule}: the submission names no service, so {effect}; the profile records "
                              f"offerings on {services}")
        return None
    for offering in offerings:
        if offering.get("service") == service:
            return offering
    shown = repr(service) if isinstance(service, str) else shape(service)
    unmeasured.append(
        f"offering: the profile records no offering on service {shown}; it records {services}, so no "
        "request key, service limit or service schema was applied"
    )
    return None


def check_parameters(parameters: dict[str, Any], offering: dict[str, Any] | None, media_kind: list[str], errors: list[dict], unmeasured: list[str]) -> None:
    """A limit the service enforces at submission is settled here instead.

    The duration band is the one such limit recorded so far. A submission that
    states its duration is checked against the band; one that does not state it
    on a video surface is reported, because the gate cannot check what it was not
    given. Without an offering, the band is the service's and is not applied.
    """

    if offering is None:
        return
    constraints = offering.get("constraints") or {}
    band = constraints.get("duration_seconds")
    is_video = bool(set(media_kind) & {"video", "video-with-audio"})
    duration = parameters.get("duration")
    if band and duration is None and is_video:
        unmeasured.append("duration: the submission does not state it, so the offering's band was not checked")
        return
    if band and duration is not None:
        observed = offering.get("observed_at", "an unrecorded date")
        if band.get("integer") and (isinstance(duration, bool) or not isinstance(duration, int)):
            errors.append(finding("DURATION_NOT_INTEGER", f"the offering records whole seconds only (observed {observed}); the submission states {duration!r}", duration=duration))
            return
        if isinstance(duration, bool) or not isinstance(duration, (int, float)):
            unmeasured.append(
                f"duration: the submission states {duration!r}, which is not a number, so the "
                "offering's band was not checked"
            )
            return
        low, high = band.get("min"), band.get("max")
        if (low is not None and duration < low) or (high is not None and duration > high):
            errors.append(finding(
                "DURATION_OUT_OF_BAND",
                f"the offering records a duration band of {low} to {high} seconds (observed {observed}); the submission states {duration}",
                duration=duration, min=low, max=high,
            ))


def schema_violations(instance: Any, schema: Any, path: str = "$") -> list[str]:
    """Evaluate the subset of JSON Schema that service parameter schemas use.

    Supported: type, const, enum, minimum, maximum, minLength, maxLength,
    minItems, maxItems, required, properties, additionalProperties, items,
    dependentRequired, allOf, anyOf, oneOf, not, if/then/else. A keyword outside
    that set is ignored, which errs toward admitting; the service settles the rest.
    """

    if not isinstance(schema, dict):
        return []
    out: list[str] = []
    types = {"object": dict, "array": list, "string": str, "boolean": bool, "integer": int, "number": (int, float)}
    t = schema.get("type")
    if t is not None:
        wanted = t if isinstance(t, list) else [t]
        ok = False
        for w in wanted:
            cls = types.get(w)
            if cls is None:
                ok = True
            elif w == "integer":
                ok = ok or (isinstance(instance, int) and not isinstance(instance, bool))
            elif w == "number":
                ok = ok or (isinstance(instance, (int, float)) and not isinstance(instance, bool))
            else:
                ok = ok or isinstance(instance, cls)
        if not ok:
            return [f"{path}: type is not {t}"]
    if "const" in schema and instance != schema["const"]:
        out.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        out.append(f"{path}: must be one of {schema['enum']}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            out.append(f"{path}: {instance} is below the minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            out.append(f"{path}: {instance} is above the maximum {schema['maximum']}")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            out.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            out.append(f"{path}: longer than {schema['maxLength']}")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            out.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            out.append(f"{path}: more than {schema['maxItems']} items")
        if "items" in schema:
            for i, item in enumerate(instance):
                out += schema_violations(item, schema["items"], f"{path}[{i}]")
    if isinstance(instance, dict):
        for key in schema.get("required") or []:
            if key not in instance:
                out.append(f"{path}: {key} is required")
        props = schema.get("properties") or {}
        for key, sub in props.items():
            if key in instance:
                out += schema_violations(instance[key], sub, f"{path}.{key}")
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in props:
                    out.append(f"{path}: {key} is not an accepted parameter")
        for key, needs in (schema.get("dependentRequired") or {}).items():
            if key in instance:
                for need in needs:
                    if need not in instance:
                        out.append(f"{path}: {key} requires {need}")
    for sub in schema.get("allOf") or []:
        out += schema_violations(instance, sub, path)
    if "anyOf" in schema:
        if not any(not schema_violations(instance, sub, path) for sub in schema["anyOf"]):
            out.append(f"{path}: matches none of the alternatives")
    if "oneOf" in schema:
        matches = [sub for sub in schema["oneOf"] if not schema_violations(instance, sub, path)]
        if len(matches) != 1:
            titles = [sub.get("title") for sub in schema["oneOf"] if sub.get("title")]
            out.append(f"{path}: must match exactly one of {titles or 'the alternatives'}; matched {len(matches)}")
    if "not" in schema and not schema_violations(instance, schema["not"], path):
        out.append(f"{path}: a forbidden combination")
    if "if" in schema:
        if not schema_violations(instance, schema["if"], path):
            if "then" in schema:
                out += schema_violations(instance, schema["then"], path)
        elif "else" in schema:
            out += schema_violations(instance, schema["else"], path)
    return out


# A stand-in for one media reference, in each form a request shape can declare.
# The schema check needs a value of the right form, not the file itself.
MEDIA_REFERENCES = {
    "uuid": "00000000-0000-4000-8000-000000000000",
    "url": "https://example.invalid/media",
    "data-uri": "data:image/png;base64,AAAA",
}
REQUEST_SHAPE_FIELDS = ("model_key", "text_key", "media_reference", "single_value_keys")


def place(request: dict[str, Any], key: str, value: Any, *, single: bool) -> None:
    """Put a value at a dotted request path, as one value or appended to a list."""

    parts = key.split(".")
    target = request
    for part in parts[:-1]:
        nested = target.get(part)
        if not isinstance(nested, dict):
            nested = target[part] = {}
        target = nested
    if single:
        target[parts[-1]] = value
    else:
        current = target.get(parts[-1])
        target[parts[-1]] = (current if isinstance(current, list) else []) + [value]


def media_key(item: dict[str, Any], mode: str | None, offering: dict[str, Any]) -> str | None:
    """The request key one input occupies on this offering, when it can be settled."""

    key = item.get("request_key")
    if isinstance(key, str) and key:
        return key
    keys = (offering.get("request_keys") or {}).get(mode) if mode else None
    return keys[0] if isinstance(keys, list) and len(keys) == 1 else None


def build_instance(text: str, inputs: list[dict], modes: list[str | None], parameters: dict[str, Any],
                   offering: dict[str, Any], negative_text: str | None = None) -> dict[str, Any]:
    """The request as the service would see it, formed by the shape the offering declares.

    The declaration names where the model identifier and the text go, where a
    negative text goes if the service has one, how a media reference is written,
    and which media keys take one value rather than a list. Nothing about any
    service is written here.
    """

    shape_ = offering["request_shape"]
    request: dict[str, Any] = copy.deepcopy(parameters or {})
    place(request, shape_["model_key"], offering.get("model_identifier"), single=True)
    place(request, shape_["text_key"], text, single=True)
    if negative_text and shape_.get("negative_text_key"):
        place(request, shape_["negative_text_key"], negative_text, single=True)
    reference = MEDIA_REFERENCES[shape_["media_reference"]]
    single = set(shape_.get("single_value_keys") or [])
    for item, mode in zip(inputs, modes):
        key = media_key(item, mode, offering)
        if key:
            place(request, key, reference, single=key in single)
    return request


def check_schema(text: str, inputs: list[dict], modes: list[str | None], parameters: dict[str, Any] | None,
                 offering: dict[str, Any] | None, root: Path, errors: list[dict], unmeasured: list[str],
                 negative_text: str | None = None) -> None:
    """The service's own parameter schema, observed and stored, settles what it can."""

    if offering is None:
        return
    service = offering.get("service")
    shape_ = offering.get("request_shape")
    if (not isinstance(shape_, dict) or any(field not in shape_ for field in REQUEST_SHAPE_FIELDS)
            or shape_.get("media_reference") not in MEDIA_REFERENCES):
        unmeasured.append(f"parameter schema: the offering on {service!r} declares no complete request shape, "
                          "so the request could not be formed")
        return
    if negative_text and not shape_.get("negative_text_key"):
        unmeasured.append(f"negative text: the offering on {service!r} declares no negative text key, so the "
                          "negative text is not part of the request the schema reads")
    if not offering.get("schema_snapshot"):
        unmeasured.append(f"parameter schema: the offering on {service!r} records no observed schema")
        return
    if parameters is None:
        unmeasured.append("parameter schema: the submission states no parameters, so the schema was not evaluated")
        return
    candidates = [ROOT / offering["schema_snapshot"], root / offering["schema_snapshot"]]
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        unmeasured.append(f"parameter schema: {offering['schema_snapshot']} is not on disk")
        return
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        unmeasured.append(f"parameter schema: {path.name} did not load: {error}")
        return
    schema = snapshot.get("schema") if isinstance(snapshot, dict) else None
    if not isinstance(schema, dict):
        unmeasured.append(f"parameter schema: {path.name} carries no schema")
        return
    observed = snapshot.get("observed_at") or offering.get("observed_at") or "undated"
    instance = build_instance(text, inputs, modes, parameters or {}, offering, negative_text)
    for violation in dict.fromkeys(schema_violations(instance, schema)):
        errors.append(finding("SCHEMA_REFUSAL", f"the parameter schema of the offering on {service!r} (observed {observed}) refuses this request: {violation}", schema_rule=violation))


def check_as_written(parameters: dict[str, Any] | None, offering: dict[str, Any] | None, unmeasured: list[str]) -> None:
    """A submission that turns the service's rewriting back on is reported, not refused.

    The offering's as_written keys are what the dispatcher sets by default so the
    text reaches the model as sent; a submission that sets one of them to another
    value has chosen to be rewritten, and the user sees that before sending.
    """

    defaults = ((offering or {}).get("constraints") or {}).get("as_written") or {}
    if not defaults or not parameters:
        return

    def walk(wanted: dict[str, Any], given: Any, path: str) -> None:
        if not isinstance(given, dict):
            return
        for key, value in wanted.items():
            here = f"{path}.{key}" if path else key
            if isinstance(value, dict):
                walk(value, given.get(key), here)
            elif key in given and given[key] != value:
                unmeasured.append(
                    f"text as written: the submission sets {here} to {given[key]!r}, so the service rewrites "
                    f"the text; {value!r} sends it as written"
                )

    walk(defaults, parameters, "")


def declared_mapping(value: Any, label: str, unmeasured: list[str]) -> dict[str, Any] | None:
    """One untrusted block of named fields, or nothing and a line saying so.

    A project file is untrusted data. A block that is a string, a list or a
    number holds no named field, so every check reading one would have to ask
    again what shape it is; it is dropped once, here, and reported, which is the
    difference between a gate that refuses and one that raises.
    """

    if value is None or isinstance(value, dict):
        return value
    unmeasured.append(
        f"{label}: the submission carries {shape(value)} where the named fields "
        "go, so nothing in it was read"
    )
    return None


def declared_phrases(value: Any, label: str, unmeasured: list[str]) -> list[str]:
    """One untrusted list of phrases: the strings in it, and a line for the rest.

    A bare string is the trap this exists for. `"black boxer briefs"` iterates,
    so a loop written for a list walks it one character at a time and refuses
    the submission eighteen times over surfaces nobody declared.
    """

    if value is None:
        return []
    if not isinstance(value, list):
        unmeasured.append(
            f"{label}: the submission carries {shape(value)} where the list goes"
            + (", and one phrase is not a list of them" if isinstance(value, str) else "")
            + ", so none of it was read"
        )
        return []
    kept = [item for item in value if isinstance(item, str)]
    dropped = len(value) - len(kept)
    if dropped:
        unmeasured.append(
            f"{label}: {dropped} entry that names no phrase was dropped" if dropped == 1
            else f"{label}: {dropped} entries that name no phrase were dropped"
        )
    return kept


def review_requirements(submission: dict) -> list[dict]:
    """Carry authored requirements to review without judging their realization."""
    obligations = submission.get('obligations')
    if not isinstance(obligations, dict): return []
    values = obligations.get('permanent_features') or []
    if not isinstance(values, list): return []
    return [{'id': 'declared-feature-' + str(i), 'source': {'field': 'obligations.permanent_features', 'index': i},
             'statement': value, 'requires': 'rendition-review'}
            for i, value in enumerate(values) if isinstance(value, str) and value.strip()]


def verdict(submission: Any, profile: dict[str, Any] | None, offering: dict[str, Any] | None,
            errors: list[dict], unmeasured: list[str]) -> dict[str, Any]:
    """One report shape for every answer, including a document that is not an object."""

    known = submission if isinstance(submission, dict) else {}
    return {
        "gate": "submission",
        "submission_id": known.get("submission_id"),
        "target": known.get("target"),
        "profile_found": profile is not None,
        "service": (offering or {}).get("service") or known.get("service"),
        "offering_observed_at": (offering or {}).get("observed_at"),
        "review_requirements": review_requirements(known),
        "status": "refused" if errors else "admitted",
        "errors": errors,
        "unmeasured": unmeasured,
    }


def check_route_reading(submission: dict[str, Any], root: Path, errors: list[dict]) -> None:
    """A current reading of the media route, with an application from each required document."""

    from route_reading import require_route_reading
    try:
        require_route_reading(submission["route_reading"], project=root, routes={"media"})
    except (ValueError, OSError, TypeError, KeyError) as exc:
        errors.append(finding("ROUTE_READING_INVALID", f"route_reading: {exc}", field="route_reading"))


def check_visual(submission: dict[str, Any], kind: str | None, gaps: set[str], root: Path,
                 profile: dict[str, Any] | None, errors: list[dict], unmeasured: list[str]) -> Any:
    """The visual continuity block, checked against its hash and against current bytes.

    Returns the block when it answers its contract, so the scene rules can read
    which characters it depicts.
    """

    import execution_contract
    import visual_continuity

    if "visual_continuity" in gaps:
        return None
    if kind is None:
        unmeasured.append(
            "visual continuity: the submission declares no kind the block could be checked "
            "against, so it was not checked"
        )
        return None
    visual = submission["visual_continuity"]
    if ("visual_continuity_sha256" not in gaps
            and execution_contract.content_id(visual) != submission["visual_continuity_sha256"]):
        errors.append(finding(
            "VISUAL_CONTINUITY_INVALID",
            "visual_continuity_sha256 does not match the visual_continuity block, so the block "
            "changed after it was built; rebuild it with scripts/visual_continuity.py build",
            field="visual_continuity_sha256",
        ))
    try:
        continuity = visual_continuity.require(visual, submission=submission, root=root, profile=profile)
    except (ValueError, OSError, TypeError, KeyError) as exc:
        errors.append(finding("VISUAL_CONTINUITY_INVALID", f"visual_continuity: {exc}",
                              field="visual_continuity"))
        return None
    unmeasured.extend(item["reason"] if isinstance(item, dict) else item for item in continuity["unmeasured"])
    return visual


def gate(submission: dict[str, Any], profiles_dir: Path | Sequence[Path], root: Path) -> dict[str, Any]:
    """The verdict on one submission.

    `profiles_dir` is one profile directory or several, searched in order, so a
    project's own profiles can come before the suite's.
    """

    errors: list[dict[str, Any]] = []
    unmeasured: list[str] = []

    # A submission is an object, and every check below reads a named field of
    # it. A string, a list or a number carries none, so asking one of them for
    # `text` raises where a gate has to refuse. The kind rule already states
    # what a submission is, so the refusal is its own and the verdict is built
    # out of the nothing that is known about this document.
    if not isinstance(submission, dict):
        check_kind(submission, errors)
        return verdict(submission, None, None, errors, unmeasured)

    # A draft still holding a placeholder is unfinished, and every rule read
    # against it would report the placeholder under another name.
    unfilled = placeholders(submission)
    if unfilled:
        for field, asks in unfilled:
            errors.append(finding("PLACEHOLDER_UNFILLED", f"placeholder not filled: {field}",
                                  field=field, asks=asks))
        unmeasured.append(
            f"every rule: {plural(len(unfilled), 'field')} still "
            + ("holds" if len(unfilled) == 1 else "hold")
            + " a placeholder, so no rule was applied; fill them and run the gate again"
        )
        return verdict(submission, None, None, errors, unmeasured)

    kind = check_kind(submission, errors)
    # The fields every kind carries. The fields of a scene-linked kind are
    # reported by the scene rules, which can name what the plot declares.
    gaps = {field for field in REQUIRED_EVERY_KIND if absent(submission.get(field))}
    for field in REQUIRED_EVERY_KIND:
        if field in gaps:
            errors.append(missing(field))

    if "route_reading" not in gaps:
        check_route_reading(submission, root, errors)
    text = submission.get("text")
    if "text" not in gaps and not isinstance(text, str):
        errors.append(finding(
            "TEXT_MISSING",
            f"'text' carries {shape(text)} where the model-facing text goes",
            field="text",
        ))
    if not isinstance(text, str):
        text = ""

    obligations = declared_mapping(submission.get("obligations"), "obligations", unmeasured) or {}
    locks = declared_phrases(obligations.get("locks"), "lock surfaces", unmeasured)
    declared_phrases(obligations.get("permanent_features"), "permanent features", unmeasured)
    identity_roles = declared_phrases(
        obligations.get("identity_reference_roles"), "identity reference roles", unmeasured)
    # A parameter block that was not read is not an empty one: the schema check
    # tells a submission that states no parameters from one that states some,
    # and this has to reach it as the first of those.
    parameters = declared_mapping(submission.get("parameters"), "parameters", unmeasured)
    text_form = submission.get("text_form")
    if text_form is not None and not isinstance(text_form, str):
        unmeasured.append(
            f"text form: the submission states {shape(text_form)} rather than a "
            "name, so it was not read"
        )
    negative_text = submission.get("negative_text")
    if negative_text is not None and not isinstance(negative_text, str):
        unmeasured.append(
            f"negative text: the submission states {shape(negative_text)} rather "
            "than text, so it was not read"
        )
    # An input that is not an object names no role, no request key and no file.
    declared_inputs = submission.get("inputs") or []
    if not isinstance(declared_inputs, list):
        unmeasured.append("inputs: the submission does not carry a list of them")
        declared_inputs = []
    inputs = [item for item in declared_inputs if isinstance(item, dict)]
    for index, item in enumerate(declared_inputs):
        if not isinstance(item, dict):
            unmeasured.append(f"inputs[{index}] is not an object, so nothing about it was read")

    target = submission.get("target")
    profile = None
    if absent(target):
        unmeasured.append("target: the submission names no target, so no target profile was read")
    elif not isinstance(target, str):
        unmeasured.append(f"target: the submission states {shape(target)} rather than a target id, "
                          "so no target profile was read")
    else:
        profile = load_profile(target, profiles_dir)
        if profile is None:
            unmeasured.append(
                f"target profile {target!r} was not found in "
                + ", ".join(str(item) for item in profile_directories(profiles_dir))
                + "; they record " + (", ".join(profile_targets(profiles_dir)) or "none")
            )

    visual = check_visual(submission, kind, gaps, root, profile, errors, unmeasured)
    if kind is not None:
        check_scene_plot(submission, kind, root, errors, unmeasured,
                         shown_characters(submission, visual))
    check_prohibitions(submission, root, errors, unmeasured)
    check_locks(text, locks, errors)
    check_identity_carrier(inputs, obligations, unmeasured)
    offering = select_offering(profile, submission.get("service"), unmeasured)
    modes = check_input_modes(inputs, profile, offering, errors, unmeasured)
    check_parameters(parameters or {}, offering, list((profile or {}).get("media_kind") or []), errors, unmeasured)
    check_schema(text, inputs, modes, parameters, offering, root, errors, unmeasured,
                 negative_text if isinstance(negative_text, str) else None)
    check_as_written(parameters, offering, unmeasured)
    minimum, source = minimum_shorter_side(profile, obligations)
    check_identity_resolution(
        inputs,
        identity_roles or ["reference"],
        root,
        minimum,
        source,
        errors,
        unmeasured,
    )

    # What the submission declared, and not what was read from it. A list the
    # gate could not read has its own line above, and a second line saying none
    # was declared would be false.
    if not obligations.get("locks"):
        unmeasured.append("lock surfaces: the submission declares none")
    if not obligations.get("permanent_features"):
        unmeasured.append("permanent features: the submission declares none")

    return verdict(submission, profile, offering, errors, unmeasured)


def print_text(report: dict[str, Any], stream: Any = None) -> None:
    """The report as lines a person reads, with nothing the JSON carries left out."""

    stream = sys.stdout if stream is None else stream
    print(f"{report['status']}: {report['submission_id']} -> {report['target']}", file=stream)
    for item in report["errors"]:
        print(f"  refused  {item['code']}: {item['message']}", file=stream)
        if item.get("asks"):
            print(f"           asks for: {item['asks']}", file=stream)
    for item in report["unmeasured"]:
        print(f"  unmeasured  {item}", file=stream)
    for item in report.get("review_requirements") or []:
        print(f"  review  {item['id']} ({item['requires']}): {item['statement']}", file=stream)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refuse a submission with provable defects.",
        epilog="Write a submission skeleton with scripts/submission_draft.py new.",
    )
    parser.add_argument("submission", type=Path)
    parser.add_argument("--profiles", type=Path, action="append", default=[],
                        help="A target profile directory, such as the project's own; repeatable. "
                             "They are searched in order, and the suite's profiles last.")
    parser.add_argument("--root", type=Path, default=None,
                        help="The project root that relative paths resolve from. Defaults to the "
                             "directory holding the submission.")
    parser.add_argument("--json", action="store_true", help="Print the report and nothing else")
    args = parser.parse_args(argv)
    profiles = [*args.profiles, DEFAULT_PROFILES]

    # Three answers, three exit codes: 1 is a refusal, 2 is a submission that
    # could not be read, 3 is a gate that broke. A file that is not UTF-8 is the
    # second of those and not the third, and `UnicodeDecodeError` is a
    # `ValueError` rather than an `OSError`, so naming it is what keeps it out
    # of the traceback that escapes every handler here.
    try:
        submission = json.loads(args.submission.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        print(f"cannot read submission: {error}", file=sys.stderr)
        return 2

    root = args.root if args.root is not None else args.submission.resolve().parent
    try:
        report = gate(submission, profiles, root)
    except Exception:
        # A verdict and a crash are different answers, and a caller that gets
        # the same exit code for both cannot tell a refusal from a broken gate.
        traceback.print_exc()
        print("the gate did not finish, so nothing here is a verdict", file=sys.stderr)
        return 3
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)
    return 1 if report["status"] == "refused" else 0


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
