#!/usr/bin/env python3
"""Build the state a scene's shots stand on, and bind each shot's records to it.

One chain file names what the author wrote: the approved scene plot, the story
point, the world-state base, the scene-context request, each character's
contracts and state schema, and for each shot its camera, shot projection,
request and one projection request per character the shot shows. The command
then runs the state commands in their order:

1. `resolve-world` at the story point, with the scene's id as the scene context;
2. `extract-character` for each character;
3. `build-context` from the scene-context request;
4. `build-projection` for each character of each shot;
5. the camera, the shot projection and the request of each shot, with every
   hash they bind written in and each sealed;
6. the complete binding check `shot_request.py --require-complete` runs.

It writes the derived state under `state/` and rewrites the three records of
each shot sealed. The chain file itself is a working input, kept under `work/`.

    python scripts/shot_chain.py --project PROJECT work/state-inputs/SC01.chain.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import execution_contract as c
import report_output
from project_layout import require_project, write_json
from protocol_contract import artifact_hash, finalize_artifact, validate_artifact

CHAIN_FIELDS = {"scene_plot", "timeline_id", "story_order", "story_time", "world_base", "events",
                "processes", "scene_context_request", "characters", "shots"}
CHARACTER_FIELDS = {"species_profile", "individual_morphology", "identity_contract", "state_schema"}
SHOT_FIELDS = {"camera", "projection", "request", "character_projections"}
EXAMPLE = "work/state-inputs/SC01.chain.json"


def exact(value: Any, expected: set[str], label: str, optional: set[str] = frozenset()) -> dict:
    """An object with exactly the named fields, naming what is missing and what is extra."""
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object with {', '.join(sorted(expected))}")
    lacking = sorted(expected - optional - set(value))
    extra = sorted(set(value) - expected)
    if lacking or extra:
        parts = ([f"missing {', '.join(lacking)}"] if lacking else []) + ([f"unexpected {', '.join(extra)}"] if extra else [])
        raise ValueError(f"{label}: {'; '.join(parts)}")
    return value


def sealed(value: dict, label: str) -> dict:
    """The record sealed with its canonical hash, refused with the schema's reasons."""
    result = finalize_artifact(value)
    report = validate_artifact(result)
    if not report["ok"]:
        raise ValueError(f"{label} is invalid: " + "; ".join(report["errors"]))
    return result


def artifact(root: Path, path: str, kind: str, label: str, *, valid: bool = False) -> dict:
    """A project file holding one artifact of the expected type, valid as it stands when asked.

    A shot record is sealed here, so only its type is checked before that.
    """
    value = c.load(c.local(root, path))
    if not isinstance(value, dict) or value.get("artifact_type") != kind:
        raise ValueError(f"{label} {path} must be a {kind}, and it is "
                         f"{value.get('artifact_type') if isinstance(value, dict) else type(value).__name__!r}")
    if valid:
        report = validate_artifact(value)
        if not report["ok"]:
            raise ValueError(f"{label} {path} is invalid: " + "; ".join(report["errors"]))
    return value


def read_chain(root: Path, chain_path: Path) -> dict:
    chain = exact(c.load(chain_path), CHAIN_FIELDS, "the chain file", optional={"events", "processes"})
    for key in ("timeline_id", "story_time"):
        c.text(chain[key], key)
    if type(chain["story_order"]) is not int:
        raise ValueError(f"story_order must be an integer, got {chain['story_order']!r}")
    if not isinstance(chain["characters"], dict) or not chain["characters"]:
        raise ValueError("characters must name each character of the scene with its contracts")
    for ident, entry in chain["characters"].items():
        exact(entry, CHARACTER_FIELDS, f"characters.{ident}")
    if not isinstance(chain["shots"], dict) or not chain["shots"]:
        raise ValueError("shots must name at least one shot with its camera, projection and request")
    for ident, entry in chain["shots"].items():
        exact(entry, SHOT_FIELDS, f"shots.{ident}")
        people = entry["character_projections"]
        if not isinstance(people, dict) or not people:
            raise ValueError(f"shots.{ident}.character_projections must name one projection request per character shown")
        unknown = sorted(set(people) - set(chain["characters"]))
        if unknown:
            raise ValueError(f"shots.{ident} shows {unknown}, which the chain's characters do not name")
    return chain


