#!/usr/bin/env python3
"""Create a new Series Continuity Director project workspace."""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import run_gallery
from narrative import MEDIA
from project_layout import (
    CANONICAL_FILES,
    DEFAULT_VIEWPOINT_PROFILE,
    MEDIA_SUBDIRECTORIES,
    NARRATIVE_SUBDIRECTORIES,
    PROJECT_ID_RE,
    PROJECT_PRODUCT,
    STATE_SUBDIRECTORIES,
)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "assets" / "project-templates"

# Suffixes whose templates carry the series placeholders. `.jsonl` is excluded:
# the event ledger is copied byte for byte because it is append-only evidence and
# starts empty.
RENDERED_SUFFIXES = {".md", ".json"}


def render_text(source: Path, title: str, series_id: str, updated_at: str) -> str:
    return (source.read_text(encoding="utf-8")
            .replace("{{SERIES_TITLE}}", title)
            .replace("{{SERIES_ID}}", series_id)
            .replace("{{UPDATED_AT}}", updated_at))


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a Series Continuity Director project")
    parser.add_argument("--out", required=True, help="New project directory")
    parser.add_argument("--series-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--medium", choices=sorted(MEDIA), default="screen",
        help="What the series is made of, which decides what a scene of it becomes: "
             "shots, pages of panels, or passages of prose. Changing it later means editing narrative/narrative.json.",
    )
    parser.add_argument('--viewpoint', help='Explicit project viewpoint; omission leaves the choice open')
    args = parser.parse_args()
    if not args.title.strip() or any(ch in args.title for ch in '\r\n'):
        raise SystemExit('title must be nonempty single-line text')
    if args.viewpoint and not (ROOT/'protocols/viewpoint/profiles'/(args.viewpoint+'.json')).is_file():
        raise SystemExit('viewpoint must name an installed profile')

    if not PROJECT_ID_RE.fullmatch(args.series_id):
        raise SystemExit("series-id must be 2 to 64 ASCII letters, digits, dots, underscores, or hyphens")
    out = Path(args.out).resolve()
    if out.exists():
        raise SystemExit(f"output already exists: {out}")
    out.mkdir(parents=True)
    updated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    for source in sorted(TEMPLATES.rglob("*")):
        rel = source.relative_to(TEMPLATES)
        target = out / rel
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif source.suffix.lower() in RENDERED_SUFFIXES:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render_text(source, args.title, args.series_id, updated_at), encoding="utf-8", newline="\n")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    state_root = out / "state"
    for name in STATE_SUBDIRECTORIES:
        (state_root / name).mkdir(parents=True, exist_ok=True)

    narrative_root = out / "narrative"
    for name in NARRATIVE_SUBDIRECTORIES:
        (narrative_root / name).mkdir(parents=True, exist_ok=True)

    # The medium decides what a scene of this series becomes, and a project that
    # starts with the wrong one is refused the first time a scene is planned.
    document = narrative_root / "narrative.json"
    if document.is_file():
        value = json.loads(document.read_text(encoding="utf-8"))
        value["medium"] = args.medium
        document.write_text(json.dumps(value, ensure_ascii=False, indent=2) + chr(10),
                            encoding="utf-8", newline=chr(10))

    media_root = out / "media"
    for name in MEDIA_SUBDIRECTORIES:
        (media_root / name).mkdir(parents=True, exist_ok=True)

    manifest = {
        "product": PROJECT_PRODUCT,
        "series_id": args.series_id,
        "title": args.title,
        "created_at": updated_at,
        "updated_at": updated_at,
        "default_viewpoint_profile": args.viewpoint,
        "canonical_files": dict(CANONICAL_FILES),
    }
    (out / "project-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    # The run gallery exists from the start and follows every run from then on.
    run_gallery.write(out)
    print(json.dumps({"ok": True, "project": str(out), "series_id": args.series_id}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
