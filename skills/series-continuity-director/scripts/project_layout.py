#!/usr/bin/env python3
"""Canonical project workspace layout shared by initialization and validation."""
from __future__ import annotations

import re

PROJECT_PRODUCT = "series-continuity-director"
DEFAULT_VIEWPOINT_PROFILE = None
PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]+$")

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
