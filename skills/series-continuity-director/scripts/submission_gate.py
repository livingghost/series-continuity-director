#!/usr/bin/env python3
"""Validate source approvals, literal contracts, media inputs and request constraints.

The author or delegated reviewer assesses meaning against the recorded requirements.
See examples/submission-gate for synthetic requests and observed reports.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILES = ROOT / "protocols" / "target" / "profiles"

RULES = {'ROUTE_READING_INVALID': 'SUB-17', 'VISUAL_CONTINUITY_INVALID': 'SUB-18', 'LOCK_SURFACE_ABSENT': 'SUB-01', 'LOCK_SURFACE_GLUED': 'SUB-02', 'INPUT_MODE_CONFLICT': 'SUB-07', 'IDENTITY_REFERENCE_TOO_SMALL': 'SUB-08', 'SUBMISSION_KIND_UNDECLARED': 'SUB-15', 'SCENE_PLOT_MISSING': 'SUB-15', 'SCENE_PLOT_OUTSIDE_ROOT': 'SUB-15', 'SCENE_PLOT_INVALID': 'SUB-15', 'SCENE_PLOT_UNAPPROVED': 'SUB-15', 'SCENE_PLOT_EDITED_AFTER_APPROVAL': 'SUB-15', 'SCENE_ID_MISMATCH': 'SUB-15', 'SHOT_NOT_IN_SCENE_PLOT': 'SUB-15', 'CHARACTER_NOT_IN_SCENE': 'SUB-15', 'ASSET_CARRIES_SHOT_FIELDS': 'SUB-15', 'SCENE_PLOT_BEHIND_NARRATIVE': 'SUB-15', 'NARRATIVE_OUTSIDE_ROOT': 'SUB-16', 'NARRATIVE_INVALID': 'SUB-16', 'CHARACTER_NOT_IN_NARRATIVE': 'SUB-16', 'PROHIBITED_SURFACE': 'SUB-16', 'DURATION_NOT_INTEGER': 'SUB-09', 'DURATION_OUT_OF_BAND': 'SUB-09', 'SCHEMA_REFUSAL': 'SUB-10'}
# A submission carrying no text at all fails before any numbered rule applies,
# so it carries no id rather than an empty one: a reader of `rule` gets a rule
# or nothing, and never a third thing that has to be told apart from both.
UNNUMBERED = frozenset({"TEXT_MISSING"})


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




def load_profile(target: str, profiles_dir: Path) -> dict[str, Any] | None:
    for path in sorted(profiles_dir.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if value.get("target_id") == target or path.stem == target:
            return value
    return None


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


def check_scene_plot(submission: dict[str, Any], root: Path, errors: list[dict],
                     unmeasured: list[str]) -> None:
    """A shot belongs to a scene whose plot was approved before any wording.

    A scene proposition and a blocking table say what happens and where people
    stand; neither records which beat put a given thing in a given frame, and
    neither is agreed before the text exists. Without that stop the first thing
    anyone sees is a finished submission, and every correction after it is made
    one shot at a time.

    Not every submission is a shot. A reference-set image, a sheet panel, a
    location plate and a probe belong to no scene, so a submission says which it
    is. Saying nothing is refused rather than treated as the exempt case.
    """

    from scene_plot import validate_scene_plot

    if not isinstance(submission, dict):
        errors.append(finding(
            "SUBMISSION_KIND_UNDECLARED",
            "a submission is an object naming what it is and what it carries, and this is "
            f"{shape(submission)}",
        ))
        return
    kind = submission.get("kind")
    if kind not in ("shot", "asset"):
        errors.append(finding(
            "SUBMISSION_KIND_UNDECLARED",
            "the submission declares no 'kind': 'shot' for a shot of a scene, 'asset' for a "
            f"reference, a sheet panel, a plate or a probe, got {kind!r}",
        ))
        return
    if kind == "asset":
        # An asset belongs to no scene, so the plot rules do not apply to it.
        # That is also the way around them, and the way around is a lie the gate
        # cannot catch from the submission alone: nothing in a text says whether
        # it is a shot. What it can catch is the lie that forgot to tidy up, and
        # what it must not do is let the skipped rules pass in silence.
        shot_fields = sorted(
            name for name in ("scene_plot", "scene_id", "shot_id")
            if isinstance(submission.get(name), str) and submission[name].strip()
        )
        if shot_fields:
            errors.append(finding(
                "ASSET_CARRIES_SHOT_FIELDS",
                "the submission declares itself an asset and carries "
                + ", ".join(shot_fields)
                + ", which belong to a shot of a scene; an asset belongs to no scene",
                fields=shot_fields,
            ))
            return
        unmeasured.append(
            "scene plot: the submission declares itself an asset, so the rules about a scene "
            "plot, the shot it plans, and who is in the scene were not applied"
        )
        return

    declared = submission.get("scene_plot")
    if not isinstance(declared, str) or not declared.strip():
        errors.append(finding(
            "SCENE_PLOT_MISSING",
            "a shot is written from an approved scene plot; the submission carries its path as "
            "'scene_plot' and its own id as 'shot_id'",
        ))
        return
    candidate = Path(declared)
    if candidate.is_absolute() or ".." in candidate.parts:
        errors.append(finding(
            "SCENE_PLOT_OUTSIDE_ROOT",
            f"the scene plot path must stay inside the project: {declared}",
        ))
        return
    path = (root / candidate).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        errors.append(finding(
            "SCENE_PLOT_OUTSIDE_ROOT",
            f"the scene plot resolves outside the project: {declared}",
        ))
        return
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(finding("SCENE_PLOT_INVALID", f"the scene plot could not be read: {declared}: {exc}"))
        return

    report = validate_scene_plot(value)
    if not report["ok"]:
        shown = report["errors"]
        elided = len(report["errors"]) - len(shown)
        detail = "; ".join(shown) + (f"; and {elided} more" if elided else "")
        errors.append(finding("SCENE_PLOT_INVALID", f"the scene plot is invalid: {declared}: {detail}"))
        return
    if not report["approved"]:
        reason = "; ".join(report["approval_errors"]) or "it carries no approved block"
        code = (
            "SCENE_PLOT_EDITED_AFTER_APPROVAL"
            if any("changed after it was approved" in item for item in report["approval_errors"])
            else "SCENE_PLOT_UNAPPROVED"
        )
        errors.append(finding(code, f"the scene plot is not approved: {declared}: {reason}"))
        return

    scene_id = submission.get("scene_id")
    if isinstance(scene_id, str) and scene_id.strip() and scene_id != report["scene_id"]:
        errors.append(finding(
            "SCENE_ID_MISMATCH",
            f"the submission names scene {scene_id!r} and the plot covers {report['scene_id']!r}",
        ))
        return

    # A submission naming somebody the scene does not contain is a shot of a
    # different scene, or a plot that omits who was there. Either way the two
    # documents disagree and neither one is the answer.
    present = submission.get("characters")
    if isinstance(present, list):
        for who in present:
            if str(who) not in report["characters"]:
                errors.append(finding(
                    "CHARACTER_NOT_IN_SCENE",
                    f"the submission names character {who!r}, and the scene plot {declared} "
                    f"carries {report['characters']}",
                    character=str(who),
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
            except (OSError, json.JSONDecodeError) as exc:
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

    shot_id = submission.get("shot_id")
    if not isinstance(shot_id, str) or not shot_id.strip():
        errors.append(finding(
            "SHOT_NOT_IN_SCENE_PLOT",
            "the submission carries no 'shot_id', so it cannot be matched to a shot in the scene plot",
        ))
        return
    if shot_id not in report["shot_ids"]:
        realization = report["realization"]
        detail = (
            f"it carries {report['shot_ids']}"
            if realization == "shots"
            else f"the scene is realized as {realization}, which a shot is not one of"
        )
        errors.append(finding(
            "SHOT_NOT_IN_SCENE_PLOT",
            f"shot {shot_id!r} is not in the approved scene plot {declared}; {detail}",
            shot_id=shot_id,
        ))


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
    errors: list[dict],
    unmeasured: list[str],
) -> None:
    """Compare the request keys this submission occupies against the profile.

    An input may name the request key it occupies. Where it does not, the role is
    matched against the modes the profile declares, and a role that more than one
    mode could hold is reported rather than charged. A submission carrying one
    reference is not carrying every reference channel the surface exposes, and
    refusing it for a conflict between two channels it never used would refuse a
    submission that is fine.
    """

    if profile is None:
        unmeasured.append("input mode exclusivity: no profile for the named target")
        return
    modes = [mode for mode in (profile.get("input_modes") or []) if mode.get("request_keys")]
    if not modes:
        unmeasured.append("input mode exclusivity: the profile declares no mode carrying a request key")
        return

    by_key = {key: mode for mode in modes for key in mode["request_keys"]}
    frame_roles = {"first_frame", "last_frame"}
    used: set[str] = set()

    for index, item in enumerate(inputs):
        if not isinstance(item, dict):
            unmeasured.append(
                f"input mode exclusivity: input {index} is not an object, so it names no "
                "request key"
            )
            continue
        declared = item.get("request_key")
        if declared is not None:
            if not isinstance(declared, str):
                unmeasured.append(
                    f"input mode exclusivity: input {index} names a request key that is not a "
                    f"name but {shape(declared)}, so the channel it occupies was not read"
                )
                continue
            if declared in by_key:
                used.add(declared)
            else:
                unmeasured.append(
                    f"input mode exclusivity: input {index} names request key {declared!r}, "
                    "which this profile does not record"
                )
            continue
        role = item.get("role", "reference")
        if not isinstance(role, str):
            unmeasured.append(
                f"input mode exclusivity: input {index} names a role that is not a name "
                f"but {shape(role)}, so the channel it occupies was not read"
            )
            continue
        wants_frame = role in frame_roles
        candidates = sorted({
            key
            for mode in modes
            if ("frame" in str(mode.get("mode", "")).lower()) == wants_frame
            for key in mode["request_keys"]
        })
        if len(candidates) == 1:
            used.add(candidates[0])
        elif not candidates:
            unmeasured.append(
                f"input mode exclusivity: the profile declares no mode that carries the role {role!r}"
            )
        else:
            unmeasured.append(
                f"input mode exclusivity: the role {role!r} could occupy any of {candidates}; "
                "name request_key on the input to settle it"
            )

    # One finding per excluded pair. The profile states an exclusion from both
    # sides, and reporting it twice says the submission has two problems.
    reported: set[tuple[str, str]] = set()
    outside: set[str] = set()
    for key in sorted(used):
        for excluded in by_key[key].get("excludes") or []:
            if excluded not in by_key:
                # The exclusion names something that is not an input, such as a
                # size setting. This gate reads inputs, so it cannot settle it.
                outside.add(excluded)
                continue
            if excluded not in used:
                continue
            pair = (min(key, excluded), max(key, excluded))
            if pair in reported:
                continue
            reported.add(pair)
            errors.append(finding(
                "INPUT_MODE_CONFLICT",
                f"the profile records that {pair[0]} excludes {pair[1]}, and this submission uses both",
                request_key=pair[0],
                excluded=pair[1],
            ))
    for excluded in sorted(outside):
        unmeasured.append(
            f"input mode exclusivity: a mode this submission uses excludes {excluded!r}, "
            "which is not an input and is not declared here"
        )


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


FACING = re.compile(
    r"\b(?:with\s+(?:his|her|their|its)\s+back\s+(?:turned|to)|back\s+turned|backs?\s+to\s+(?:the|us)|from\s+behind|"
    r"facing\s+away|turned\s+away|rear\s+view|back\s+view|seen\s+from\s+(?:behind|underneath))\b",
    re.IGNORECASE,
)




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


def select_offering(profile: dict[str, Any] | None, service: str | None, unmeasured: list[str]) -> dict[str, Any] | None:
    """The offering is the model as one service exposes it.

    A profile may list several; the submission names the service it will use. With
    one offering the choice is settled; with none, the mode-level request keys stand
    on their own.
    """

    if profile is None:
        return None
    offerings = [o for o in (profile.get("offerings") or []) if isinstance(o, dict)]
    if not offerings:
        return None
    if service:
        for offering in offerings:
            if offering.get("service") == service:
                return offering
        unmeasured.append(
            f"offering: the profile records no offering on service {service!r}; "
            f"it records {[o.get('service') for o in offerings]}"
        )
        return None
    if len(offerings) == 1:
        return offerings[0]
    unmeasured.append(
        "offering: the profile records several services "
        f"{[o.get('service') for o in offerings]} and the submission names none"
    )
    return None


def apply_offering(profile: dict[str, Any] | None, offering: dict[str, Any] | None) -> dict[str, Any] | None:
    """Request keys belong to the offering; the mode keeps its meaning."""

    if profile is None or offering is None or not offering.get("request_keys"):
        return profile
    keys = offering["request_keys"]
    modes = []
    for mode in profile.get("input_modes") or []:
        name = str(mode.get("mode", ""))
        if name in keys:
            modes.append({**mode, "request_keys": list(keys[name])})
        else:
            modes.append(mode)
    return {**profile, "input_modes": modes}


def check_parameters(parameters: dict[str, Any], offering: dict[str, Any] | None, media_kind: list[str], errors: list[dict], unmeasured: list[str]) -> None:
    """A limit the service enforces at submission is settled here instead.

    The duration band is the one such limit recorded so far. A submission that
    states its duration is checked against the band; one that does not state it
    on a video surface is reported, because the gate cannot check what it was not
    given.
    """

    constraints = (offering or {}).get("constraints") or {}
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


def build_instance(text: str, inputs: list[dict], parameters: dict[str, Any], offering: dict[str, Any]) -> dict[str, Any]:
    """The request as the service would see it, from what the submission declares."""

    instance: dict[str, Any] = {"model": offering.get("model_identifier"), "positivePrompt": text}
    for key, value in (parameters or {}).items():
        instance[key] = value
    media: dict[str, list[str]] = {}
    keys_by_mode = offering.get("request_keys") or {}
    for item in inputs:
        key = str(item.get("request_key") or "")
        if not key:
            # Resolve the role the way the input-mode check does: a frame role takes a
            # frame mode, any other role the single non-frame mode, if there is one.
            role = str(item.get("role", "reference"))
            wants_frame = role in ("first_frame", "last_frame")
            candidates = sorted({k for mode, ks in keys_by_mode.items() if ("frame" in mode.lower()) == wants_frame for k in ks})
            key = candidates[0] if len(candidates) == 1 else ""
        if key.startswith("inputs."):
            media.setdefault(key[len("inputs."):], []).append("00000000-0000-4000-8000-000000000000")
        elif key in ("seedImage", "maskImage"):
            instance.setdefault("inputs", {})[key] = "00000000-0000-4000-8000-000000000000"
        elif key:
            media.setdefault(key, []).append("00000000-0000-4000-8000-000000000000")
    if media:
        instance.setdefault("inputs", {}).update(media)
    return instance


def check_schema(text: str, inputs: list[dict], parameters: dict[str, Any] | None, offering: dict[str, Any] | None, root: Path, errors: list[dict], unmeasured: list[str]) -> None:
    """The service's own parameter schema, observed and stored, settles what it can."""

    if not offering or not offering.get("schema_snapshot"):
        unmeasured.append("parameter schema: the offering records no observed schema")
        return
    if parameters is None:
        unmeasured.append("parameter schema: the submission states no parameters, so the schema was not evaluated")
        return
    candidates = [Path(__file__).resolve().parents[1] / offering["schema_snapshot"], root / offering["schema_snapshot"]]
    path = next((c for c in candidates if c.is_file()), None)
    if path is None:
        unmeasured.append(f"parameter schema: {offering['schema_snapshot']} is not on disk")
        return
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        unmeasured.append(f"parameter schema: {path.name} did not load: {error}")
        return
    schema = snapshot.get("schema")
    if not isinstance(schema, dict):
        unmeasured.append(f"parameter schema: {path.name} carries no schema")
        return
    instance = build_instance(text, inputs, parameters or {}, offering)
    for violation in dict.fromkeys(schema_violations(instance, schema)):
        errors.append(finding("SCHEMA_REFUSAL", f"the service's parameter schema (observed {snapshot.get('observed_at', 'undated')}) refuses this request: {violation}", schema_rule=violation))


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