def scene_of(root: Path, chain: dict) -> tuple[dict, dict]:
    """The approved plot the shots belong to, checked against the chain."""
    from scene_plot import validate_scene_plot
    plot = c.load(c.local(root, chain["scene_plot"]))
    report = validate_scene_plot(plot)
    if not report["ok"] or not report["approved"]:
        reasons = report["errors"] or report.get("approval_errors") or ["it carries no approval"]
        raise ValueError(f"the scene plot {chain['scene_plot']} is not approved: " + "; ".join(reasons))
    if report["realization"] != "shots":
        raise ValueError(f"the scene plot is realized as {report['realization']}, and only shots have cameras")
    missing = sorted(set(chain["shots"]) - set(report["shot_ids"]))
    if missing:
        raise ValueError(f"the scene plot declares shots {report['shot_ids']}, not {missing}")
    absent = sorted(set(chain["characters"]) - set(plot.get("characters") or []))
    if absent:
        raise ValueError(f"the scene plot's characters are {plot.get('characters')}, not {absent}")
    return plot, report


def build(root: Path, chain: dict) -> tuple[list[tuple[Path, dict]], dict]:
    """Every record the chain derives, with the path it is written to."""
    from state_protocol import (build_projection, build_scene_context, extract_character_snapshot,
                                load_jsonl, parse_processes, resolve_world)

    plot, report = scene_of(root, chain)
    scene, order, timeline = report["scene_id"], chain["story_order"], chain["timeline_id"]
    people = {ident: {name: artifact(root, entry[name], kind, f"characters.{ident}.{name}", valid=True)
                      for name, kind in (("species_profile", "species-morphology-profile"),
                                         ("individual_morphology", "individual-morphology-contract"),
                                         ("identity_contract", "character-identity-contract"),
                                         ("state_schema", "character-state-schema"))}
              for ident, entry in chain["characters"].items()}
    written: list[tuple[Path, dict]] = []

    world = sealed(resolve_world(
        base_state=c.load(c.local(root, chain["world_base"])),
        events=load_jsonl(c.local(root, chain.get("events") or "state/events.jsonl")),
        processes=parse_processes(str(c.local(root, chain["processes"])) if chain.get("processes") else None),
        timeline_id=timeline, story_order=order, story_time=chain["story_time"],
        snapshot_id=f"{scene}-{order}-world", scene_context_id=scene,
        character_state_schemas=[people[ident]["state_schema"] for ident in people]), "the world snapshot")
    written.append((root / "state" / "snapshots" / f"{scene}-{order}-world.json", world))

    states: dict[str, dict] = {}
    for ident, record in people.items():
        states[ident] = sealed(extract_character_snapshot(
            world, character_id=ident,
            species_profile_hash=artifact_hash(record["species_profile"]),
            individual_morphology_hash=artifact_hash(record["individual_morphology"]),
            identity_hash=artifact_hash(record["identity_contract"]),
            era_hash=None, form_hash=None, appearance_hash=None,
            snapshot_id=f"{scene}-{order}-{ident}"), f"the state snapshot of {ident}")
        written.append((root / "state" / "snapshots" / f"{scene}-{order}-{ident}.json", states[ident]))

    request = c.load(c.local(root, chain["scene_context_request"]))
    if request.get("scene_context_id") != scene:
        raise ValueError(f"the scene-context request names scene_context_id {request.get('scene_context_id')!r}; "
                         f"a scene context takes its scene's id, {scene!r}")
    context = sealed(build_scene_context(request, world, list(states.values())), "the scene context")
    written.append((root / "state" / "scene-contexts" / f"{scene}-{order}.json", context))

    for shot, entry in chain["shots"].items():
        shown = list(entry["character_projections"])
        for ident in shown:
            record = people[ident]
            projection = sealed(build_projection(
                record["identity_contract"], record["species_profile"], record["individual_morphology"],
                states[ident], context, c.load(c.local(root, entry["character_projections"][ident])), None),
                f"the visual state projection of {ident} in {shot}")
            written.append((root / "state" / "visual-projections" / f"{scene}-{shot}-{ident}.json", projection))

        state_map = {ident: artifact_hash(states[ident]) for ident in shown}
        camera = artifact(root, entry["camera"], "shot-camera-spec", f"shots.{shot}.camera")
        for key, expected in (("scene_id", scene), ("shot_id", shot)):
            if camera.get(key) != expected:
                raise ValueError(f"the camera {entry['camera']} names {key} {camera.get(key)!r}, "
                                 f"and the chain places it at {expected!r}")
        camera = sealed({**camera, "state_snapshot_sha256_by_character": state_map}, f"the camera of {shot}")
        written.append((c.local(root, entry["camera"]), camera))

        projection = artifact(root, entry["projection"], "shot-visual-projection", f"shots.{shot}.projection")
        projection = sealed({**projection, "scene_id": scene, "shot_id": shot,
                             "scene_context_sha256": artifact_hash(context),
                             "camera_spec_sha256": artifact_hash(camera),
                             "state_snapshot_sha256_by_character": state_map}, f"the shot projection of {shot}")
        written.append((c.local(root, entry["projection"]), projection))

        shot_request = artifact(root, entry["request"], "shot-request", f"shots.{shot}.request")
        shot_request = sealed({
            **shot_request, "scene_id": scene, "shot_id": shot,
            "species_profile_sha256_by_character": {i: artifact_hash(people[i]["species_profile"]) for i in shown},
            "individual_morphology_sha256_by_character": {i: artifact_hash(people[i]["individual_morphology"]) for i in shown},
            "identity_contract_sha256_by_character": {i: artifact_hash(people[i]["identity_contract"]) for i in shown},
            "state_snapshot_sha256_by_character": state_map,
            "scene_context_sha256": artifact_hash(context),
            "camera_spec_sha256": artifact_hash(camera),
            "shot_projection_sha256": artifact_hash(projection),
            "scene_plot_sha256": plot["approved"]["content_sha256"],
            "narrative_sha256": plot["narrative_sha256"],
        }, f"the request of {shot}")
        written.append((c.local(root, entry["request"]), shot_request))
    return written, report


