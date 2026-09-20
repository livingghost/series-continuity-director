#!/usr/bin/env python3
"""Declare where things are, so a check cannot move with the mistake it is checking.

Two roots exist and they are not the same.

  SUITE  the skill: SKILL.md, references/, scripts/, protocols/, assets/,
         examples/, adapters/, agents/
  REPO   the repository, which is also the plugin root: README.md, LICENSE,
         CONTRIBUTING.md, CHANGELOG.md, package-manifest.toml, and the generated
         host files beside them

The lists below are stated, not computed from what is on disk. A declared member
that is absent is an error.

`REPO` is the nearest ancestor of `SUITE` holding `package-manifest.toml`. The
release archive mirrors the repository, so the walk gives the same answer in a
checkout and in an extracted release.
"""
from __future__ import annotations

from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]

# Files the repository owns. A host and a license scanner look for LICENSE at the
# root, and the manifest is the build definition for the whole tree.
REPO_FILES = (
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "package-manifest.toml",
)

# Files and directories the suite owns.
SUITE_FILES = ("SKILL.md",)
SUITE_DIRECTORIES = (
    "adapters",
    "agents",
    "assets",
    "config",
    "examples",
    "protocols",
    "references",
    "scripts",
)

MANIFEST_NAME = "package-manifest.toml"


def repository_root(suite: Path = SUITE) -> Path | None:
    """The nearest ancestor that holds the manifest, or None.

    None means the suite is not in a repository laid out this way. The caller
    decides whether that is an error or a case that does not apply.
    """

    for candidate in (suite, *suite.parents):
        if (candidate / MANIFEST_NAME).is_file():
            return candidate
    return None


def require_repository_root(suite: Path = SUITE) -> Path:
    root = repository_root(suite)
    if root is None:
        raise RuntimeError(
            f"no {MANIFEST_NAME} at or above {suite}; the suite is not in a repository "
            "laid out as this one is"
        )
    return root


def suite_root(repo: Path, manifest: dict) -> Path:
    return (repo / manifest["hosts"]["suite_root"]).resolve()


def check_layout(repo: Path, suite: Path = SUITE) -> list[str]:
    """Every declared member is where it is declared to be."""

    errors: list[str] = []
    for name in REPO_FILES:
        if not (repo / name).is_file():
            errors.append(f"missing repository file: {name}")
        if (suite / name).exists() and suite != repo:
            errors.append(f"{name} belongs to the repository, not to the suite: found in {suite.name}")
    for name in SUITE_FILES:
        if not (suite / name).is_file():
            errors.append(f"missing suite file: {name}")
    for name in SUITE_DIRECTORIES:
        if not (suite / name).is_dir():
            errors.append(f"missing suite directory: {name}")
    return errors


REPO = repository_root()