DIALECTS = {
    "parenthesis-colon": (r"\([^()]*:\s*\d+(?:\.\d+)?\s*\)", "(term:number)"),
    "compel": (r"\)\s*\d+(?:\.\d+)?|\w\+\+|\w--", "(term)number, term++ or term--"),
}






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


from execution_contract import content_id as c_visual_hash


def gate(submission: dict[str, Any], profiles_dir: Path, root: Path) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    unmeasured: list[str] = []

    # A submission is an object, and every check below reads a named field of
    # it. A string, a list or a number carries none, so asking one of them for
    # `text` raises where a gate has to refuse. The shot rules already state
    # what a submission is, so the refusal is theirs and the verdict is built
    # out of the nothing that is known about this document.
    if not isinstance(submission, dict):
        check_scene_plot(submission, root, errors, unmeasured)
        return {
            "gate": "submission",
            "submission_id": None,
            "target": None,
            "profile_found": False,
            "service": None,
            "offering_observed_at": None,
            "status": "refused",
            "errors": errors,
            "unmeasured": unmeasured,
        }

    from route_reading import require_route_reading
    try:
        require_route_reading(submission.get("route_reading"), project=root, routes={"media"})
    except (ValueError, OSError, TypeError, KeyError) as exc:
        errors.append(finding("ROUTE_READING_INVALID", str(exc)))
    text = submission.get("text")
    if not isinstance(text, str) or not text.strip():
        errors.append(finding("TEXT_MISSING", "the submission carries no model-facing text"))
        text = ""

    obligations = declared_mapping(submission.get("obligations"), "obligations", unmeasured) or {}
    locks = declared_phrases(obligations.get("locks"), "lock surfaces", unmeasured)
    features = declared_phrases(obligations.get("permanent_features"), "permanent features", unmeasured)
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
            "name, so neither the vocabulary nor the contradiction check read it"
        )
        text_form = None
    negative_text = submission.get("negative_text")
    if negative_text is not None and not isinstance(negative_text, str):
        unmeasured.append(
            f"negative text: the submission states {shape(negative_text)} rather "
            "than text, so it was not compared against the primary field"
        )
        negative_text = None
    # An input that is not an object names no role, no request key and no file.
    declared_inputs = submission.get("inputs") or []
    if not isinstance(declared_inputs, list):
        unmeasured.append("inputs: the submission does not carry a list of them")
        declared_inputs = []
    inputs = [item for item in declared_inputs if isinstance(item, dict)]
    for index, item in enumerate(declared_inputs):
        if not isinstance(item, dict):
            unmeasured.append(f"inputs[{index}] is not an object, so nothing about it was read")
    profile = load_profile(str(submission.get("target") or ""), profiles_dir)
    if profile is None and submission.get("target"):
        unmeasured.append(f"target profile {submission['target']!r} was not found in {profiles_dir}")

    import visual_continuity
    try:
        visual=submission.get('visual_continuity')
        if c_visual_hash(visual)!=submission.get('visual_continuity_sha256'):
            raise ValueError('visual continuity hash mismatch')
        continuity=visual_continuity.require(visual,submission=submission,root=root,profile=profile)
        unmeasured.extend(x['reason'] if isinstance(x,dict) else x for x in continuity['unmeasured'])
    except (ValueError,OSError,TypeError,KeyError) as exc:
        errors.append(finding('VISUAL_CONTINUITY_INVALID',str(exc)))
    check_scene_plot(submission, root, errors, unmeasured)
    check_prohibitions(submission, root, errors, unmeasured)
    check_locks(text, locks, errors)
    check_identity_carrier(inputs, obligations, unmeasured)
    offering = select_offering(profile, submission.get("service"), unmeasured)
    check_input_modes(inputs, apply_offering(profile, offering), errors, unmeasured)
    check_parameters(parameters or {}, offering, list((profile or {}).get("media_kind") or []), errors, unmeasured)
    check_schema(text, inputs, parameters, offering, root, errors, unmeasured)
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

    return {
        "gate": "submission",
        "submission_id": submission.get("submission_id"),
        "target": submission.get("target"),
        "profile_found": profile is not None,
        "service": (offering or {}).get("service") or submission.get("service"),
        "offering_observed_at": (offering or {}).get("observed_at"),
        "review_requirements": review_requirements(submission),
        "status": "refused" if errors else "admitted",
        "errors": errors,
        "unmeasured": unmeasured,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refuse a submission with provable defects.")
    parser.add_argument("submission", type=Path)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--root", type=Path, default=None,
                        help="Root for relative input paths. Defaults to the directory "
                             "holding the submission.")
    parser.add_argument("--json", action="store_true", help="Print the report and nothing else")
    args = parser.parse_args(argv)

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
        report = gate(submission, args.profiles, root)
    except Exception:
        # A verdict and a crash are different answers, and a caller that gets
        # the same exit code for both cannot tell a refusal from a broken gate.
        traceback.print_exc()
        print("the gate did not finish, so nothing here is a verdict", file=sys.stderr)
        return 3
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"{report['status']}: {report['submission_id']} -> {report['target']}")
        for item in report["errors"]:
            print(f"  refused  {item['code']}: {item['message']}")
        for item in report["unmeasured"]:
            print(f"  unmeasured  {item}")
    return 1 if report["status"] == "refused" else 0


if __name__ == "__main__":
    raise SystemExit(main())