def verify(root: Path, chain: dict, scene: str) -> dict[str, Any]:
    """The complete binding check of each shot, as `shot_request.py --require-complete` makes it."""
    from shot_request import validate_bundle
    order = chain["story_order"]
    results = {}
    for shot, entry in chain["shots"].items():
        shown = list(entry["character_projections"])
        people = chain["characters"]
        report = validate_bundle(
            c.load(c.local(root, entry["request"])),
            species_profile_files={i: c.local(root, people[i]["species_profile"]) for i in shown},
            individual_morphology_files={i: c.local(root, people[i]["individual_morphology"]) for i in shown},
            identity_files={i: c.local(root, people[i]["identity_contract"]) for i in shown},
            state_files={i: root / "state" / "snapshots" / f"{scene}-{order}-{i}.json" for i in shown},
            scene_context=root / "state" / "scene-contexts" / f"{scene}-{order}.json",
            camera_spec=c.local(root, entry["camera"]), shot_projection=c.local(root, entry["projection"]),
            require_complete=True)
        results[shot] = {"complete": report["complete"], "errors": report["errors"]}
    return results


def run(project: Path, chain_path: Path) -> dict[str, Any]:
    root = require_project(project)
    chain = read_chain(root, chain_path)
    with c.lock(root):
        written, report = build(root, chain)
        for path, value in written:
            path.parent.mkdir(parents=True, exist_ok=True)
            write_json(path, value)
        shots = verify(root, chain, report["scene_id"])
    return {"ok": all(item["complete"] for item in shots.values()), "scene_id": report["scene_id"],
            "written": [path.relative_to(root).as_posix() for path, _ in written], "shots": shots}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("chain", type=Path, help=f"The chain file, such as PROJECT/{EXAMPLE}")
    parser.add_argument("--project", type=Path, required=True, help="The project root")
    report_output.add_json_flag(parser)
    args = parser.parse_args(argv)
    report_output.use_json(args.json)
    try:
        result = run(args.project, args.chain)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        message = f"a file lacks the field {exc}" if isinstance(exc, KeyError) else str(exc)
        report_output.emit({"ok": False, "error": message})
        return 1
    report_output.emit(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
