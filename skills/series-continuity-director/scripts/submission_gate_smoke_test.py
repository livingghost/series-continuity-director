#!/usr/bin/env python3
"""Check that the submission gate reaches the declared verdict on each fixture.

Every fixture is a real submission and carries the verdict it must receive, and a
refused one also carries the code that must appear. A fixture may also declare a
line that must appear in `unmeasured`, because a check that quietly stops running
leaves the status unchanged on the day it stops working.

The exclusivity rule is exercised separately, against a profile written here. No
shipped profile has two reference channels that exclude each other, and that is
the shape the rule has to survive: a submission carrying one reference occupies
one channel, and charging it with a conflict between two would refuse a
submission that is fine.

The rest of the cases are written here rather than as fixtures, for two reasons.
Some exercise a rule at the boundary that separates it from a looser reading of
it, and a submission admitted or refused identically under both readings proves
nothing about which is in force: the permanent feature head, the word boundary
a prohibited surface is searched on, and the code `finding` refuses to emit.
Each of those cases records the looser reading it refutes, and a case that
cannot tell the two apart is not a case for the rule it is filed under. The others hand the gate a submission no fixture
would be allowed to be: a field of the wrong shape, and a file that cannot be
read at all. What they fix is that a verdict is reached and the exit code says
which verdict it is, because a traceback is not a verdict.

One case reads no single report. The gate writes prose, and `check_report_language`
reads every line it wrote across every case above, because the defect that rule
exists for is not visible in any one verdict: a report is still correct about
which field it could not read while naming that field's shape in Python's word
for it rather than in the reader's.

No case here asserts the exact sentence the gate happens to write. An expectation
pinned to a sentence goes red when somebody improves the wording and stays green
when somebody deletes the check underneath it, which is the failure this file
exists to be the opposite of. Where a case has to look inside a line it looks for
a name it supplied itself -- a request key, a field, a character -- and never for
the gate's words around it.
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

from submission_gate import (  # noqa: E402
    check_permanent_features,
    finding,
    gate,
    image_size,
)

CASES = ROOT / "examples" / "submission-gate"
PROFILES = ROOT / "protocols" / "target" / "profiles"

# Every line the gate wrote during this run, with the case that drew it. A rule
# about the report's language is a rule about all of it, and a check that reads
# one case's report can only ever see the sentences that case happens to draw.
MESSAGES: list[tuple[str, str]] = []


def run_gate(case: str, submission: Any, profiles: Path, root: Path) -> dict:
    """Reach a verdict, and keep every line the gate wrote reaching it."""

    report = gate(submission, profiles, root)
    MESSAGES.extend((case, item["message"]) for item in report["errors"])
    MESSAGES.extend((case, line) for line in report["unmeasured"])
    return report


def names(line: str, name: str) -> bool:
    """Does this line name that thing, as a whole word rather than inside one?

    The things a case looks for are names it supplied to the gate itself: a
    request key, a field, an id. `parameters` must not be found inside `no
    parameters stated`'s neighbour `parameter schema`, and `input 0` must not be
    found inside `input 01`.
    """

    return re.search(rf"(?<![0-9A-Za-z]){re.escape(name)}(?![0-9A-Za-z])", line) is not None


def png(width: int, height: int) -> bytes:
    return (b"\x89PNG\r\n\x1a\n" + (13).to_bytes(4, "big") + b"IHDR"
            + width.to_bytes(4, "big") + height.to_bytes(4, "big"))


def jpeg(width: int, height: int) -> bytes:
    frame = (b"\x08" + height.to_bytes(2, "big") + width.to_bytes(2, "big")
             + b"\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01")
    return (b"\xff\xd8"
            + b"\xff\xe0" + (16).to_bytes(2, "big") + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            + b"\xff\xc0" + (len(frame) + 2).to_bytes(2, "big") + frame
            + b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\xff\xd9")


def gif(width: int, height: int) -> bytes:
    return (b"GIF89a" + width.to_bytes(2, "little") + height.to_bytes(2, "little")
            + b"\x00\x00\x00")


def bmp(width: int, height: int) -> bytes:
    return (b"BM" + (0).to_bytes(4, "little") + (0).to_bytes(4, "little")
            + (54).to_bytes(4, "little") + (40).to_bytes(4, "little")
            + width.to_bytes(4, "little", signed=True)
            # Stored top down, which a reader must take as a direction and not
            # as a negative height.
            + (-height).to_bytes(4, "little", signed=True)
            + b"\x01\x00\x18\x00" + bytes(24))


def webp_extended(width: int, height: int) -> bytes:
    body = (b"VP8X" + (10).to_bytes(4, "little") + b"\x00\x00\x00\x00"
            + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little"))
    return b"RIFF" + (len(body) + 4).to_bytes(4, "little") + b"WEBP" + body


def webp_lossy(width: int, height: int) -> bytes:
    body = (b"VP8 " + (14).to_bytes(4, "little") + b"\x00\x00\x00" + b"\x9d\x01\x2a"
            + width.to_bytes(2, "little") + height.to_bytes(2, "little") + b"\x00\x00")
    return b"RIFF" + (len(body) + 4).to_bytes(4, "little") + b"WEBP" + body


def webp_lossless(width: int, height: int) -> bytes:
    bits = (width - 1) | ((height - 1) << 14)
    body = (b"VP8L" + (10).to_bytes(4, "little") + b"\x2f"
            + bits.to_bytes(4, "little") + b"\x00\x00\x00\x00\x00")
    return b"RIFF" + (len(body) + 4).to_bytes(4, "little") + b"WEBP" + body


def tiff(width: int, height: int, order: str = "little") -> bytes:
    def word(value: int, size: int) -> bytes:
        return value.to_bytes(size, order)

    def entry(tag: int) -> bytes:
        value = width if tag == 256 else height
        return word(tag, 2) + word(4, 2) + word(1, 4) + word(value, 4)

    magic = b"II*\x00" if order == "little" else b"MM\x00*"
    return magic + word(8, 4) + word(2, 2) + entry(256) + entry(257) + word(0, 4)


IMAGE_CASES = [
    ("png", "png", png(640, 480)),
    ("jpeg", "jpg", jpeg(640, 480)),
    ("gif", "gif", gif(640, 480)),
    ("bmp stored top down", "bmp", bmp(640, 480)),
    ("webp extended", "webp", webp_extended(640, 480)),
    ("webp lossy", "webp", webp_lossy(640, 480)),
    ("webp lossless", "webp", webp_lossless(640, 480)),
    ("tiff little endian", "tif", tiff(640, 480)),
    ("tiff big endian", "tif", tiff(640, 480, "big")),
]

EXCLUSIVITY_PROFILE = {
    "target_id": "exclusivity-fixture",
    "input_modes": [
        {
            "mode": "reference images",
            "request_keys": ["inputs.referenceImages"],
            "excludes": ["inputs.referenceVideos"],
        },
        {
            "mode": "reference videos",
            "request_keys": ["inputs.referenceVideos"],
            "excludes": ["inputs.referenceImages"],
        },
    ],
}

EXCLUSIVITY_TEXT = (
    "The grey wolf stays asleep on the pillow. His upper ear rotates about thirty "
    "degrees toward the door and stops there."
)

IMAGE_KEY = {
    "role": "reference",
    "path": "fixtures/large.jpg",
    "request_key": "inputs.referenceImages",
}
VIDEO_KEY = {
    "role": "reference",
    "path": "fixtures/large.jpg",
    "request_key": "inputs.referenceVideos",
}

# A role the profile gives to more than one channel is reported and not charged,
# and what makes the report worth reading is that it says which channels those
# are: the reader's next move is to name one of them as `request_key`, and a line
# that only says the role is ambiguous does not tell them what to write. So the
# expectation is the keys, which this file handed the gate in the profile above,
# and not the sentence the gate puts them in.
# case name, inputs, expected status, names one unmeasured line must carry, expected conflicts
EXCLUSIVITY_CASES = [
    (
        "one reference, no request key",
        [{"role": "reference", "path": "fixtures/large.jpg"}],
        "admitted",
        ("inputs.referenceImages", "inputs.referenceVideos"),
        0,
    ),
    (
        "one reference naming its key",
        [IMAGE_KEY],
        "admitted",
        (),
        0,
    ),
    (
        "both channels named",
        [IMAGE_KEY, VIDEO_KEY],
        "refused",
        (),
        # The profile states the exclusion from both sides. One submission using
        # both channels has one problem, not two.
        1,
    ),
    (
        "a request key the profile does not record",
        [{
            "role": "reference",
            "path": "fixtures/large.jpg",
            "request_key": "inputs.somethingElse",
        }],
        "admitted",
        ("inputs.somethingElse",),
        0,
    ),
]


def check_fixtures(results: list[dict], errors: list[str]) -> None:
    for path in sorted(CASES.glob("*.json")):
        submission = json.loads(path.read_text(encoding="utf-8"))
        expected = submission.pop("expected_status", None)
        expected_code = submission.pop("expected_code", None)
        expected_unmeasured = submission.pop("expected_unmeasured", None)
        if expected is None:
            errors.append(f"{path.name}: fixture declares no expected_status")
            continue
        report = run_gate(f"fixture {path.stem}", submission, PROFILES, CASES)
        actual = report["status"]
        results.append({
            "case": path.stem,
            "expected": expected,
            "actual": actual,
            "codes": sorted({item["code"] for item in report["errors"]}),
            "unmeasured": len(report["unmeasured"]),
        })
        if actual != expected:
            errors.append(
                f"{path.stem}: expected {expected}, got {actual}"
                + (f" ({', '.join(item['code'] for item in report['errors'])})" if report["errors"] else "")
            )
        # The status alone is not enough. A refused fixture that is refused for
        # some other reason proves nothing about the check it was written for,
        # and a check that quietly degrades to unmeasured leaves the status
        # unchanged on the day it stops working.
        elif expected_code is not None:
            found = {item["code"] for item in report["errors"]}
            # Every refusal cites the rule it implements.
            unruled = sorted({item["code"] for item in report["errors"] if not item.get("rule")})
            if unruled:
                errors.append(f"{path.stem}: refusals cite no rule: {unruled}")
            if expected_code not in found:
                errors.append(
                    f"{path.stem}: refused, but not by {expected_code}; "
                    f"codes were {sorted(found) or 'none'}, unmeasured {report['unmeasured']}"
                )
        # `expected_unmeasured` is a substring of a sentence the gate writes, and
        # two fixtures declare one: `e01-lowres` asks for `could occupy any of`
        # and `asset-needs-no-plot` for `declares itself an asset`. That is the
        # defect this file was rewritten to remove, and it survives here because
        # the expectation lives in the fixture rather than in this file --
        # rewording either line turns the suite red while losing nothing a reader
        # needs, and deleting the check underneath would leave it green.
        # Whoever owns `examples/submission-gate/` should say what the line has
        # to carry rather than what it has to read: the request keys for the
        # first, and for the second that the scene rules were skipped and said to
        # be skipped.
        if expected_unmeasured is not None and not any(
            expected_unmeasured in item for item in report["unmeasured"]
        ):
            errors.append(
                f"{path.stem}: nothing in unmeasured carries {expected_unmeasured!r}; "
                f"unmeasured was {report['unmeasured']}"
            )


def check_exclusivity(results: list[dict], errors: list[str]) -> None:
    base = {
        "submission_id": "exclusivity",
        "kind": "shot",
        "scene_plot": "fixtures/scene-plot.json",
        "shot_id": "exclusivity",
        "narrative": "fixtures/narrative.json",
        "characters": ["C01"],
        "target": EXCLUSIVITY_PROFILE["target_id"],
        "text": EXCLUSIVITY_TEXT,
        "obligations": {"locks": [], "permanent_features": []},
    }
    with tempfile.TemporaryDirectory(prefix="scd-gate-profile-") as directory:
        profiles = Path(directory)
        (profiles / "exclusivity-fixture.json").write_text(
            json.dumps(EXCLUSIVITY_PROFILE, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="",
        )
        for name, inputs, expected, wanted, conflicts in EXCLUSIVITY_CASES:
            report = run_gate(f"exclusivity: {name}", {**base, "inputs": inputs}, profiles, CASES)
            found = [item for item in report["errors"] if item["code"] == "INPUT_MODE_CONFLICT"]
            results.append({
                "case": f"exclusivity: {name}",
                "expected": expected,
                "actual": report["status"],
                "codes": sorted({item["code"] for item in report["errors"]}),
                "unmeasured": len(report["unmeasured"]),
            })
            if report["status"] != expected:
                errors.append(
                    f"exclusivity {name!r}: expected {expected}, got {report['status']} "
                    f"({[item['message'] for item in report['errors']]})"
                )
            if len(found) != conflicts:
                errors.append(
                    f"exclusivity {name!r}: expected {conflicts} input mode conflicts, "
                    f"got {len(found)}: {[item['message'] for item in found]}"
                )
            if wanted and not any(
                all(names(item, key) for key in wanted) for item in report["unmeasured"]
            ):
                errors.append(
                    f"exclusivity {name!r}: expected one line of unmeasured to name "
                    f"{list(wanted)}, so a reader is told which key to write; unmeasured was "
                    f"{report['unmeasured']}"
                )


def check_resolution_floor(results: list[dict], errors: list[str]) -> None:
    """The pixel floor is declared, and the refusal says which declaration set it.

    A threshold nobody can see is a decision the gate made for the user. These
    cases fix where the number may come from and require the answer to name its
    source.
    """

    # fixtures/large.jpg is 1152 on its shorter side: below the explicitly declared floor, so the same file passes or fails on the declared number
    # alone.
    HIGH = 2048
    profile_with_floor = {
        "target_id": "floor-fixture",
        "identity_reference": {"minimum_shorter_side": HIGH},
    }
    profile_with_low_floor = {
        "target_id": "floor-fixture",
        "identity_reference": {"minimum_shorter_side": 64},
    }
    profile_without = {"target_id": "floor-fixture"}
    reference = {"role": "reference", "path": "fixtures/large.jpg"}
    base = {
        "submission_id": "floor",
        "kind": "shot",
        "scene_plot": "fixtures/scene-plot.json",
        "shot_id": "floor",
        "narrative": "fixtures/narrative.json",
        "characters": ["C01"],
        "target": "floor-fixture",
        "text": EXCLUSIVITY_TEXT,
        "inputs": [reference],
    }
    # The number is the rule and the source is the accounting for it. The last
    # two rows are the pair that needs both: a profile floor of HIGH against a
    # submission floor of 64, and a profile floor of 64 against a submission
    # floor of HIGH, refuse this file on the same number, and only `minimum_source`
    # says which declaration the gate took it from.
    # name, profile, obligations, expected status, the source cited, the number applied
    cases = [
        ("no declaration, no invented floor", profile_without, {}, "admitted",
         "no documented or operator-declared floor", None),
        ("the profile records a floor", profile_with_floor, {}, "refused",
         "the target profile", HIGH),
        (
            "the submission declares a floor",
            profile_without,
            {"identity_reference_minimum_shorter_side": HIGH},
            "refused",
            "this submission",
            HIGH,
        ),
        (
            "the submission raises a profile floor",
            profile_with_low_floor,
            {"identity_reference_minimum_shorter_side": HIGH},
            "refused",
            "this submission",
            HIGH,
        ),
        (
            "the submission cannot lower a profile floor",
            profile_with_floor,
            {"identity_reference_minimum_shorter_side": 64},
            "refused",
            "the target profile",
            HIGH,
        ),
    ]
    with tempfile.TemporaryDirectory(prefix="scd-gate-floor-") as directory:
        profiles = Path(directory)
        for name, profile, obligations, expected, source, minimum in cases:
            (profiles / "floor-fixture.json").write_text(
                json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8", newline="",
            )
            report = run_gate(f"floor: {name}", {**base, "obligations": obligations},
                              profiles, CASES)
            found = [item for item in report["errors"]
                     if item["code"] == "IDENTITY_REFERENCE_TOO_SMALL"]
            results.append({
                "case": f"floor: {name}",
                "expected": expected,
                "actual": report["status"],
                "codes": sorted({item["code"] for item in report["errors"]}),
                "unmeasured": len(report["unmeasured"]),
            })
            if report["status"] != expected:
                errors.append(
                    f"floor {name!r}: expected {expected}, got {report['status']} "
                    f"({[item['message'] for item in report['errors']]})"
                )
            if expected == "refused":
                if not found:
                    errors.append(f"floor {name!r}: expected a resolution refusal and got none")
                    continue
                if found[0].get("minimum") != minimum:
                    errors.append(
                        f"floor {name!r}: expected the floor applied to be {minimum}, got "
                        f"{found[0].get('minimum')}; the stricter of what the profile and the "
                        "submission declare is the one that stands"
                    )
                # Which declaration the number came from is an answer to a
                # question with three answers, carried as its own field so a
                # reader never has to parse it back out of the sentence.
                if found[0].get("minimum_source") != source:
                    errors.append(
                        f"floor {name!r}: expected the refusal to cite {source!r}, got "
                        f"{[item.get('minimum_source') for item in found]}"
                    )


def check_image_formats(results: list[dict], errors: list[str]) -> None:
    """Every still format the registry treats as media reports a real size.

    The resolution rule is the one check that reads a file rather than text, so a
    format it cannot open turns the rule off for that submission. It says so, but
    a project whose references are all in that format is left with a rule that
    never runs and a report that never refuses.
    """

    with tempfile.TemporaryDirectory(prefix="scd-gate-image-") as directory:
        base = Path(directory)
        for name, suffix, data in IMAGE_CASES:
            path = base / f"{name.replace(' ', '-')}.{suffix}"
            path.write_bytes(data)
            size = image_size(path)
            results.append({"case": f"image: {name}", "expected": "640x480",
                            "actual": "unreadable" if size is None else f"{size[0]}x{size[1]}"})
            if size != (640, 480):
                errors.append(f"image {name!r}: expected 640x480, read {size}")

        # A file that is not a still is not measured, and the gate must say so
        # rather than inventing a size for it.
        other = base / "not-an-image.bin"
        other.write_bytes(b"\x00\x01\x02\x03" * 16)
        results.append({"case": "image: an unrecognized file", "expected": "unreadable",
                        "actual": "unreadable" if image_size(other) is None else "read"})
        if image_size(other) is not None:
            errors.append("an unrecognized file was given a size")


# SUB-05 asks the text for the head of the declared phrase. Three looser rules
# reach the same verdict on most submissions, so each case below says which of
# them it is here to refute:
#   any    a rule matching any word of the feature admits this one wrongly
#   last   a rule matching the last word of the feature refuses this one wrongly
#   stem   a rule comparing whole words rather than stems refuses this one wrongly
# feature, text, verdict, what it refutes
PERMANENT_FEATURE_CASES = [
    ("one long bushy tail", "The wolf walks down a long corridor at dawn.", "refused", "any"),
    ("two white forepaws", "A white wall stands behind him.", "refused", "any"),
    ("a white patch on the chest", "His chest is turned away from the window.", "refused", "any, last"),
    ("a tail with a white tip", "His tail curls around the chair leg.", "named", "last"),
    ("six fins along the spine", "Six fins stand up as he turns.", "named", "last"),
    ("a notch in the right ear", "He stands at the right of the door.", "refused", "any"),
    ("a scar across the left cheek", "The scar runs from brow to jaw.", "named", "last"),
    ("upright triangular ears", "His upper ear rotates toward the door.", "named", "stem"),
    ("rounded ears", "He has rounded ears and one long striped tail.", "named", "nothing; the fixture case"),
]


def check_permanent_feature_head(results: list[dict], errors: list[str]) -> None:
    """SUB-05 reads the head of the declared phrase, not a word of it.

    An English noun phrase puts its head before its complement. Asking for any
    word admits `one long bushy tail` on `a long corridor at dawn`; asking for
    the last word refuses a text that names the tail, the patch and the fins
    while the declaration named the tip, the chest and the spine. Every case
    here separates the head rule from one of those two.
    """

    for feature, text, expected, refutes in PERMANENT_FEATURE_CASES:
        found: list[dict] = []
        check_permanent_features(text, [feature], found)
        MESSAGES.extend((f"permanent feature: {feature!r}", item["message"]) for item in found)
        actual = "refused" if found else "named"
        results.append({
            "case": f"permanent feature: {feature!r} against {text!r}",
            "expected": expected,
            "actual": actual,
            "refutes": refutes,
        })
        if actual != expected:
            errors.append(
                f"permanent feature {feature!r} against {text!r}: expected {expected}, "
                f"got {actual}; this case exists to refute the {refutes} rule"
            )


# The prohibition surface the shipped narrative fixture carries: once standing
# on its own, then each of the two ways a longer word can swallow it.
# name, text, how many PROHIBITED_SURFACE refusals it must draw
PROHIBITION_CASES = [
    (
        "the surface stands on its own",
        "The badger stands at the bench. He adds that he will never say this out loud.",
        1,
    ),
    (
        "a longer word ends with it",
        "The badger stands at the bench. He adds that he will saynever say this out loud.",
        0,
    ),
    (
        "a longer word begins with it",
        "The badger stands at the bench. He adds that he will never say thistles out loud.",
        0,
    ),
]


def check_prohibition_boundary(results: list[dict], errors: list[str]) -> None:
    """A prohibited phrase inside a longer word is not the phrase.

    SUB-16 searches on a word boundary, the way the lock check in the same file
    does. The shipped fixture carries the surface as a free-standing phrase, so
    it is refused with or without the boundary; only a text that glues the
    surface to a longer word tells the two searches apart.
    """

    base = {
        "submission_id": "prohibition-boundary",
        "kind": "asset",
        "target": "xai-grok-imagine-2",
        "narrative": "fixtures/narrative.json",
        "characters": ["C01"],
        "obligations": {},
    }
    for name, text, expected in PROHIBITION_CASES:
        report = run_gate(f"prohibition boundary: {name}", {**base, "text": text}, PROFILES, CASES)
        found = [item for item in report["errors"] if item["code"] == "PROHIBITED_SURFACE"]
        results.append({
            "case": f"prohibition boundary: {name}",
            "expected": f"{expected} prohibited surface",
            "actual": f"{len(found)} prohibited surface",
        })
        if len(found) != expected:
            errors.append(
                f"prohibition boundary {name!r}: expected {expected} PROHIBITED_SURFACE "
                f"refusal(s), got {len(found)}: {[item['message'] for item in found]}"
            )


# A submission is a project file, and a project file is untrusted data. Each row
# is a field given a shape it is not, and three things have to be true of every
# one of them. None of the three is a sentence the gate happens to write.
#
#   It reaches a verdict rather than raising. A traceback is not a verdict, and
#   a caller cannot tell one from a refusal.
#
#   The report names the field it could not read, once. A reader told only that
#   something was unreadable is left to diff the document against the schema,
#   and a field reported twice says the submission has two problems: the gate
#   holds back its `declares none` line for exactly that reason, and until now
#   nothing checked that it did.
#
#   The value is dropped rather than walked, which is the column that costs
#   something to satisfy. `"black boxer briefs"` iterates, so a lock loop
#   written for a list walks it one character at a time and refuses the
#   submission eighteen times over surfaces nobody declared. Every row states
#   the codes the submission earns in full, and each of these earns exactly one:
#   it declares no kind. A code beyond that list is the gate having read a value
#   it reported it could not read.
#
# Between them the rows hand the gate every shape a JSON document can put in the
# wrong place -- a piece of text, a number, a true/false, a list, a block of
# named fields -- because a report is only as good as its worst branch, and the
# loop at the end of the check adds the sixth, a document that is nothing at all.
# name, submission, expected status, the field the report must name, the codes it must cite
UNTRUSTED_CASES = [
    (
        "obligations is a string",
        {"obligations": "none"},
        "refused",
        "obligations",
        ["SUBMISSION_KIND_UNDECLARED"],
    ),
    (
        "a lock list given as one string",
        {"obligations": {"locks": "black boxer briefs"}},
        "refused",
        "lock surfaces",
        # Not eighteen LOCK_SURFACE_ABSENT refusals, one per character.
        ["SUBMISSION_KIND_UNDECLARED"],
    ),
    (
        "a lock list given as a block of named fields",
        {"obligations": {"locks": {"chest": "black boxer briefs"}}},
        "refused",
        "lock surfaces",
        ["SUBMISSION_KIND_UNDECLARED"],
    ),
    (
        "a lock list holding something that is not a phrase",
        {"obligations": {"locks": ["black boxer briefs", 7]}},
        "refused",
        "lock surfaces",
        # The phrase in the list is still checked, and the entry that is not a
        # phrase is dropped instead of being searched for as one.
        ["LOCK_SURFACE_ABSENT", "SUBMISSION_KIND_UNDECLARED"],
    ),
    (
        "permanent features given as a number",
        {"obligations": {"permanent_features": 42}},
        "refused",
        "permanent features",
        ["SUBMISSION_KIND_UNDECLARED"],
    ),
    (
        "permanent features given as true",
        {"obligations": {"permanent_features": True}},
        "refused",
        "permanent features",
        ["SUBMISSION_KIND_UNDECLARED"],
    ),
    (
        "parameters given as a list",
        {"parameters": ["duration", 6]},
        "refused",
        "parameters",
        ["SUBMISSION_KIND_UNDECLARED"],
    ),
    (
        "text form given as a number",
        {"text_form": 1},
        "refused",
        "text form",
        ["SUBMISSION_KIND_UNDECLARED"],
    ),
    (
        "negative text given as a list",
        {"negative_text": ["a mug"]},
        "refused",
        "negative text",
        ["SUBMISSION_KIND_UNDECLARED"],
    ),
    (
        "an input whose role is a list",
        {"target": "xai-grok-imagine-2",
         "inputs": [{"role": ["reference"], "path": "fixtures/large.jpg"}]},
        "refused",
        "input 0",
        ["SUBMISSION_KIND_UNDECLARED"],
    ),
    (
        "an input whose request key is a number",
        {"target": "xai-grok-imagine-2",
         "inputs": [{"role": "reference", "request_key": 7}]},
        "refused",
        "input 0",
        ["SUBMISSION_KIND_UNDECLARED"],
    ),
]


def check_untrusted_fields(results: list[dict], errors: list[str]) -> None:
    """A field of the wrong shape is reported, dropped, and never raised.

    The submission is refused throughout these cases for a reason of its own:
    it declares no kind. What each case fixes is that the gate reached that
    verdict at all, said which field it could not read, and refused by nothing
    else, because a value reported as unread and then read anyway is the worse
    of the two failures: the report says the check did not run and the refusals
    say it did.
    """

    for name, overlay, expected, field, codes in UNTRUSTED_CASES:
        case = f"untrusted: {name}"
        try:
            report = run_gate(case, {"submission_id": "untrusted",
                                     "text": "a quiet room at dawn", **overlay},
                              PROFILES, CASES)
        except Exception as error:  # noqa: BLE001
            results.append({"case": case, "expected": expected,
                            "actual": f"raised {type(error).__name__}"})
            errors.append(f"untrusted {name!r}: the gate raised {type(error).__name__}: {error}")
            continue
        named = [line for line in report["unmeasured"] if names(line, field)]
        cited = sorted(item["code"] for item in report["errors"])
        results.append({"case": case, "expected": expected, "actual": report["status"],
                        "lines naming the field": len(named), "codes": cited})
        if report["status"] != expected:
            errors.append(f"untrusted {name!r}: expected {expected}, got {report['status']}")
        if len(named) != 1:
            errors.append(
                f"untrusted {name!r}: expected one line of unmeasured to name {field!r} and "
                f"found {len(named)}; unmeasured was {report['unmeasured']}"
            )
        if cited != sorted(codes):
            errors.append(
                f"untrusted {name!r}: expected the refusal to cite {sorted(codes)} and nothing "
                f"else, got {cited}; a code beyond that list is the gate reading a value it "
                "reported it could not read"
            )

    # A submission that is not an object at all. Every check reads a named
    # field, so this is the one case where there is nothing to read.
    for value in ("a string", ["a", "b"], 42, None, True):
        try:
            report = run_gate(f"untrusted: the submission is {type(value).__name__}",
                              value, PROFILES, CASES)
        except Exception as error:  # noqa: BLE001
            results.append({"case": f"untrusted: the submission is {type(value).__name__}",
                            "expected": "refused", "actual": f"raised {type(error).__name__}"})
            errors.append(
                f"untrusted submission {value!r}: the gate raised {type(error).__name__}: {error}")
            continue
        codes = {item["code"] for item in report["errors"]}
        results.append({"case": f"untrusted: the submission is {type(value).__name__}",
                        "expected": "refused", "actual": report["status"]})
        if report["status"] != "refused" or "SUBMISSION_KIND_UNDECLARED" not in codes:
            errors.append(
                f"untrusted submission {value!r}: expected a SUBMISSION_KIND_UNDECLARED "
                f"refusal, got {report['status']} with {sorted(codes)}"
            )


# A refusal, a submission that could not be read, and a gate that broke are
# three different answers. A caller that gets the same number for two of them
# cannot tell them apart, and the second is the one that escapes quietly: a file
# that is not UTF-8 raises where the JSON handler cannot see it.
# name, what to write, expected exit code
EXIT_CASES = [
    ("a refused submission", b'{"submission_id": "x", "text": "a quiet room at dawn"}', 1),
    ("bytes that are not UTF-8", '{"text": "café at dawn"}'.encode("latin-1"), 2),
    ("text that is not JSON", b"{not json at all", 2),
    ("no file at that path", None, 2),
]


def check_exit_codes(results: list[dict], errors: list[str]) -> None:
    """The command's exit code says which of the three answers this is.

    The third, a gate that broke, has no case here: it is the code reserved for
    a defect this file cannot write on purpose, and every document the cases
    above hand the gate is one it now reaches a verdict about.
    """

    from submission_gate import main as gate_main

    with tempfile.TemporaryDirectory(prefix="scd-gate-exit-") as directory:
        for name, data, expected in EXIT_CASES:
            path = Path(directory) / "submission.json"
            if data is None:
                path = Path(directory) / "no-such-submission.json"
            else:
                path.write_bytes(data)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                try:
                    actual: object = gate_main([str(path), "--json"])
                except Exception as error:  # noqa: BLE001
                    actual = f"raised {type(error).__name__}"
            results.append({"case": f"exit code: {name}", "expected": expected, "actual": actual})
            if actual != expected:
                errors.append(
                    f"exit code {name!r}: expected {expected}, got {actual}; "
                    f"stderr was {stderr.getvalue().strip()[:200]!r}"
                )


def check_finding_codes(results: list[dict], errors: list[str]) -> None:
    """A code no rule registers is a mistake in this file, and says so here.

    `finding` refuses an unregistered code rather than emitting a refusal that
    cites no rule, because a refusal nobody can argue against the written rule
    is the one thing this gate must not produce. Nothing else notices when that
    guard goes: every code in use is registered, so the guard only ever fires on
    a code added in a later edit.
    """

    cases = [
        ("an unregistered code", "A_CODE_NO_RULE_REGISTERS", "refused"),
        ("a numbered code", "LOCK_SURFACE_ABSENT", "SUB-01"),
        ("the unnumbered code", "TEXT_MISSING", "no rule"),
    ]
    for name, code, expected in cases:
        try:
            item = finding(code, "a message")
        except KeyError:
            actual = "refused"
        else:
            actual = item.get("rule") or "no rule"
        results.append({"case": f"finding: {name}", "expected": expected, "actual": actual})
        if actual != expected:
            errors.append(f"finding {name!r} ({code}): expected {expected}, got {actual}")


# Python's word for a value's shape, where that word is not also the English
# noun. The list is chosen on that test alone, in both directions. `list` and
# `set` are deliberately absent: Python's name for those two is already the word
# a reader of the document would use, so there is no defect to catch there and
# banning them would ban the correct answer. `complex` is absent for the mirror
# reason: it is an ordinary English word, and no JSON document produces one, so
# banning it could only ever refuse a sentence that was fine. What is left are
# words no writer of a submission typed, each of them a word no English article
# agrees with. A message carries the submission's own wording as well as the
# gate's, so a word that is both a type name and ordinary English costs more
# here than it pays.
PYTHON_TYPE_NAMES = (
    "str", "int", "float", "bool", "dict", "tuple", "bytes", "bytearray",
    "frozenset", "NoneType",
)
TYPE_NAME = re.compile(
    r"(?<![0-9A-Za-z_])(?:" + "|".join(PYTHON_TYPE_NAMES) + r")(?![0-9A-Za-z_])")
# The other half of the same defect. `a` before a vowel is `a int`, `a object`,
# `a array`: the article was written for a noun the sentence no longer carries,
# which is what happens when a value is dropped into prose by its identifier.
DISAGREEING_ARTICLE = re.compile(r"(?<![0-9A-Za-z])a\s+(?=[aeiou])")


def check_report_language(results: list[dict], errors: list[str]) -> None:
    """No line the gate writes names a value's shape in Python's word for it.

    A gate that drops `type(value).__name__` into a sentence tells a submission
    carrying a number where a list goes that it carried `a int`, and a suite
    whose expectations are written against that text defends the defect:
    repairing the wording turns it red, and deleting the guard underneath leaves
    it green. This case is what makes that shape of defect visible.

    The rule is about the whole report and not about any one verdict, so it
    reads every line every case above drew. A report can be entirely right about
    which field it could not read and still be unreadable, and no check that
    looks at one submission's answer will ever see that.

    A line of this report is prose somebody reads. Two things are wrong with a
    type name in one, and both are looked for: the word is not one the writer of
    the submission used, and the article in front of it does not agree with it.
    """

    if not MESSAGES:
        errors.append("report language: no message was collected, so nothing was checked")
        return
    offences: list[tuple[str, str, str]] = []
    for case, message in MESSAGES:
        for found in TYPE_NAME.findall(message):
            offences.append((case, f"the Python name {found!r}", message))
        for found in DISAGREEING_ARTICLE.finditer(message):
            offences.append((case, f"'a' before a vowel at offset {found.start()}", message))
    results.append({
        "case": "report language: no Python type name where an English noun goes",
        "expected": "0 offences",
        "actual": f"{len(offences)} offences in {len(MESSAGES)} lines",
    })
    for case, what in dict.fromkeys((case, what) for case, what, _ in offences):
        line = next(message for c, w, message in offences if (c, w) == (case, what))
        errors.append(
            f"report language ({case}): {what} in a line a person reads: {line!r}"
        )


def main() -> int:
    results: list[dict] = []
    errors: list[str] = []

    check_fixtures(results, errors)
    fixtures = len(results)
    if fixtures < 9:
        errors.append(f"expected at least nine fixtures, found {fixtures}")
    check_exclusivity(results, errors)
    check_resolution_floor(results, errors)
    check_permanent_feature_head(results, errors)
    check_prohibition_boundary(results, errors)
    check_untrusted_fields(results, errors)
    check_exit_codes(results, errors)
    check_finding_codes(results, errors)
    check_image_formats(results, errors)
    # Last, because it reads what every case above made the gate write.
    check_report_language(results, errors)

    print(json.dumps({
        "ok": not errors,
        "checks": len(results),
        "fixtures": fixtures,
        "results": results,
        "errors": errors,
    }, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
