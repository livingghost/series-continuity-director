#!/usr/bin/env python3
"""Validate a Series Continuity Director project workspace."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_registry import check as check_registry, media_files  # noqa: E402
from state_protocol import validate_artifact as validate_state_artifact  # noqa: E402
from viewpoint_protocol import validate_artifact as validate_viewpoint_artifact  # noqa: E402
from project_layout import (  # noqa: E402
    ARTIFACT_JSON_ROOTS,
    CANONICAL_FILES,
    DEFAULT_VIEWPOINT_PROFILE,
    EPISODE_MEDIA_SUBDIRECTORIES,
    MEDIA_SUBDIRECTORIES,
    NARRATIVE_PROSE_DIRECTORIES,
    NARRATIVE_SUBDIRECTORIES,
    PROJECT_ID_RE,
    PROJECT_MANIFEST,
    PROJECT_MANIFEST_REQUIRED_FIELDS,
    PROJECT_PRODUCT,
    REQUIRED_PROJECT_FILES,
    STATE_SUBDIRECTORIES,
    WORK_DIRECTORY,
    read_document,
)
import report_output  # noqa: E402
import run_gallery  # noqa: E402
import work_ledger  # noqa: E402
FORBIDDEN_PUNCTUATION = {"\u2014": "Unicode em dash", "\u2013": "Unicode en dash"}

# Suffixes this validator opens as text. A project holds the media it produced,
# and a workspace built around video is measured in gigabytes: reading every file
# to find out whether it decodes reads the footage as well as the notes.
TEXT_SUFFIXES = {".md", ".markdown", ".json", ".jsonl", ".txt", ".toml", ".yaml", ".yml", ".csv"}

# Files this suite defines, as opposed to the writing the user keeps beside them.
# The punctuation rule binds the suite's own artifacts, because their text is
# copied into submissions and compared byte for byte. A dash in a scene note the
# user wrote is theirs to choose.
MANAGED_FILES = frozenset({*REQUIRED_PROJECT_FILES, "project-manifest.json"})
MANAGED_ROOTS = frozenset(ARTIFACT_JSON_ROOTS)

# The one document the narrative half hangs from, named from the layout rather
# than spelled again here, so the path this reports and the path initialization
# writes cannot drift apart.
NARRATIVE_FILE = CANONICAL_FILES["narrative"]


def is_managed(relative: Path) -> bool:
    posix = relative.as_posix()
    if posix in MANAGED_FILES:
        return True
    if not relative.parts or relative.parts[0] not in MANAGED_ROOTS:
        return False
    if any(posix.startswith(f"{prefix}/") for prefix in NARRATIVE_PROSE_DIRECTORIES):
        # The author's own writing, and the one file the suite ships beside it.
        return relative.suffix.lower() == ".json" or relative.name == "README.md"
    return True


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value


def emit(project: Path, errors: list[str], warnings: list[str], stats: dict[str, Any]) -> int:
    """Print the report with each problem once, in the order it was first found.

    The coverage report and the index read files this command also reads, and
    they word a shared problem the same way, so a repeat is dropped here.
    """

    errors = list(dict.fromkeys(errors))
    warnings = list(dict.fromkeys(warnings))
    report = {"ok": not errors, "project": str(project), "errors": errors, "warnings": warnings,
              "stats": stats, "generated_media_quality": "not evaluated"}
    report_output.emit(report)
    return 0 if not errors else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Series Continuity Director project")
    parser.add_argument("project")
    report_output.add_json_flag(parser)
    args = parser.parse_args()
    report_output.use_json(args.json)
    project = Path(args.project).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    stats: dict[str, Any] = {"state_artifacts": 0, "producer_artifacts": 0, "viewpoint_artifacts": 0, "events": 0, "text_files": 0}

    # A mistyped path is one problem, not one per file the layout expects.
    if not project.is_dir():
        return emit(project, [f"no project at {project}: the directory does not exist"], [], stats)
    if not (project / PROJECT_MANIFEST).is_file():
        return emit(project, [
            f"{project} is not a project: it has no {PROJECT_MANIFEST}. "
            f"{ROOT / 'scripts' / 'init_project.py'} creates one"], [], stats)

    for rel in REQUIRED_PROJECT_FILES:
        if not (project / rel).is_file():
            errors.append(f"missing required file: {rel}")

    for name in STATE_SUBDIRECTORIES:
        rel = f"state/{name}"
        if not (project / rel).is_dir():
            errors.append(f"missing required directory: {rel}")

    # The narrative directories are part of the layout, required like the rest.
    for name in NARRATIVE_SUBDIRECTORIES:
        rel = f"narrative/{name}"
        if not (project / rel).is_dir():
            errors.append(f"missing required directory: {rel}")

    for name in MEDIA_SUBDIRECTORIES:
        rel = f"media/{name}"
        if not (project / rel).is_dir():
            errors.append(f"missing required directory: {rel}")

    # The open task and the trail of tasks. A project without them cannot tell a
    # session that lost its context what it was doing.
    if not (project / WORK_DIRECTORY).is_dir():
        errors.append(f"missing required directory: {WORK_DIRECTORY}")
    else:
        errors.extend(work_ledger.check(project))

    # The run gallery is written by init_project.py and by every dispatch, so one
    # that does not match the run records means a record was written some other way.
    stale = run_gallery.stale(project)
    if stale:
        errors.append(f"{stale}; scripts/run_gallery.py rewrites it")

    # An episode directory holds only the four stages plus the cut. A media file
    # dropped somewhere else under an episode has no stage, and a reader arriving
    # later cannot tell a proposed frame from a returned take from the one take
    # that was accepted. Character and location media sit outside every episode
    # because they outlive all of them.
    episodes = project / "media" / "episodes"
    if episodes.is_dir():
        for episode in sorted(p for p in episodes.iterdir() if p.is_dir()):
            unknown = sorted(
                child.name
                for child in episode.iterdir()
                if child.is_dir() and child.name not in EPISODE_MEDIA_SUBDIRECTORIES
            )
            for name in unknown:
                errors.append(
                    f"media/episodes/{episode.name}/{name} is not one of the episode stages "
                    f"{', '.join(EPISODE_MEDIA_SUBDIRECTORIES)}"
                )

    manifest: dict[str, Any] = {}
    manifest_path = project / "project-manifest.json"
    if manifest_path.is_file():
        try:
            manifest = read_json(manifest_path)
        except Exception as exc:
            errors.append(f"{PROJECT_MANIFEST}: {exc}")
        missing = sorted(PROJECT_MANIFEST_REQUIRED_FIELDS - set(manifest))
        extra = sorted(set(manifest) - PROJECT_MANIFEST_REQUIRED_FIELDS)
        if missing:
            errors.append(f"project manifest missing fields: {missing}")
        if extra:
            errors.append(f"project manifest has unexpected fields: {extra}")
        if manifest.get("product") != PROJECT_PRODUCT:
            errors.append(f"project manifest product must be {PROJECT_PRODUCT}")
        series_id_value = manifest.get("series_id")
        if not isinstance(series_id_value, str) or not PROJECT_ID_RE.fullmatch(series_id_value):
            errors.append("project manifest series_id must use the canonical project ID format")
        for field in ("title", "created_at", "updated_at"):
            if not isinstance(manifest.get(field), str) or not manifest.get(field):
                errors.append(f"project manifest {field} must be a non-empty string")
        viewpoint = manifest.get("default_viewpoint_profile")
        if viewpoint is not None:
            if not isinstance(viewpoint, str) or not viewpoint.strip():
                errors.append("project viewpoint must name a selected profile or remain null")
            elif not (ROOT / "protocols/viewpoint/profiles" / (viewpoint + ".json")).is_file():
                errors.append("project viewpoint must name an installed profile")
        # The match is exact in both directions: a manifest that invents a
        # canonical file is refused, and so is one that drops any file the
        # current layout defines.
        if manifest.get("canonical_files") != CANONICAL_FILES:
            errors.append("project manifest canonical_files differs from the canonical project layout")

    # Every path this prints is POSIX and relative to the project, the form the
    # coverage report and the index print, so one problem reads the same in all.
    undecodable: set[Path] = set()
    for path in sorted(project.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(project)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"{relative.as_posix()}: carries a text suffix but is not UTF-8")
            undecodable.add(path)
            continue
        stats["text_files"] += 1
        if not is_managed(relative):
            continue
        for token, label in FORBIDDEN_PUNCTUATION.items():
            if token in text:
                errors.append(f"{relative.as_posix()}: contains {label}")

    events_path = project / "state/events.jsonl"
    if events_path.is_file():
        for line_number, raw in enumerate(events_path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError("state event must be a JSON object")
                report = validate_state_artifact(event)
                if not report.get("ok"):
                    errors.extend(f"state/events.jsonl:{line_number}: {message}" for message in report.get("errors", []))
                stats["events"] += 1
            except Exception as exc:
                errors.append(f"state/events.jsonl:{line_number}: {exc}")

    for path in sorted(project.rglob("*.json")):
        if path.name == PROJECT_MANIFEST or path in undecodable:
            continue
        relative = path.relative_to(project).as_posix()
        value, problem = read_document(path, relative)
        if problem:
            errors.append(problem)
            continue
        typed_root = relative.split("/")[0] in ARTIFACT_JSON_ROOTS
        if not isinstance(value, dict):
            # Outside the typed roots a JSON file is the project's own working
            # data, such as a list of reading applications, and only its syntax
            # is checked.
            if typed_root:
                errors.append(f"{relative}: JSON under a managed artifact directory must be an object with artifact_type")
            continue
        artifact_type = value.get("artifact_type")
        if not artifact_type:
            if typed_root:
                errors.append(
                    f"{relative}: JSON under a managed artifact directory requires artifact_type; "
                    "keep command inputs such as state requests under work/"
                )
            continue
        if artifact_type == "narrative":
            from narrative import validate_narrative

            report = validate_narrative(value)
            stats["narratives"] = stats.get("narratives", 0) + 1
            for notice in report.get("notices") or []:
                warnings.append(f"{relative}: {notice}")
            if report["ok"] and not report["approved"] and report["approval_errors"]:
                errors.append(
                    f"{relative}: the narrative's approval does not hold: "
                    + "; ".join(report["approval_errors"])
                )
            # A narrative still carrying what initialization put there is
            # structurally valid and says nothing, and is reported as a warning
            # rather than an error because a project is allowed to exist before
            # its story does. It is reported once, by `narrative_index.scan`,
            # which reads the blanks in narrative.json as well as the ones in
            # the files beside it, and whose gaps this extends into the warnings
            # below. The layout declares one narrative, at the path
            # CANONICAL_FILES names, and narrative_coverage and narrative_index
            # both open that one.
        elif artifact_type == "scene-plot":
            # The suite's own artifact, validated in code rather than by a protocol
            # schema, because it is not part of the interchange.
            from scene_plot import validate_scene_plot

            report = validate_scene_plot(value)
            stats["scene_plots"] = stats.get("scene_plots", 0) + 1
            if report["ok"] and not report["approved"] and report["approval_errors"]:
                errors.append(
                    f"{relative}: the scene plot's approval does not hold: "
                    + "; ".join(report["approval_errors"])
                )
        elif (ROOT / "protocols/shared-state/schemas" / f"{artifact_type}.schema.json").is_file():
            report = validate_state_artifact(value)
            stats["state_artifacts"] += 1
        elif (ROOT / "protocols/viewpoint/schemas" / f"{artifact_type}.schema.json").is_file():
            report = validate_viewpoint_artifact(value)
            stats["viewpoint_artifacts"] += 1
        else:
            if relative.split("/")[0] in ARTIFACT_JSON_ROOTS:
                errors.append(f"{relative}: unknown artifact_type {artifact_type!r}")
            else:
                # Whatever seals a visual-contract-package writes its own
                # artifacts beside the media it made. They are not this
                # suite's to validate, and they are not wrong for being here.
                stats["producer_artifacts"] += 1
            continue
        if not report.get("ok"):
            errors.extend(f"{relative}: {message}" for message in report.get("errors", []))
        artifact_series_id = value.get("series_id")
        if artifact_series_id is not None and artifact_series_id != manifest.get("series_id"):
            errors.append(f"{relative}: series_id does not match project manifest")

    # Confirm that the human-readable state files identify the same series.
    series_id = str(manifest.get("series_id") or "")
    if series_id:
        for rel in ("series-state.md", "character-profiles.md", "asset-registry.md",
                    "production-state.md"):
            path = project / rel
            if path.is_file() and re.search(rf"^series_id:\s*{re.escape(series_id)}\s*$", path.read_text(encoding="utf-8"), re.MULTILINE) is None:
                errors.append(f"{rel}: series_id does not match project manifest")

    # The narrative against the scenes meant to cover it. A plot approved against
    # a narrative that has since changed is approved against a document that no
    # longer exists, and no single-artifact check can see it.
    narrative_path = project / "narrative" / "narrative.json"
    if narrative_path.is_file():
        from narrative_coverage import cover

        coverage = cover(narrative_path, project / "narrative" / "scenes", series=project)
        errors.extend(coverage["errors"])
        warnings.extend(coverage["gaps"])
        warnings.extend(coverage["notices"])
        stats["narrative_scenes"] = coverage["scenes"]

    # Both directions through the narrative directory: a file nothing names, and
    # a name with no file behind it. Neither is visible from inside one document.
    if (project / "narrative").is_dir():
        from narrative_index import scan as scan_narrative

        index = scan_narrative(project)
        errors.extend(index["errors"])
        warnings.extend(index["gaps"])
        stats["narrative_entities"] = index["counts"]

    # Asset authority. A role with two accepted assets, or an accepted asset
    # sitting on a superseded one, is a registry that cannot answer which file to
    # submit. Unrecorded media is a warning: the file exists and the record is
    # missing, which is recoverable, while a contradictory record is not.
    registry_path = project / "asset-registry.md"
    if registry_path.is_file():
        registry_errors, registry_warnings = check_registry(
            registry_path.read_text(encoding="utf-8"), media_files(project)
        )
        errors.extend(registry_errors)
        warnings.extend(registry_warnings)

    return emit(project, errors, warnings, stats)


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
