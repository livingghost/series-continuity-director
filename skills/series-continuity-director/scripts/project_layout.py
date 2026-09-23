#!/usr/bin/env python3
"""Canonical project workspace layout shared by initialization and validation."""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

PROJECT_PRODUCT = "series-continuity-director"
PROJECT_MANIFEST = "project-manifest.json"
DEFAULT_VIEWPOINT_PROFILE = None
PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]+$")
# The installed suite. Project state written here would ship with the next copy
# of the suite and be read as the suite's own files.
SUITE = Path(__file__).resolve().parents[1]
INIT_COMMAND = f"{SUITE / 'scripts' / 'init_project.py'} --out <directory> --series-id <id> --title \"<title>\""

CANONICAL_FILES = {
    "series_state": "series-state.md",
    "character_profiles": "character-profiles.md",
    "asset_registry": "asset-registry.md",
    "production_state": "production-state.md",
    "event_ledger": "state/events.jsonl",
    "narrative": "narrative/narrative.json",
}

PROJECT_MANIFEST_REQUIRED_FIELDS = frozenset({
    "product",
    "series_id",
    "title",
    "created_at",
    "updated_at",
    "default_viewpoint_profile",
    "canonical_files",
})

ARTIFACT_JSON_ROOTS = ("state", "shots", "narrative")

STATE_SUBDIRECTORIES = (
    "processes",
    "snapshots",
    "scene-contexts",
    "visual-projections",
    "relationships",
    "wardrobe",
    "inventory",
    "reference-selections",
    "candidate-manifests",
    "external-contracts",
    "adoption-receipts",
    "observations",
)

NARRATIVE_SUBDIRECTORIES = (
    "design",
    "personas",
    "world/locations",
    "world/factions",
    "world/systems",
    "world/artifacts",
    "glossary",
    "scenes",
)

# Where the author's own writing lives. The punctuation rule binds artifacts whose
# text a submission copies byte for byte. A persona, a place, or a glossary entry
# is read by a person who then writes that text, so the dashes in it are the
# author's to choose. The README each of these directories ships is the suite's,
# and is bound like the rest of the suite's files.
NARRATIVE_PROSE_DIRECTORIES = (
    "narrative/design",
    "narrative/personas",
    "narrative/world",
    "narrative/glossary",
)

# What a freshly initialized narrative carries in place of a decision nobody has
# made yet is not declared here. `narrative_index.py` owns that list, beside the
# rules for where those words count and where a document is only quoting them,
# and the README the narrative directory ships names it as the reporter.

MEDIA_SUBDIRECTORIES = (
    "characters",
    "locations",
    "episodes",
)

# The open task and the trail of tasks, which `work_ledger.py` writes and a
# session reads before anything else.
WORK_DIRECTORY = "work"

EPISODE_MEDIA_SUBDIRECTORIES = (
    "frames",
    "prompts",
    "takes",
    "accepted",
    "edit",
)

REQUIRED_PROJECT_FILES = (
    "project-manifest.json",
    "series-state.md",
    "character-profiles.md",
    "asset-registry.md",
    "production-state.md",
    "state/events.jsonl",
    "narrative/narrative.json",
)


def inside_suite(path: Path) -> bool:
    """Whether a path is the installed suite or somewhere inside it."""

    resolved = path.resolve()
    return resolved == SUITE or SUITE in resolved.parents


def refuse_suite(path: Path) -> None:
    """Raise when a writer is pointed at the installed suite.

    SKILL.md keeps project state, run evidence and generated files out of the
    suite bundle, so every writer checks its destination here first.
    """

    if inside_suite(path):
        raise ValueError(
            f"{path.resolve()} is inside the installed suite at {SUITE}; a project lives "
            f"outside it. Create one with {INIT_COMMAND}"
        )


def require_project(path: Path) -> Path:
    """The resolved project directory a writer may write into, or ValueError saying why not."""

    resolved = path.resolve()
    refuse_suite(resolved)
    if not resolved.is_dir():
        raise ValueError(f"no project at {resolved}: the directory does not exist")
    manifest = resolved / PROJECT_MANIFEST
    if not manifest.is_file():
        raise ValueError(
            f"{resolved} is not a project: it has no {PROJECT_MANIFEST}. Pass --project with a "
            f"project directory, or create one with {INIT_COMMAND}"
        )
    try:
        value = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{PROJECT_MANIFEST} in {resolved} cannot be read: {exc}") from exc
    if not isinstance(value, dict) or value.get("product") != PROJECT_PRODUCT:
        raise ValueError(
            f"{resolved} is not a {PROJECT_PRODUCT} project: its {PROJECT_MANIFEST} names "
            f"product {value.get('product') if isinstance(value, dict) else None!r}"
        )
    return resolved


def shown(path: Path, root: Path | None) -> str:
    """A path as every report prints it: POSIX and relative to the project when inside it."""

    if root is not None:
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            pass
    return path.as_posix()


def read_document(path: Path, label: str) -> tuple[Any, str | None]:
    """Read one JSON document, or return the one message every reader prints for it.

    Three readers open the same files. Each once worded its own failure, so one
    syntax error arrived three times in three path styles. They share this, and
    a report that merges theirs keeps one copy.
    """

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None, f"{label}: carries a text suffix but is not UTF-8"
    except OSError as exc:
        return None, f"{label}: could not be read: {exc.strerror or exc}"
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, f"{label}: not valid JSON: {exc}"


def write_json(path: Path, value: Any) -> None:
    """Replace a JSON document in one step, so a reader never sees half of it."""

    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    descriptor, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def state_directory_paths() -> tuple[str, ...]:
    return tuple(f"state/{name}" for name in STATE_SUBDIRECTORIES)


def narrative_directory_paths() -> tuple[str, ...]:
    """Where the story itself lives, as against the pictures of it.

    A persona says who a person is; `character-profiles.md` says what they
    look like, and the two drift the moment one file holds both. A place has
    facts that no image of it carries. A term used in two characters mouths
    belongs to neither of them. A scene plot is where the story meets the
    coverage, so it sits here rather than in the shot root.
    """

    return tuple(f"narrative/{name}" for name in NARRATIVE_SUBDIRECTORIES)


def media_directory_paths() -> tuple[str, ...]:
    return tuple(f"media/{name}" for name in MEDIA_SUBDIRECTORIES)


def episode_media_directory_paths(episode_id: str) -> tuple[str, ...]:
    """Where one episode's working media lives.

    Character and location media sit outside every episode because they outlive
    all of them: a face does not change when the story moves to another morning,
    and a room reshot per episode stops being the same room. An episode owns only
    what it made, and it owns it in four stages, so an arriving reader can tell a
    proposed frame from a returned take from the one take that was accepted,
    without knowing what happened in the session that produced them.
    """

    return tuple(f"media/episodes/{episode_id}/{name}" for name in EPISODE_MEDIA_SUBDIRECTORIES)
