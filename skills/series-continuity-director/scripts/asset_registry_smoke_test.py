#!/usr/bin/env python3
"""Check that the registry reader reaches the declared verdict on each case.

Each case is a minimal registry plus the media list a project would present, and
it declares whether the reader must raise an error, a warning, or neither.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from asset_registry import check  # noqa: E402


def record(asset_id: str, role: str, status: str, path: str, derived: str = "") -> str:
    return (
        f"### {asset_id} - case asset\n"
        f"- type: scene media\n"
        f"- role: {role}\n"
        f"- status: {status}\n"
        f"- file: {path}\n"
        f"- derived from: {derived}\n"
    )


CASES = [
    {
        "name": "one accepted per role",
        "registry": record("S01", "e02-s01/start-frame", "accepted", "media/episodes/e02/frames/s01.jpg")
        + record("S02", "e02-s01/start-frame", "candidate", "media/episodes/e02/frames/s01-alt.jpg"),
        "media": ["media/episodes/e02/frames/s01.jpg", "media/episodes/e02/frames/s01-alt.jpg"],
        "errors": 0,
        "warnings": 0,
    },
    {
        "name": "two accepted for one role",
        "registry": record("S01", "e02-s01/start-frame", "accepted", "media/episodes/e02/frames/s01.jpg")
        + record("S02", "e02-s01/start-frame", "accepted", "media/episodes/e02/frames/s01-alt.jpg"),
        "media": ["media/episodes/e02/frames/s01.jpg", "media/episodes/e02/frames/s01-alt.jpg"],
        "errors": 1,
        "warnings": 0,
    },
    {
        "name": "accepted asset sitting on a superseded upstream",
        "registry": record("C01", "C01/identity", "superseded", "media/characters/c01-v1.jpg")
        + record("S01", "e02-s01/start-frame", "accepted", "media/episodes/e02/frames/s01.jpg", "C01"),
        "media": ["media/characters/c01-v1.jpg", "media/episodes/e02/frames/s01.jpg"],
        "errors": 1,
        "warnings": 0,
    },
    {
        "name": "the same asset marked stale instead",
        "registry": record("C01", "C01/identity", "superseded", "media/characters/c01-v1.jpg")
        + record("S01", "e02-s01/start-frame", "stale", "media/episodes/e02/frames/s01.jpg", "C01"),
        "media": ["media/characters/c01-v1.jpg", "media/episodes/e02/frames/s01.jpg"],
        "errors": 0,
        "warnings": 0,
    },
    {
        "name": "produced media with no record",
        "registry": record("S01", "e02-s01/start-frame", "accepted", "media/episodes/e02/frames/s01.jpg"),
        "media": ["media/episodes/e02/frames/s01.jpg", "media/episodes/e02/takes/s01-take1.mp4"],
        "errors": 0,
        "warnings": 1,
    },
    {
        "name": "a status outside the vocabulary",
        "registry": record("S01", "e02-s01/start-frame", "final", "media/episodes/e02/frames/s01.jpg"),
        "media": ["media/episodes/e02/frames/s01.jpg"],
        "errors": 1,
        "warnings": 0,
    },
    {
        "name": "a file with no role",
        "registry": record("S01", "", "accepted", "media/episodes/e02/frames/s01.jpg"),
        "media": ["media/episodes/e02/frames/s01.jpg"],
        "errors": 1,
        "warnings": 0,
    },
    {
        "name": "many unrecorded files collapse to a count",
        "registry": record("S01", "e02-s01/start-frame", "accepted", "media/episodes/e02/frames/s01.jpg"),
        "media": ["media/episodes/e02/frames/s01.jpg"]
                 + [f"media/episodes/e01/takes/t{n:02d}.mp4" for n in range(25)],
        "errors": 0,
        "warnings": 21,
    },
    {
        # The reader decides what counts as media on disk and what counts as a
        # file name inside a record. When those two answers come from different
        # lists, a correctly registered container is reported as unrecorded for
        # as long as the lists disagree.
        "name": "a container outside the image and audio suffixes",
        "registry": record("V01", "e02-s01/take", "accepted", "media/episodes/e02/takes/s01.webm"),
        "media": ["media/episodes/e02/takes/s01.webm"],
        "errors": 0,
        "warnings": 0,
    },
    {
        "name": "a file name that only ends with a recorded one",
        "registry": record("S01", "e02-s01/start-frame", "accepted", "s01.jpg"),
        "media": ["media/episodes/e02/frames/s01.jpg", "media/episodes/e02/frames/alt-s01.jpg"],
        "errors": 0,
        "warnings": 1,
    },
    {
        "name": "the shipped template on a new project",
        "registry": (ROOT / "assets/project-templates/asset-registry.md").read_text(encoding="utf-8"),
        "media": [],
        "errors": 0,
        "warnings": 0,
    },
]


def main() -> int:
    results: list[dict] = []
    failures: list[str] = []
    for case in CASES:
        errors, warnings = check(case["registry"], case["media"])
        results.append({
            "case": case["name"],
            "errors": len(errors),
            "warnings": len(warnings),
            "messages": errors + warnings,
        })
        if len(errors) != case["errors"] or len(warnings) != case["warnings"]:
            failures.append(
                f"{case['name']}: expected {case['errors']} errors and {case['warnings']} warnings, "
                f"got {len(errors)} and {len(warnings)}: {errors + warnings}"
            )

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
