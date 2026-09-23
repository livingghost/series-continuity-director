#!/usr/bin/env python3
"""Author, validate and resolve state, identity and visual projection artifacts."""
from __future__ import annotations
import argparse
import copy
import json
import os
import re
import hashlib
import stat
from pathlib import Path
from typing import Any, Iterable, Sequence
import protocol_contract as public_contract
from protocol_contract import (ARTIFACT_TYPES, SELF_HASH_FIELDS, ZERO_SHA256,
    STATE_LINEAGE_ARTIFACT_FIELDS, STATE_AWARE_REQUIRED_LINEAGE_FIELDS,
    SUPPORTED_SCHEMA_KEYWORDS, ANNOTATION_SCHEMA_KEYWORDS, canonical_json,
    parse_json, sha256_text, sha256_json, load_json, load_jsonl, write_json,
    artifact_type, schema_for, artifact_content_for_hash, artifact_hash,
    finalize_artifact, validate_against_schema, unsupported_schema_keywords,
    validate_cross_invariants, validate_artifact, schema_named)
from temporal_state import (ENTITY_BUCKETS, array_index, decode_pointer, get_pointer, _parent_for_pointer, apply_change, entity_root, precondition_holds, _is_lifecycle_change, _state_path_key, validate_temporal_inputs, _approved_events_as_of, _change_is_active, _restartable_epochs, _process_operations, apply_event, resolve_world as _resolve_public_world)
ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "protocols/shared-state/schemas"
PACKAGE_NAME = "series-continuity-director"
_MISSING = object()
STATE_SECTION_NAMES = (
    "physical_state",
    "appearance_state",
    "wardrobe_state",
    "equipment_state",
    "inventory_state",
    "emotional_state",
    "performance_state",
    "knowledge_state",
    "social_role_state",
    "character_specific_state",
)

COVERAGE_POLICIES = ("core-coverage", "series-coverage", "motion-evaluation")


def _declared_value_matches(value: Any, value_type: str) -> bool:
    if value_type == "any":
        return True
    return public_contract._type_matches(value, value_type)


def _character_schema_index(
    schemas: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    by_character: dict[str, dict[str, dict[str, Any]]] = {}
    for schema in schemas:
        report = validate_artifact(schema)
        if not report["ok"]:
            raise ValueError(
                f"invalid character state schema {schema.get('state_schema_id')}: "
                + "; ".join(report["errors"])
            )
        if schema.get("state_machines"):
            raise ValueError("character-state-schema state_machines require explicit path and trigger bindings")
        character_id = str(schema["character_id"])
        if character_id in by_character:
            raise ValueError(f"duplicate character state schema: {character_id}")
        declared: dict[str, dict[str, Any]] = {}
        for item in schema.get("state_paths", []):
            path = str(item["path"])
            if path in declared:
                raise ValueError(f"duplicate state path for {character_id}: {path}")
            declared[path] = item
        initial = schema.get("initial_state", {})
        marker = object()
        for path, item in declared.items():
            value = get_pointer(initial, path, missing=marker)
            if value is marker:
                continue
            value_type = str(item.get("value_type") or "any")
            if not _declared_value_matches(value, value_type):
                raise ValueError(
                    f"character state schema {character_id} initial value at {path} "
                    f"does not match declared type {value_type}"
                )
        by_character[character_id] = declared
    return by_character


def _require_declared_character_path(
    schema_index: dict[str, dict[str, dict[str, Any]]],
    *,
    character_id: str,
    path: str,
    allow_descendant: bool = False,
) -> dict[str, Any]:
    declared = schema_index.get(character_id)
    if declared is None:
        raise ValueError(f"missing character state schema for {character_id}")
    if path in declared:
        return declared[path]
    if allow_descendant:
        path_tokens = decode_pointer(path)
        for declared_path, item in declared.items():
            declared_tokens = decode_pointer(declared_path)
            if path_tokens[:len(declared_tokens)] == declared_tokens:
                return item
    raise ValueError(f"undeclared character state path for {character_id}: {path}")


def _validate_event_state_contract(
    event: dict[str, Any],
    schema_index: dict[str, dict[str, dict[str, Any]]],
) -> None:
    for condition in event.get("preconditions", []):
        if condition.get("entity_type") == "character":
            _require_declared_character_path(
                schema_index,
                character_id=str(condition["entity_id"]),
                path=str(condition["path"]),
                allow_descendant=True,
            )
    for change in event.get("changes", []):
        if change.get("entity_type") != "character" or _is_lifecycle_change(change):
            continue
        character_id = str(change["entity_id"])
        path = str(change["path"])
        declaration = _require_declared_character_path(
            schema_index,
            character_id=character_id,
            path=path,
        )
        persistence = str(change.get("persistence") or "")
        if persistence not in declaration.get("allowed_persistence", []):
            raise ValueError(
                f"character state persistence {persistence!r} is not allowed for {character_id}:{path}"
            )
        operation = str(change.get("operation") or "")
        value_type = str(declaration.get("value_type") or "any")
        if operation in {"set", "replace"} and not _declared_value_matches(change.get("value"), value_type):
            raise ValueError(
                f"character state value for {character_id}:{path} does not match declared type {value_type}"
            )
        if operation == "merge" and value_type not in {"object", "any"}:
            raise ValueError(f"merge requires an object state path: {character_id}:{path}")
        if operation == "append" and value_type not in {"array", "any"}:
            raise ValueError(f"append requires an array state path: {character_id}:{path}")
        if operation == "increment" and value_type not in {"number", "any"}:
            raise ValueError(f"increment requires a number state path: {character_id}:{path}")


def _validate_process_state_contract(
    process: dict[str, Any],
    schema_index: dict[str, dict[str, dict[str, Any]]],
) -> None:
    if process.get("entity_type") != "character":
        return
    character_id = str(process["entity_id"])
    path = str(process["path"])
    declaration = _require_declared_character_path(
        schema_index,
        character_id=character_id,
        path=path,
    )
    value_type = str(declaration.get("value_type") or "any")
    for index, milestone in enumerate(process.get("milestones", [])):
        if not _declared_value_matches(milestone.get("state"), value_type):
            raise ValueError(
                f"state process milestone {index} for {character_id}:{path} "
                f"does not match declared type {value_type}"
            )



def load_validated_artifact(path: Path, expected_type: str) -> dict[str, Any]:
    value = load_json(path)
    if value.get("artifact_type") != expected_type:
        raise ValueError(f"expected artifact_type {expected_type}: {path}")
    report = validate_artifact(value)
    if not report["ok"]:
        raise ValueError(f"invalid {expected_type}: " + "; ".join(report["errors"]))
    return value


def resolve_world(*, base_state, events, processes, timeline_id, story_order,
                  story_time, snapshot_id, scene_context_id,
                  character_state_schemas=None):
    """Check the project's declared mutable paths, then derive public state."""
    declarations = _character_schema_index(character_state_schemas or [])
    for event in events:
        _validate_event_state_contract(event, declarations)
    for process in processes:
        _validate_process_state_contract(process, declarations)
    return _resolve_public_world(base_state=base_state, events=events,
        processes=processes, timeline_id=timeline_id, story_order=story_order,
        story_time=story_time, snapshot_id=snapshot_id,
        scene_context_id=scene_context_id)


def _checked_growth(value: Any, name: str) -> dict[str, Any]:
    errors = validate_against_schema(value, schema_named("growth-geometry.schema.json"))
    if errors:
        raise ValueError(f"invalid {name}: " + "; ".join(errors))
    return copy.deepcopy(value)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _linked(path: Path) -> bool:
    """Whether a path component is a symbolic link or a Windows directory junction.

    A resolved path passes through neither. Its spelling may still differ from
    what resolve() returns, such as a lowercase drive letter or an 8.3 short
    name, so the components are inspected instead of the strings compared.
    """
    try:
        info = os.lstat(path)
    except OSError:
        return False
    # Only Windows reports a reparse tag, and only Windows defines the junction tag.
    tag = getattr(info, "st_reparse_tag", None)
    return stat.S_ISLNK(info.st_mode) or (tag is not None and tag == stat.IO_REPARSE_TAG_MOUNT_POINT)


def validate_source_bytes(source: Any, field: str = "source") -> dict[str, Any]:
    """Verify an explicitly selected file source; this check neither fetches URIs nor records adoption."""
    if not isinstance(source, dict):
        raise ValueError(f"{field} must be a source object")
    kind = source.get("kind")
    definition = {"pack-artifact": "pack-artifact-source", "supplied-file": "supplied-file-source"}.get(kind)
    if definition is None:
        raise ValueError(f"{field}: unknown source kind")
    errors = validate_against_schema(source, {"$ref": "prepared-generation-reference.schema.json#/$defs/" + definition})
    if errors:
        raise ValueError(f"{field}: " + "; ".join(errors))
    path = Path(source["resolved_path"])
    if not path.is_absolute() or ".." in path.parts or any(map(_linked, [path, *path.parents])) or not path.is_file():
        raise ValueError(f"{field}: select an explicitly resolved regular file")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != source["sha256"]:
        raise ValueError(f"{field}: source byte hash mismatch")
    # Pack metadata remains producer provenance, not permission to discover a pack catalogue.
    return copy.deepcopy(source)


def extract_character_snapshot(
    world_snapshot: dict[str, Any],
    *,
    character_id: str,
    species_profile_hash: str,
    individual_morphology_hash: str,
    identity_hash: str,
    era_hash: str | None,
    form_hash: str | None,
    appearance_hash: str | None,
    snapshot_id: str,
) -> dict[str, Any]:
    world_report = validate_artifact(world_snapshot)
    if not world_report["ok"]:
        raise ValueError("invalid world-state snapshot: " + "; ".join(world_report["errors"]))
    state = world_snapshot.get("entities", {}).get("characters", {}).get(character_id)
    if not isinstance(state, dict):
        raise ValueError(f"character is absent from world snapshot: {character_id}")
    result = {
        "artifact_type": "state-snapshot",
        "snapshot_id": snapshot_id,
        "character_id": character_id,
        "timeline_id": world_snapshot["timeline_id"],
        "scene_context_id": world_snapshot["scene_context_id"],
        "story_order": world_snapshot["story_order"],
        "story_time": world_snapshot["story_time"],
        "species_profile_sha256": species_profile_hash,
        "individual_morphology_sha256": individual_morphology_hash,
        "identity_contract_sha256": identity_hash,
        "era_contract_sha256": era_hash,
        "form_contract_sha256": form_hash,
        "appearance_variant_sha256": appearance_hash,
        "applied_event_ids": list(world_snapshot.get("applied_event_ids", [])),
        "applied_process_milestones": list(world_snapshot.get("applied_process_milestones", [])),
        **{name: copy.deepcopy(state.get(name, {})) for name in STATE_SECTION_NAMES},
        "uncertainties": copy.deepcopy(state.get("uncertainties", [])),
        "state_snapshot_sha256": "0" * 64,
    }
    return finalize_artifact(result)



def build_scene_context(
    request: dict[str, Any],
    world_snapshot: dict[str, Any],
    character_snapshots: list[dict[str, Any]],
) -> dict[str, Any]:
    world_report = validate_artifact(world_snapshot)
    if not world_report["ok"]:
        raise ValueError("invalid world-state snapshot: " + "; ".join(world_report["errors"]))
    if world_snapshot.get("scene_context_id") != request.get("scene_context_id"):
        raise ValueError("world snapshot target scene does not match the context request")
    if world_snapshot.get("timeline_id") != request.get("timeline_id"):
        raise ValueError("world snapshot timeline does not match the context request")
    world_order = world_snapshot.get("story_order")
    if (
        not isinstance(world_order, int)
        or world_order < int(request["story_order_start"])
        or world_order > int(request["story_order_end"])
    ):
        raise ValueError("world snapshot order is outside the context request range")
    active_ids = request.get("active_character_ids", [])
    if not isinstance(active_ids, list) or any(not isinstance(x, str) or not x for x in active_ids):
        raise ValueError("active_character_ids must be a list of nonempty identifiers")
    if len(set(active_ids)) != len(active_ids):
        raise ValueError("duplicate active character ID")
    snapshot_by_id = {}
    for snapshot in character_snapshots:
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("character_id"), str):
            raise ValueError("invalid character snapshot input")
        cid = snapshot["character_id"]
        if cid in snapshot_by_id:
            raise ValueError("duplicate character snapshot ID: " + cid)
        snapshot_by_id[cid] = snapshot
    missing = [item for item in active_ids if item not in snapshot_by_id]
    if missing:
        raise ValueError(f"missing character snapshots for active characters: {missing}")
    active_refs = []
    for character_id in active_ids:
        snapshot = snapshot_by_id[character_id]
        report = validate_artifact(snapshot)
        if not report["ok"]:
            raise ValueError(f"invalid state snapshot for {character_id}: {'; '.join(report['errors'])}")
        if snapshot.get("scene_context_id") != request.get("scene_context_id"):
            raise ValueError(
                f"state snapshot target scene differs for active character {character_id}"
            )
        for field in ("timeline_id", "story_order", "story_time"):
            if snapshot.get(field) != world_snapshot.get(field):
                raise ValueError(f"state snapshot {field} differs from world for {character_id}")
        world_character = world_snapshot.get("entities", {}).get("characters", {}).get(character_id)
        if not isinstance(world_character, dict):
            raise ValueError(f"selected character is absent from world: {character_id}")
        for section in STATE_SECTION_NAMES:
            if canonical_json(snapshot.get(section, {})) != canonical_json(world_character.get(section, {})):
                raise ValueError(f"state snapshot {section} differs from world for {character_id}")
        for field in ("applied_event_ids", "applied_process_milestones"):
            if snapshot.get(field, []) != world_snapshot.get(field, []):
                raise ValueError(f"snapshot history differs from world for {character_id}: {field}")
        active_refs.append({
            "character_id": character_id,
            "snapshot_id": snapshot["snapshot_id"],
            "state_snapshot_sha256": snapshot["state_snapshot_sha256"],
        })

    entities = world_snapshot.get("entities", {})
    environment_id = request.get("environment_id")
    environment_value = {}
    if environment_id:
        if str(environment_id) not in entities.get("environments", {}):
            raise ValueError("selected environment is absent from world: " + str(environment_id))
        environment_value = copy.deepcopy(entities["environments"][str(environment_id)])
    for field in ("relationship_ids", "prop_ids"):
        ids = request.get(field, [])
        if not isinstance(ids, list) or any(not isinstance(x, str) or not x for x in ids) or len(set(ids)) != len(ids):
            raise ValueError(f"{field} must contain unique nonempty IDs")
    relationship_values = []
    for relationship_id in request.get("relationship_ids", []):
        value = entities.get("relationships", {}).get(str(relationship_id))
        if value is None:
            raise ValueError("selected relationship is absent from world: " + str(relationship_id))
        if value is not None:
            relationship_values.append({"relationship_id": relationship_id, "state": copy.deepcopy(value)})
    prop_values = []
    for prop_id in request.get("prop_ids", []):
        value = entities.get("props", {}).get(str(prop_id))
        if value is None:
            raise ValueError("selected prop is absent from world: " + str(prop_id))
        if value is not None:
            prop_values.append({"prop_id": prop_id, "state": copy.deepcopy(value)})

    result = {
        "artifact_type": "scene-context-snapshot",
        "scene_context_id": str(request["scene_context_id"]),
        "timeline_id": str(request["timeline_id"]),
        "story_order_start": int(request["story_order_start"]),
        "story_order_end": int(request["story_order_end"]),
        "story_time_start": str(request["story_time_start"]),
        "story_time_end": str(request["story_time_end"]),
        "location_snapshot": copy.deepcopy(request.get("location_snapshot", {})),
        "environment_snapshot": environment_value,
        "active_character_snapshots": active_refs,
        "relationship_snapshots": relationship_values,
        "prop_and_inventory_bindings": prop_values,
        "social_context": copy.deepcopy(request.get("social_context", {})),
        "viewer_disclosure_state": copy.deepcopy(request.get("viewer_disclosure_state", {})),
        "planned_events": copy.deepcopy(request.get("planned_events", [])),
        "context_snapshot_sha256": "0" * 64,
    }
    return finalize_artifact(result)



def _identity_features(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    features: dict[str, dict[str, Any]] = {}
    for detail in contract.get("distinctive_details", []):
        if isinstance(detail, dict) and detail.get("id"):
            features[str(detail["id"])] = {
                "feature_id": str(detail["id"]),
                "wording": str(detail.get("prompt") or detail.get("label") or detail["id"]),
                "priority": str(detail.get("identity_priority") or "supporting"),
                "source": "distinctive-detail",
                "carriers": ["reference-media", "text", "review"],
            }
    for anchor in contract.get("anchor_fragments", []):
        if isinstance(anchor, dict) and anchor.get("anchor_id"):
            features[str(anchor["anchor_id"])] = {
                "feature_id": str(anchor["anchor_id"]),
                "wording": str(anchor.get("wording") or ""),
                "priority": str(anchor.get("priority") or "supporting"),
                "source": "anchor-fragment",
                "carriers": list(anchor.get("carriers", [])),
                "required_when": list(anchor.get("required_when", [])),
                "omit_when": list(anchor.get("omit_when", [])),
            }
    return features



def _resolve_path_items(snapshot: dict[str, Any], items: Iterable[Any], *, group: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, raw in enumerate(items):
        if isinstance(raw, str):
            item = {"path": raw}
        elif isinstance(raw, dict):
            item = raw
        else:
            raise ValueError(f"{group}[{index}] must be a string or object")
        path = str(item.get("path") or "")
        if not path:
            raise ValueError(f"{group}[{index}] is missing path")
        value = get_pointer(snapshot, path, missing=None)
        result.append({
            "path": path,
            "label": str(item.get("label") or path.rsplit("/", 1)[-1]),
            "value": value,
            "wording": str(item.get("wording") or ""),
            "priority": str(item.get("priority") or "supporting"),
            "carriers": list(item.get("carriers", [])),
        })
    return result



def resolve_morphology_projection(
    species_profile: dict[str, Any],
    individual_morphology: dict[str, Any],
    state_snapshot: dict[str, Any],
    request: dict[str, Any],
) -> dict[str, Any]:
    """Resolve exact shot-visible morphology without inventing missing anatomy."""
    for artifact, expected in (
        (species_profile, "species-morphology-profile"),
        (individual_morphology, "individual-morphology-contract"),
    ):
        report = validate_artifact(artifact)
        if not report["ok"] or artifact.get("artifact_type") != expected:
            raise ValueError(f"invalid {expected}: " + "; ".join(report.get("errors", [])))

    species_hash = artifact_hash(species_profile)
    individual_hash = artifact_hash(individual_morphology)
    species_ref = individual_morphology.get("species_profile_ref", {})
    if species_ref.get("id") != species_profile.get("profile_id") or species_ref.get("sha256") != species_hash:
        raise ValueError("individual morphology species_profile_ref does not match supplied profile")
    if state_snapshot.get("species_profile_sha256") != species_hash:
        raise ValueError("state snapshot species profile hash differs from supplied profile")
    if state_snapshot.get("individual_morphology_sha256") != individual_hash:
        raise ValueError("state snapshot individual morphology hash differs from supplied contract")

    feature_by_id = {
        str(item.get("feature_id")): item
        for item in individual_morphology.get("feature_realizations", [])
        if isinstance(item, dict) and item.get("feature_id")
    }
    requested_visible = [str(item) for item in request.get("visible_morphology_feature_ids", [])]
    if not requested_visible:
        requested_visible = [
            feature_id for feature_id, item in feature_by_id.items()
            if item.get("identity_priority") == "signature" and item.get("status") != "absent"
        ]
    visible: list[dict[str, Any]] = []
    for feature_id in requested_visible:
        item = feature_by_id.get(feature_id)
        if item is None:
            raise ValueError(f"unknown morphology feature ID: {feature_id}")
        if item.get("status") == "absent":
            raise ValueError(f"absent morphology feature cannot be required visible: {feature_id}")
        if not isinstance(item.get("resolved_feature"), dict):
            raise ValueError(f"morphology feature lacks resolved_feature: {feature_id}")
        visible.append(copy.deepcopy(item))

    explicit_hidden = list(dict.fromkeys(str(item) for item in request.get("occluded_morphology_feature_ids", [])))
    for feature_id in explicit_hidden:
        if feature_id not in feature_by_id:
            raise ValueError(f"unknown occluded morphology feature ID: {feature_id}")
    automatically_hidden = [
        feature_id for feature_id, item in feature_by_id.items()
        if feature_id not in requested_visible and item.get("status") != "absent"
    ]
    hidden_feature_refs = list(dict.fromkeys(explicit_hidden + automatically_hidden))
    state_deltas = _resolve_path_items(
        state_snapshot,
        request.get("morphology_state_paths", []),
        group="morphology_state_paths",
    )
    obligations = list(dict.fromkeys(
        [str(item) for item in request.get("morphology_visibility_obligations", [])]
        + [
            f"preserve {item.get('feature_id')} count, attachment, shape, surface, and declared individual differences"
            for item in visible
        ]
    ))
    crop_requirements = list(dict.fromkeys(str(item) for item in request.get("morphology_crop_and_occlusion_requirements", [])))
    expression_channels = []
    species_channels = {
        str(item.get("channel_id")): copy.deepcopy(item)
        for item in species_profile.get("expression_system", [])
        if isinstance(item, dict) and item.get("channel_id")
    }
    individual_channels = {
        str(item.get("channel_id")): copy.deepcopy(item)
        for item in individual_morphology.get("individual_expression_signature", [])
        if isinstance(item, dict) and item.get("channel_id")
    }
    expression_projection: list[dict[str, Any]] = []
    requested_expression = {
        str(item.get("channel_id")): copy.deepcopy(item)
        for item in request.get("morphology_expression_projection", [])
        if isinstance(item, dict) and item.get("channel_id")
    }
    for channel_id in sorted(set(species_channels) | set(individual_channels)):
        species_channel = species_channels.get(channel_id)
        individual_channel = individual_channels.get(channel_id)
        expression_channels.append({
            "channel_id": channel_id,
            "species_capability": species_channel,
            "individual_signature": individual_channel,
        })
        authored = requested_expression.get(channel_id)
        if authored is not None:
            expression_projection.append(authored)
        else:
            expression_projection.append({
                "channel_id": channel_id,
                "carrier_feature_refs": list((species_channel or {}).get("carrier_feature_refs", [])),
                "configuration": str((individual_channel or {}).get("baseline_bias") or (species_channel or {}).get("neutral_state") or "neutral declared state"),
                "meaning_candidates": list((species_channel or {}).get("readable_meanings", [])),
                "tool_refs": list((species_channel or {}).get("external_tool_refs", [])),
            })
    count_checks = [
        f"{item.get('feature_id')}: actual_count={item.get('actual_count')} and attachment={item.get('attachment_realization', {}).get('attachment_landmarks', [])}"
        for item in visible
    ]
    return {
        "species_profile_ref": {
            "id": str(species_profile["profile_id"]),
            "sha256": species_hash,
        },
        "individual_morphology_ref": {
            "id": str(individual_morphology["contract_id"]),
            "sha256": individual_hash,
        },
        "active_form": str(individual_morphology.get("life_stage_and_form", {}).get("active_form") or "baseline"),
        "body_plan": {
            "species_body_plan": copy.deepcopy(species_profile.get("body_plan", {})),
            "individual_measurements": copy.deepcopy(individual_morphology.get("individual_measurements", {})),
            "life_stage_and_form": copy.deepcopy(individual_morphology.get("life_stage_and_form", {})),
        },
        "frame_character": copy.deepcopy(individual_morphology.get("frame_character") or species_profile.get("frame_character_model", {}).get("default") or {}),
        "measurement_pass_status": str(request.get("measurement_pass_status") or ("complete" if individual_morphology.get("load_bearing_part_measurements") or request.get("morphology_load_bearing_part_measurements") else "not-required")),
        "load_bearing_part_measurements": copy.deepcopy(
            request.get("morphology_load_bearing_part_measurements")
            if request.get("morphology_load_bearing_part_measurements") is not None
            else individual_morphology.get("load_bearing_part_measurements", [])
        ),
        "visible_feature_instances": visible,
        "hidden_or_out_of_frame_feature_refs": hidden_feature_refs,
        "feature_relationships": copy.deepcopy(individual_morphology.get("feature_relationship_realizations", [])),
        "surface_and_marking_map": copy.deepcopy(individual_morphology.get("surface_and_marking_map", [])),
        "expression_channels": expression_channels,
        "expression_projection": expression_projection,
        "communication_and_expression_tools": copy.deepcopy(
            individual_morphology.get("communication_and_expression_tool_realizations", [])
        ),
        "identity_invariants": copy.deepcopy(individual_morphology.get("identity_invariants", [])),
        "inventory_proof": {
            "declared_visible_count": len(visible),
            "declared_hidden_count": len(hidden_feature_refs),
            "unresolved_count": len(individual_morphology.get("unresolved_features", [])),
            "count_and_attachment_checks": count_checks,
        },
        "current_state_deltas": state_deltas,
        "visible_obligations": obligations,
        "crop_and_occlusion_requirements": crop_requirements,
        "uncertainties": copy.deepcopy(state_snapshot.get("uncertainties", [])),
    }



def projection_semantic_content(value: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "resolved_morphology", "visible_identity_features", "visible_state_deltas", "performance_cues",
        "wardrobe_and_accessory_state", "held_or_visible_props",
        "relationship_blocking_cues", "environmental_body_responses",
        "occluded_or_irrelevant_features", "reference_asset_requirements",
        "text_anchor_fragments", "review_dimensions",
    )
    return {key: value.get(key) for key in keys}



def build_projection(
    identity_contract: dict[str, Any],
    species_profile: dict[str, Any],
    individual_morphology: dict[str, Any],
    state_snapshot: dict[str, Any],
    scene_context: dict[str, Any],
    request: dict[str, Any],
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    for artifact in (identity_contract, state_snapshot, scene_context):
        report = validate_artifact(artifact)
        if not report["ok"]:
            raise ValueError(f"invalid {artifact.get('artifact_type')}: {'; '.join(report['errors'])}")
    species_hash = artifact_hash(species_profile)
    individual_hash = artifact_hash(individual_morphology)
    if identity_contract.get("species_morphology_profile_ref") != {
        "id": species_profile.get("profile_id"), "sha256": species_hash
    }:
        raise ValueError("identity contract species morphology reference does not match supplied profile")
    if identity_contract.get("individual_morphology_contract_ref") != {
        "id": individual_morphology.get("contract_id"), "sha256": individual_hash
    }:
        raise ValueError("identity contract individual morphology reference does not match supplied contract")
    if individual_morphology.get("character_id") != identity_contract.get("character_id"):
        raise ValueError("individual morphology contract belongs to another character")
    if request.get("character_id") != identity_contract.get("character_id"):
        raise ValueError("projection request character_id differs from identity contract")
    # These are copied into the projection as they stand, and its schema holds
    # each entry as an object, so the request is the place to name the shape.
    for field in ("performance_cues", "relationship_blocking_cues", "environmental_body_responses",
                  "reference_asset_requirements"):
        items = request.get(field, [])
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise ValueError(f'projection request {field} must be an array of objects, such as '
                             f'[{{"cue": "shoulders drop as the parcel leaves his paws"}}]; got {items!r}')

    character_id = identity_contract["character_id"]
    if state_snapshot.get("character_id") != character_id or state_snapshot.get("identity_contract_sha256") != artifact_hash(identity_contract):
        raise ValueError("state snapshot does not bind the supplied identity")
    if state_snapshot["scene_context_id"] != scene_context["scene_context_id"] or state_snapshot["timeline_id"] != scene_context["timeline_id"]:
        raise ValueError("projection snapshot and scene context have different scope")
    if not scene_context["story_order_start"] <= state_snapshot["story_order"] <= scene_context["story_order_end"]:
        raise ValueError("projection snapshot is outside the scene context range")
    binding = {"character_id": character_id, "snapshot_id": state_snapshot["snapshot_id"], "state_snapshot_sha256": artifact_hash(state_snapshot)}
    if binding not in scene_context["active_character_snapshots"]:
        raise ValueError("scene context does not bind the projection's exact character snapshot")
    features = _identity_features(identity_contract)
    visible_features: list[dict[str, Any]] = []
    for feature_id in request.get("visible_identity_feature_ids", []):
        if str(feature_id) not in features:
            raise ValueError(f"unknown identity feature ID: {feature_id}")
        visible_features.append(copy.deepcopy(features[str(feature_id)]))

    text_anchors: list[dict[str, Any]] = []
    for anchor_id in request.get("text_anchor_ids", []):
        feature = features.get(str(anchor_id))
        if not feature or feature.get("source") != "anchor-fragment":
            raise ValueError(f"unknown anchor fragment ID: {anchor_id}")
        text_anchors.append(copy.deepcopy(feature))

    projection = {
        "artifact_type": "visual-state-projection",
        "projection_id": str(request["projection_id"]),
        "character_id": str(request["character_id"]),
        "state_snapshot_sha256": str(state_snapshot["state_snapshot_sha256"]),
        "scene_context_sha256": str(scene_context["context_snapshot_sha256"]),
        "resolved_morphology": resolve_morphology_projection(
            species_profile, individual_morphology, state_snapshot, request
        ),
        "visible_identity_features": visible_features,
        "visible_state_deltas": _resolve_path_items(state_snapshot, request.get("visible_state_paths", []), group="visible_state_paths"),
        "performance_cues": copy.deepcopy(request.get("performance_cues", [])),
        "wardrobe_and_accessory_state": _resolve_path_items(state_snapshot, request.get("wardrobe_paths", []), group="wardrobe_paths"),
        "held_or_visible_props": _resolve_path_items(state_snapshot, request.get("prop_paths", []), group="prop_paths"),
        "relationship_blocking_cues": copy.deepcopy(request.get("relationship_blocking_cues", [])),
        "environmental_body_responses": copy.deepcopy(request.get("environmental_body_responses", [])),
        "occluded_or_irrelevant_features": _resolve_path_items(state_snapshot, request.get("occluded_state_paths", []), group="occluded_state_paths"),
        "reference_asset_requirements": copy.deepcopy(request.get("reference_asset_requirements", [])),
        "text_anchor_fragments": text_anchors,
        "review_dimensions": list(dict.fromkeys(str(item) for item in request.get("review_dimensions", []))),
        "prompt_regeneration_required": True,
        "projection_sha256": "0" * 64,
    }
    if previous:
        projection["prompt_regeneration_required"] = (
            projection_semantic_content(projection) != projection_semantic_content(previous)
            or projection["state_snapshot_sha256"] != previous.get("state_snapshot_sha256")
            or projection["scene_context_sha256"] != previous.get("scene_context_sha256")
        )
    return finalize_artifact(projection)



def _changed_growth_paths(before: Any, after: Any, path: str = "") -> list[str]:
    """Return exact changed JSON pointers; arrays retain their declared order."""
    if isinstance(before, dict) and isinstance(after, dict):
        changed: list[str] = []
        for key in sorted(set(before) | set(after)):
            child = path + "/" + key.replace("~", "~0").replace("/", "~1")
            if key not in before or key not in after:
                changed.append(child)
            else:
                changed.extend(_changed_growth_paths(before[key], after[key], child))
        return changed
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [child for index, (left, right) in enumerate(zip(before, after))
                for child in _changed_growth_paths(left, right, f"{path}/{index}")]
    return [] if type(before) is type(after) and before == after else [path]



def _checked_growth_parent(
    value: dict[str, Any], kind: str, identity: dict[str, Any]
) -> None:
    report = validate_artifact(value)
    if not report["ok"] or value.get("artifact_type") != kind:
        raise ValueError(f"invalid {kind}: " + "; ".join(report.get("errors", [])))
    if value.get("character_id") != identity.get("character_id"):
        raise ValueError(f"{kind} belongs to another character")
    if value.get("parent_identity_contract_sha256") != artifact_hash(identity):
        raise ValueError(f"{kind} parent identity hash does not match the supplied identity")
    if value.get("canon_status") != "approved":
        raise ValueError(f"{kind} must be approved before it can resolve growth geometry")



def resolve_growth_geometry(
    identity_contract: dict[str, Any],
    *,
    era_contract: dict[str, Any] | None = None,
    form_contract: dict[str, Any] | None = None,
    appearance_variant: dict[str, Any] | None = None,
    state_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve authored geometry once for renderers, production and graph checks.

    An approved era or form may declare a complete replacement. An appearance
    variant may change only the exact JSON pointers the resolved identity lists
    in variant_fields. Current grooming is serialized as condition annotations;
    it never overwrites permanent geometry or the authority that permits edits.
    Inputs are neither mutated nor inferred from species, material or prose.
    """
    report = validate_artifact(identity_contract)
    if not report["ok"] or identity_contract.get("artifact_type") != "character-identity-contract":
        raise ValueError("invalid character identity for growth resolution: " + "; ".join(report.get("errors", [])))
    geometry = _checked_growth(identity_contract.get("stable_identity", {}).get("growth_geometry"),
                               "stable_identity.growth_geometry")
    for contract, kind, field in (
        (era_contract, "era-contract", "approved_changes"),
        (form_contract, "form-contract", "surface_system"),
    ):
        if contract is None:
            continue
        _checked_growth_parent(contract, kind, identity_contract)
        declaration = contract.get(field, {})
        if "growth_geometry" in declaration:
            geometry = _checked_growth(declaration["growth_geometry"], f"{kind}.{field}.growth_geometry")
    if appearance_variant is not None:
        _checked_growth_parent(appearance_variant, "appearance-variant-contract", identity_contract)
        # There is one canonical geometry field, not a competing declaration
        # hidden inside the free-form appearance description.
        if "growth_geometry" in appearance_variant.get("appearance_definition", {}):
            raise ValueError("appearance_definition must not shadow the top-level growth_geometry")
        variant_geometry = appearance_variant.get("growth_geometry")
        if variant_geometry is not None:
            variant_geometry = _checked_growth(variant_geometry, "appearance-variant-contract.growth_geometry")
            changed = _changed_growth_paths(geometry, variant_geometry)
            prefix = "/stable_identity/growth_geometry"
            allowed = set(geometry["variant_fields"])
            # A variant cannot grant itself permission or remove identity locks.
            protected = ("/variant_fields", "/identity_lock_fields", "/representation")
            forbidden = [path for path in changed
                         if prefix + path not in allowed
                         or any(path == key or path.startswith(key + "/") for key in protected)]
            if forbidden:
                raise ValueError("appearance variant changes growth outside authorized variant_fields: "
                                 + ", ".join(prefix + path for path in forbidden))
            geometry = variant_geometry
    if state_snapshot is not None:
        report = validate_artifact(state_snapshot)
        if not report["ok"] or state_snapshot.get("artifact_type") != "state-snapshot":
            raise ValueError("invalid state snapshot for growth resolution: " + "; ".join(report.get("errors", [])))
        if state_snapshot.get("character_id") != identity_contract.get("character_id"):
            raise ValueError("state snapshot belongs to another character")
        expected = {
            "identity_contract_sha256": artifact_hash(identity_contract),
            "era_contract_sha256": artifact_hash(era_contract) if era_contract is not None else None,
            "form_contract_sha256": artifact_hash(form_contract) if form_contract is not None else None,
            "appearance_variant_sha256": artifact_hash(appearance_variant) if appearance_variant is not None else None,
        }
        for field, digest in expected.items():
            if state_snapshot.get(field) != digest:
                raise ValueError(f"state snapshot {field} differs from supplied growth authority")
        grooming = state_snapshot.get("appearance_state", {}).get("grooming")
        if grooming is not None:
            # A single canonical string preserves arbitrary authored condition
            # structure without inventing anatomy or interpreting natural text.
            condition = "/appearance_state/grooming = " + canonical_json(grooming)
            if condition not in geometry["grooming_state"]:
                geometry["grooming_state"].append(condition)
    return geometry



def anchor_text_for_view(contract: dict[str, Any], tokens: set[str]) -> list[str]:
    chosen: list[str] = []
    for anchor in contract.get("anchor_fragments", []):
        if not isinstance(anchor, dict):
            continue
        required_when = set(str(item) for item in anchor.get("required_when", []))
        omit_when = set(str(item) for item in anchor.get("omit_when", []))
        if omit_when & tokens:
            continue
        if not required_when or required_when & tokens or anchor.get("priority") == "signature":
            wording = str(anchor.get("wording") or "").strip()
            if wording:
                chosen.append(wording)
    return chosen



def plan_reference_bundle(
    contract: dict[str, Any],
    *,
    species_profile: dict[str, Any],
    individual_morphology: dict[str, Any],
    style_family_id: str,
    target_model: str,
    policy: str,
    out_dir: Path,
    era_contract: dict[str, Any] | None = None,
    appearance_variant: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report = validate_artifact(contract)
    if not report["ok"]:
        raise ValueError("invalid identity contract: " + "; ".join(report["errors"]))
    if policy not in COVERAGE_POLICIES:
        raise ValueError(f"unknown coverage policy: {policy}")
    identity_hash = artifact_hash(contract)
    species_report = validate_artifact(species_profile)
    if not species_report["ok"] or species_profile.get("artifact_type") != "species-morphology-profile":
        raise ValueError("invalid species morphology profile: " + "; ".join(species_report.get("errors", [])))
    individual_report = validate_artifact(individual_morphology)
    if not individual_report["ok"] or individual_morphology.get("artifact_type") != "individual-morphology-contract":
        raise ValueError("invalid individual morphology contract: " + "; ".join(individual_report.get("errors", [])))
    species_hash = artifact_hash(species_profile)
    individual_hash = artifact_hash(individual_morphology)
    species_ref = contract.get("species_morphology_profile_ref", {})
    individual_ref = contract.get("individual_morphology_contract_ref", {})
    if species_ref.get("id") != species_profile.get("profile_id") or species_ref.get("sha256") != species_hash:
        raise ValueError("identity contract species morphology reference does not match supplied profile")
    if individual_ref.get("id") != individual_morphology.get("contract_id") or individual_ref.get("sha256") != individual_hash:
        raise ValueError("identity contract individual morphology reference does not match supplied contract")
    if individual_morphology.get("character_id") != contract.get("character_id"):
        raise ValueError("individual morphology contract belongs to another character")
    if individual_morphology.get("domain") != contract.get("domain") or species_profile.get("domain") != contract.get("domain"):
        raise ValueError("morphology domain differs from character identity domain")
    era_hash: str | None = None
    appearance_hash: str | None = None
    if era_contract is not None:
        era_report = validate_artifact(era_contract)
        if not era_report["ok"] or era_contract.get("artifact_type") != "era-contract":
            raise ValueError("invalid era contract: " + "; ".join(era_report.get("errors", [])))
        if era_contract.get("character_id") != contract.get("character_id"):
            raise ValueError("era contract belongs to another character")
        era_hash = artifact_hash(era_contract)
    if appearance_variant is not None:
        appearance_report = validate_artifact(appearance_variant)
        if not appearance_report["ok"] or appearance_variant.get("artifact_type") != "appearance-variant-contract":
            raise ValueError("invalid appearance variant: " + "; ".join(appearance_report.get("errors", [])))
        if appearance_variant.get("character_id") != contract.get("character_id"):
            raise ValueError("appearance variant belongs to another character")
        appearance_hash = artifact_hash(appearance_variant)
    declared_views = contract.get("reference_views")
    if not declared_views:
        raise ValueError("reference planning requires explicit reference_views and camera contracts")
    requirements = [item for item in contract.get("coverage_requirements", []) if isinstance(item, dict)]
    reference_candidates = {
        name: {"view": row["view"], "framing": row["framing"],
               "tokens": set(row["coverage_tokens"]), "camera": copy.deepcopy(row["camera"])}
        for name, row in sorted(declared_views.items())
    }
    selected: list[str] = [] if requirements else list(reference_candidates)

    # Add candidates greedily until every declared requirement has at least one acceptable view.
    def requirement_covered(req: dict[str, Any], candidates: list[str]) -> bool:
        acceptable = set(str(item) for item in req.get("acceptable_views", []))
        return any(acceptable & reference_candidates[name]["tokens"] for name in candidates)

    unresolved = [req for req in requirements if not requirement_covered(req, selected)]
    while unresolved:
        best_name: str | None = None
        best_score = 0
        for name, candidate in reference_candidates.items():
            if name in selected:
                continue
            score = sum(bool(set(req.get("acceptable_views", [])) & candidate["tokens"]) for req in unresolved)
            if score > best_score:
                best_name, best_score = name, score
        if not best_name or best_score == 0:
            break
        selected.append(best_name)
        unresolved = [req for req in requirements if not requirement_covered(req, selected)]

    asset_rows: list[dict[str, Any]] = []
    pending_render_specs: list[tuple[str, dict[str, Any]]] = []
    coverage_matrix: dict[str, list[str]] = {str(req["requirement_id"]): [] for req in requirements}
    stable = copy.deepcopy(contract.get("stable_identity", {}))
    stable["growth_geometry"] = resolve_growth_geometry(
        contract, era_contract=era_contract, appearance_variant=appearance_variant,
    )
    stable["species_morphology_profile"] = copy.deepcopy(species_profile)
    stable["individual_morphology_contract"] = copy.deepcopy(individual_morphology)
    if era_contract is not None:
        stable["era_changes"] = copy.deepcopy(era_contract.get("approved_changes", {}))
    if appearance_variant is not None:
        stable["appearance_variant"] = copy.deepcopy(appearance_variant.get("appearance_definition", {}))
    character_id = str(contract["character_id"])

    for index, name in enumerate(selected, 1):
        candidate = reference_candidates[name]
        tokens = set(candidate["tokens"])
        requirement_ids = []
        for req in requirements:
            if set(req.get("acceptable_views", [])) & tokens:
                rid = str(req["requirement_id"])
                requirement_ids.append(rid)
        asset_id = f"{character_id}-A{index:02d}"
        render_spec_id = f"ARS-{asset_id}"
        anchors = anchor_text_for_view(contract, tokens)
        identity_summary = "; ".join(
            str(stable.get(key) or "").strip()
            for key in ("species_or_base_form", "body_plan", "proportions", "head_and_face", "structure_notes", "surfaces_and_markings", "appendages", "asymmetry_rules", "identity_accessories")
            if str(stable.get(key) or "").strip()
        )
        scaffold = (
            f"Create a {candidate['framing']} character reference in {candidate['view']} view. "
            f"Preserve the approved identity: {identity_summary}. "
            + ("Visible signature anchors: " + "; ".join(anchors) + ". " if anchors else "")
            + "Use neutral production lighting, clear unobstructed declared structure, and the selected concrete style family consistently. "
            + "This is a reference asset: prioritize measurable identity, attachment, markings, proportions, and silhouette over scene storytelling."
        )
        spec = {
                "artifact_type": "asset-render-specification",
            "render_spec_id": render_spec_id,
            "asset_id": asset_id,
            "character_id": character_id,
            "purpose": name,
            "view": candidate["view"],
            "framing": candidate["framing"],
            "species_profile_sha256": species_hash,
            "individual_morphology_sha256": individual_hash,
            "identity_contract_sha256": identity_hash,
            "era_contract_sha256": era_hash,
            "appearance_variant_sha256": appearance_hash,
            "state_snapshot_sha256": None,
            "visual_state_projection_sha256": None,
            "visual_authority_sha256": (contract.get("visual_authority_ref") or {}).get("sha256"),
            "visual_evidence_bundle_sha256": None,
            "style_family_id": style_family_id,
            "target_model": target_model,
            "coverage_requirement_ids": requirement_ids,
            "art_direction": {
                "center_of_appeal": "measurable character identity and consistent design",
                "composition": f"{candidate['view']} {candidate['framing']}",
                "medium": style_family_id,
                "detail_hierarchy": "declared identity landmarks, silhouette, attachments and local details",
            },
            "subject_resolution": copy.deepcopy(stable),
            "scene": {"background": "plain neutral reference background", "storytelling": "none"},
            "camera": copy.deepcopy(candidate["camera"]),
            "lighting": {"key": "neutral soft directional light", "fill": "clean neutral fill", "color": "stable local color"},
            "prompt_scaffold": scaffold,
            "selected_preset_ids": [style_family_id],
            "render_spec_sha256": "0" * 64,
        }
        spec = finalize_artifact(spec)
        spec_report = validate_artifact(spec)
        if not spec_report.get("ok"):
            raise ValueError(
                f"invalid generated render specification {render_spec_id}: "
                + "; ".join(spec_report.get("errors", []))
            )
        file_name = f"{asset_id}-{name}.render-spec.json"
        pending_render_specs.append((file_name, spec))
        asset_rows.append({
            "asset_id": asset_id,
            "purpose": name,
            "render_spec_file": file_name,
            "render_spec_sha256": spec["render_spec_sha256"],
            "coverage_requirement_ids": requirement_ids,
        })
        for rid in requirement_ids:
            coverage_matrix[rid].append(asset_id)

    unresolved_ids = [str(req["requirement_id"]) for req in unresolved]
    plan = {
        "artifact_type": "reference-bundle-plan",
        "bundle_id": f"RB-{character_id}",
        "character_id": character_id,
        "species_profile_sha256": species_hash,
        "individual_morphology_sha256": individual_hash,
        "identity_contract_sha256": identity_hash,
        "era_contract_sha256": era_hash,
        "appearance_variant_sha256": appearance_hash,
        "visual_authority_sha256": (contract.get("visual_authority_ref") or {}).get("sha256"),
        "visual_evidence_bundle_sha256": None,
        "style_family_id": style_family_id,
        "coverage_policy": policy,
        "assets": asset_rows,
        "coverage_matrix": coverage_matrix,
        "unresolved_requirements": unresolved_ids,
        "generated_by": PACKAGE_NAME,
        "notes": [
            "The plan is generation intent, not approved canon.",
            "Actual images require direct inspection and a separate candidate manifest before adoption.",
        ],
        "bundle_plan_sha256": "0" * 64,
    }
    plan = finalize_artifact(plan)
    plan_report = validate_artifact(plan)
    if not plan_report.get("ok"):
        raise ValueError(
            "invalid generated reference bundle plan: "
            + "; ".join(plan_report.get("errors", []))
        )

    # The output directory is the commit boundary.  No child file is written
    # until every child render specification and the enclosing plan validate.
    out_dir.mkdir(parents=True, exist_ok=True)
    for file_name, spec in pending_render_specs:
        write_json(out_dir / file_name, spec)
    write_json(out_dir / "reference-bundle-plan.json", plan)
    return plan



def build_lineage(args: argparse.Namespace) -> dict[str, Any]:
    def hash_file(path_value: str | None, expected_type: str | None = None) -> str | None:
        if not path_value:
            return None
        data = load_json(Path(path_value))
        if expected_type and data.get("artifact_type") != expected_type:
            raise ValueError(f"expected {expected_type}, got {data.get('artifact_type')}: {path_value}")
        report = validate_artifact(data)
        if not report["ok"]:
            raise ValueError(f"invalid artifact {path_value}: {'; '.join(report['errors'])}")
        return artifact_hash(data)

    if args.mode == "stateless":
        supplied = [
            name
            for name in (
                "species_profile",
                "individual_morphology",
                "identity_contract",
                "era_contract",
                "form_contract",
                "appearance_variant",
                "state_snapshot",
                "scene_context",
                "visual_projection",
                "asset_render_spec",
                "visual_authority",
                "visual_evidence_bundle",
            )
            if getattr(args, name, None)
        ]
        if supplied:
            raise ValueError(f"stateless lineage does not accept state artifacts: {supplied}")
        node_hashes = {field: None for field in STATE_LINEAGE_ARTIFACT_FIELDS}
    else:
        node_hashes = {
            "species_profile_sha256": hash_file(
                args.species_profile, "species-morphology-profile"
            ),
            "individual_morphology_sha256": hash_file(
                args.individual_morphology, "individual-morphology-contract"
            ),
            "identity_contract_sha256": hash_file(
                args.identity_contract, "character-identity-contract"
            ),
            "era_contract_sha256": hash_file(args.era_contract, "era-contract"),
            "form_contract_sha256": hash_file(args.form_contract, "form-contract"),
            "appearance_variant_sha256": hash_file(
                args.appearance_variant, "appearance-variant-contract"
            ),
            "state_snapshot_sha256": hash_file(args.state_snapshot, "state-snapshot"),
            "scene_context_sha256": hash_file(
                args.scene_context, "scene-context-snapshot"
            ),
            "visual_projection_sha256": hash_file(
                args.visual_projection, "visual-state-projection"
            ),
            "asset_render_spec_sha256": hash_file(
                args.asset_render_spec, "asset-render-specification"
            ),
            "visual_authority_sha256": hash_file(
                args.visual_authority, "visual-authority"
            ),
            "visual_evidence_bundle_sha256": hash_file(
                args.visual_evidence_bundle, "visual-evidence-bundle"
            ),
        }

    result = {
        "artifact_type": "state-lineage",
        "mode": args.mode,
        **node_hashes,
        "lineage_sha256": ZERO_SHA256,
    }
    return finalize_artifact(result)



def _compare(left: Any, operator: str, right: Any) -> bool:
    """Evaluate one rule comparison without raising on absent or incompatible data.

    Environment rules are optional proposals, not state mutations. A rule whose
    JSON pointer does not resolve, or whose value cannot participate in the
    requested comparison, is simply not satisfied. This mirrors event
    preconditions, where a missing path evaluates false unless the operator is
    ``not-exists``.
    """

    if operator == "exists":
        return left is not _MISSING
    if operator == "not-exists":
        return left is _MISSING
    if left is _MISSING:
        return False
    if operator == "equals":
        return left == right
    if operator == "not-equals":
        return left != right
    if operator == "contains":
        try:
            return right in left
        except TypeError:
            return False
    try:
        if operator == "greater-than":
            return left > right
        if operator == "greater-or-equal":
            return left >= right
        if operator == "less-than":
            return left < right
        if operator == "less-or-equal":
            return left <= right
    except TypeError:
        return False
    raise ValueError(f"unsupported comparison operator: {operator}")



def propose_environment_adaptations(
    state_schema: dict[str, Any],
    environment_snapshot: dict[str, Any],
    *,
    character_id: str,
    proposal_id: str,
) -> dict[str, Any]:
    for artifact in (state_schema, environment_snapshot):
        report = validate_artifact(artifact)
        if not report["ok"]:
            raise ValueError(f"invalid {artifact.get('artifact_type')}: {'; '.join(report['errors'])}")
    if state_schema.get("character_id") != character_id:
        raise ValueError("state schema character_id differs from requested character")

    matched: list[str] = []
    proposals: list[dict[str, Any]] = []
    for raw_rule in state_schema.get("environment_adaptation_rules", []):
        if not isinstance(raw_rule, dict):
            continue
        rule_id = str(raw_rule.get("rule_id") or "")
        conditions = raw_rule.get("when", [])
        if not rule_id or not isinstance(conditions, list):
            continue
        satisfied = True
        for condition in conditions:
            if not isinstance(condition, dict):
                satisfied = False
                break
            path = str(condition.get("path") or "")
            operator = str(condition.get("operator") or "equals")
            current = get_pointer(environment_snapshot, path, missing=_MISSING)
            if not _compare(current, operator, condition.get("value")):
                satisfied = False
                break
        if satisfied:
            matched.append(rule_id)
            proposal = copy.deepcopy(raw_rule.get("proposal", {}))
            if isinstance(proposal, dict):
                proposal.setdefault("rule_id", rule_id)
                # Environment rules may propose identity-affecting presentation
                # changes, but they cannot lower the approval boundary authored
                # by this protocol.
                proposal["requires_human_approval"] = True
                proposals.append(proposal)

    result = {
        "artifact_type": "appearance-adaptation-proposal",
        "proposal_id": proposal_id,
        "character_id": character_id,
        "environment_snapshot_sha256": str(environment_snapshot["environment_snapshot_sha256"]),
        "matched_rule_ids": matched,
        "proposals": proposals,
        "approval_required": True,
        "status": "proposed",
        "proposal_sha256": "0" * 64,
    }
    return finalize_artifact(result)



def select_state_references(
    bindings: list[dict[str, Any]],
    *,
    selection_id: str,
    identity_hash: str,
    era_hash: str | None,
    appearance_hash: str | None,
    state_hash: str | None,
    story_order: int,
    required_features: list[str],
    limit: int,
) -> dict[str, Any]:

    if (
        not isinstance(required_features, list)
        or any(not isinstance(value, str) or not value for value in required_features)
        or len(set(required_features)) != len(required_features)
    ):
        raise ValueError("required_features must contain unique non-empty strings")
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
        raise ValueError("reference selection limit must be a non-negative integer")
    if not isinstance(story_order, int) or isinstance(story_order, bool):
        raise ValueError("story_order must be an integer")

    eligible: list[dict[str, Any]] = []
    for binding in bindings:
        report = validate_artifact(binding)
        if not report["ok"]:
            raise ValueError(f"invalid reference binding {binding.get('binding_id')}: {'; '.join(report['errors'])}")
        canonical_source = validate_source_bytes(
            binding.get("source"),
            f"reference binding {binding.get('binding_id')}.source",
        )
        if canonical_source != binding.get("source"):
            raise ValueError(
                f"reference binding {binding.get('binding_id')}.source is not canonical"
            )
        if binding.get("identity_contract_sha256") != identity_hash:
            continue
        if binding.get("era_contract_sha256") not in {None, era_hash}:
            continue
        if binding.get("appearance_variant_sha256") not in {None, appearance_hash}:
            continue
        if binding.get("state_snapshot_sha256") not in {None, state_hash}:
            continue
        story_range = binding.get("effective_story_range", {})
        start = story_range["from_order"]
        end = story_range.get("to_order")
        if story_order < start or (end is not None and story_order > end):
            continue
        # A binding superseded for future scenes remains usable inside a closed
        # range, because to_order already bounds it. An open-ended superseded
        # binding carries no such bound, so it must not be selected at all.
        if binding.get("superseded_for_future_scenes") is True and end is None:
            continue
        eligible.append(binding)

    def source_order_key(item: dict[str, Any]) -> str:
        source = item["source"]
        return source.get("asset_id") or source.get("reference_id")

    def selected_reference(item: dict[str, Any], covers: list[str]) -> dict[str, Any]:
        return {
            "binding_id": item["binding_id"],
            "role": item["role"],
            "source": copy.deepcopy(item["source"]),
            "covers": covers,
            "intended_influence": copy.deepcopy(item.get("intended_influence", [])),
            "review_dimensions": copy.deepcopy(item.get("review_dimensions", [])),
            "unsupported_or_occluded_state": copy.deepcopy(
                item.get("unsupported_or_occluded_state", [])
            ),
            "unsupported_assumptions": copy.deepcopy(
                item.get("unsupported_assumptions", [])
            ),
        }

    remaining = set(required_features)
    selected: list[dict[str, Any]] = []
    candidates = list(eligible)
    while remaining and candidates and len(selected) < limit:
        best = min(
            candidates,
            key=lambda item: (
                -len(remaining & set(item.get("visibly_supported_state", []))),
                source_order_key(item),
                item["binding_id"],
            ),
        )
        coverage = remaining & set(best.get("visibly_supported_state", []))
        if not coverage:
            break
        selected.append(selected_reference(best, sorted(coverage)))
        remaining -= coverage
        candidates.remove(best)

    # When there are no explicit feature obligations, choose the strongest generic identity binding.
    if not required_features and eligible and limit > 0:
        ranked = sorted(
            eligible,
            key=lambda item: (
                "identity" not in item.get("intended_influence", []),
                -len(item.get("visibly_supported_state", [])),
                source_order_key(item),
            ),
        )
        selected = [selected_reference(item, []) for item in ranked[:limit]]

    result = {
        "artifact_type": "reference-selection",
        "selection_id": selection_id,
        "identity_contract_sha256": identity_hash,
        "era_contract_sha256": era_hash,
        "appearance_variant_sha256": appearance_hash,
        "state_snapshot_sha256": state_hash,
        "story_order": story_order,
        "required_state_features": list(required_features),
        "selected_references": selected,
        "unresolved_requirements": sorted(remaining),
        "selection_sha256": "0" * 64,
    }
    return finalize_artifact(result)



def parse_processes(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    data = parse_json(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and data.get("artifact_type") == "state-process":
        return [data]
    if not isinstance(data, list):
        raise ValueError("process file must contain one state-process object or an array")
    if not all(isinstance(item, dict) for item in data):
        raise ValueError("process array must contain objects")
    return data



def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage Shared State Protocol artifacts.")
    sub = parser.add_subparsers(dest="command", required=True)

    validate_cmd = sub.add_parser("validate")
    validate_cmd.add_argument("artifacts", nargs="+")

    finalize_cmd = sub.add_parser("finalize")
    finalize_cmd.add_argument("artifact")
    finalize_cmd.add_argument("--out", required=True)

    hash_cmd = sub.add_parser("hash")
    hash_cmd.add_argument("artifact")

    resolve_cmd = sub.add_parser("resolve-world")
    resolve_cmd.add_argument("--base-state", required=True)
    resolve_cmd.add_argument("--events", required=True)
    resolve_cmd.add_argument("--processes")
    resolve_cmd.add_argument("--timeline", required=True)
    resolve_cmd.add_argument("--scene-context-id", required=True)
    resolve_cmd.add_argument("--character-state-schema", action="append", default=[])
    resolve_cmd.add_argument("--story-order", type=int, required=True)
    resolve_cmd.add_argument("--story-time", required=True)
    resolve_cmd.add_argument("--snapshot-id", required=True)
    resolve_cmd.add_argument("--out", required=True)

    extract_cmd = sub.add_parser("extract-character")
    extract_cmd.add_argument("--world-snapshot", required=True)
    extract_cmd.add_argument("--character-id", required=True)
    extract_cmd.add_argument("--species-profile", required=True)
    extract_cmd.add_argument("--individual-morphology", required=True)
    extract_cmd.add_argument("--identity-contract", required=True)
    extract_cmd.add_argument("--era-contract")
    extract_cmd.add_argument("--form-contract")
    extract_cmd.add_argument("--appearance-variant")
    extract_cmd.add_argument("--snapshot-id", required=True)
    extract_cmd.add_argument("--out", required=True)

    context_cmd = sub.add_parser("build-context")
    context_cmd.add_argument("--request", required=True)
    context_cmd.add_argument("--world-snapshot", required=True)
    context_cmd.add_argument("--character-snapshot", action="append", default=[])
    context_cmd.add_argument("--out", required=True)

    projection_cmd = sub.add_parser("build-projection")
    projection_cmd.add_argument("--species-profile", required=True)
    projection_cmd.add_argument("--individual-morphology", required=True)
    projection_cmd.add_argument("--identity-contract", required=True)
    projection_cmd.add_argument("--state-snapshot", required=True)
    projection_cmd.add_argument("--scene-context", required=True)
    projection_cmd.add_argument("--request", required=True)
    projection_cmd.add_argument("--previous")
    projection_cmd.add_argument("--out", required=True)

    bundle_cmd = sub.add_parser("plan-reference-bundle")
    bundle_cmd.add_argument("--identity-contract", required=True)
    bundle_cmd.add_argument("--species-profile", required=True)
    bundle_cmd.add_argument("--individual-morphology", required=True)
    bundle_cmd.add_argument("--style-family", required=True)
    bundle_cmd.add_argument("--target-model", required=True)
    bundle_cmd.add_argument("--policy", choices=sorted(COVERAGE_POLICIES), default="series-coverage")
    bundle_cmd.add_argument("--era-contract")
    bundle_cmd.add_argument("--appearance-variant")
    bundle_cmd.add_argument("--out-dir", required=True)

    lineage_cmd = sub.add_parser("make-lineage")
    lineage_cmd.add_argument("--mode", choices=["stateless", "state-aware"], required=True)
    lineage_cmd.add_argument("--species-profile")
    lineage_cmd.add_argument("--individual-morphology")
    lineage_cmd.add_argument("--identity-contract")
    lineage_cmd.add_argument("--era-contract")
    lineage_cmd.add_argument("--form-contract")
    lineage_cmd.add_argument("--appearance-variant")
    lineage_cmd.add_argument("--state-snapshot")
    lineage_cmd.add_argument("--scene-context")
    lineage_cmd.add_argument("--visual-projection")
    lineage_cmd.add_argument("--asset-render-spec")
    lineage_cmd.add_argument("--visual-authority")
    lineage_cmd.add_argument("--visual-evidence-bundle")
    lineage_cmd.add_argument("--out", required=True)

    adapt_cmd = sub.add_parser("propose-environment-adaptations")
    adapt_cmd.add_argument("--state-schema", required=True)
    adapt_cmd.add_argument("--environment-snapshot", required=True)
    adapt_cmd.add_argument("--character-id", required=True)
    adapt_cmd.add_argument("--proposal-id", required=True)
    adapt_cmd.add_argument("--out", required=True)

    select_cmd = sub.add_parser("select-references")
    select_cmd.add_argument("--bindings", required=True, help="JSON array or object with a bindings array")
    select_cmd.add_argument("--selection-id", required=True)
    select_cmd.add_argument("--identity-contract", required=True)
    select_cmd.add_argument("--era-contract")
    select_cmd.add_argument("--appearance-variant")
    select_cmd.add_argument("--state-snapshot")
    select_cmd.add_argument("--story-order", type=int, required=True)
    select_cmd.add_argument("--required-feature", action="append", default=[])
    select_cmd.add_argument("--limit", type=int, default=3)
    select_cmd.add_argument("--out", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            reports = []
            for item in args.artifacts:
                data = load_json(Path(item))
                report = validate_artifact(data)
                report["file"] = item
                reports.append(report)
            result = {"ok": all(item["ok"] for item in reports), "artifacts": reports}
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["ok"] else 1

        if args.command == "finalize":
            data = finalize_artifact(load_json(Path(args.artifact)))
            report = validate_artifact(data)
            if not report["ok"]:
                raise ValueError("invalid finalized artifact: " + "; ".join(report["errors"]))
            write_json(Path(args.out), data)
            print(json.dumps(data, ensure_ascii=False, indent=2))
            return 0

        if args.command == "hash":
            data = load_json(Path(args.artifact))
            print(json.dumps({"artifact_type": data.get("artifact_type"), "sha256": artifact_hash(data)}, indent=2))
            return 0

        if args.command == "resolve-world":
            base = load_json(Path(args.base_state))
            events = load_jsonl(Path(args.events))
            processes = parse_processes(args.processes)
            result = resolve_world(
                base_state=base, events=events, processes=processes,
                timeline_id=args.timeline, story_order=args.story_order,
                story_time=args.story_time, snapshot_id=args.snapshot_id,
                scene_context_id=args.scene_context_id,
                character_state_schemas=[load_validated_artifact(Path(v), "character-state-schema") for v in args.character_state_schema],
            )
            report = validate_artifact(result)
            if not report["ok"]:
                raise ValueError("resolved world snapshot is invalid: " + "; ".join(report["errors"]))
            write_json(Path(args.out), result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        if args.command == "extract-character":
            species_profile = load_validated_artifact(Path(args.species_profile), "species-morphology-profile")
            individual_morphology = load_validated_artifact(Path(args.individual_morphology), "individual-morphology-contract")
            identity = load_validated_artifact(Path(args.identity_contract), "character-identity-contract")
            result = extract_character_snapshot(
                load_json(Path(args.world_snapshot)), character_id=args.character_id,
                species_profile_hash=artifact_hash(species_profile),
                individual_morphology_hash=artifact_hash(individual_morphology),
                identity_hash=artifact_hash(identity),
                era_hash=artifact_hash(load_validated_artifact(Path(args.era_contract), "era-contract")) if args.era_contract else None,
                form_hash=artifact_hash(load_validated_artifact(Path(args.form_contract), "form-contract")) if args.form_contract else None,
                appearance_hash=artifact_hash(load_validated_artifact(Path(args.appearance_variant), "appearance-variant-contract")) if args.appearance_variant else None,
                snapshot_id=args.snapshot_id,
            )
            report = validate_artifact(result)
            if not report["ok"]:
                raise ValueError("character snapshot is invalid: " + "; ".join(report["errors"]))
            write_json(Path(args.out), result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        if args.command == "build-context":
            request = load_json(Path(args.request))
            world = load_json(Path(args.world_snapshot))
            snapshots = [load_json(Path(path)) for path in args.character_snapshot]
            result = build_scene_context(request, world, snapshots)
            report = validate_artifact(result)
            if not report["ok"]:
                raise ValueError("scene context is invalid: " + "; ".join(report["errors"]))
            write_json(Path(args.out), result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        if args.command == "build-projection":
            result = build_projection(
                load_validated_artifact(Path(args.identity_contract), "character-identity-contract"),
                load_validated_artifact(Path(args.species_profile), "species-morphology-profile"),
                load_validated_artifact(Path(args.individual_morphology), "individual-morphology-contract"),
                load_json(Path(args.state_snapshot)),
                load_json(Path(args.scene_context)),
                load_json(Path(args.request)),
                load_json(Path(args.previous)) if args.previous else None,
            )
            report = validate_artifact(result)
            if not report["ok"]:
                raise ValueError("visual state projection is invalid: " + "; ".join(report["errors"]))
            write_json(Path(args.out), result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        if args.command == "plan-reference-bundle":
            result = plan_reference_bundle(
                load_validated_artifact(Path(args.identity_contract), "character-identity-contract"),
                species_profile=load_validated_artifact(Path(args.species_profile), "species-morphology-profile"),
                individual_morphology=load_validated_artifact(Path(args.individual_morphology), "individual-morphology-contract"),
                style_family_id=args.style_family,
                target_model=args.target_model, policy=args.policy, out_dir=Path(args.out_dir),
                era_contract=load_validated_artifact(Path(args.era_contract), "era-contract") if args.era_contract else None,
                appearance_variant=load_validated_artifact(Path(args.appearance_variant), "appearance-variant-contract") if args.appearance_variant else None,
            )
            report = validate_artifact(result)
            if not report["ok"]:
                raise ValueError("reference bundle plan is invalid: " + "; ".join(report["errors"]))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        if args.command == "make-lineage":
            result = build_lineage(args)
            report = validate_artifact(result)
            if not report["ok"]:
                raise ValueError("state lineage is invalid: " + "; ".join(report["errors"]))
            write_json(Path(args.out), result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        if args.command == "propose-environment-adaptations":
            result = propose_environment_adaptations(
                load_json(Path(args.state_schema)), load_json(Path(args.environment_snapshot)),
                character_id=args.character_id, proposal_id=args.proposal_id,
            )
            report = validate_artifact(result)
            if not report["ok"]:
                raise ValueError("appearance adaptation proposal is invalid: " + "; ".join(report["errors"]))
            write_json(Path(args.out), result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        if args.command == "select-references":
            raw = parse_json(Path(args.bindings).read_text(encoding="utf-8"))
            bindings = raw.get("bindings", []) if isinstance(raw, dict) else raw
            if not isinstance(bindings, list) or not all(isinstance(item, dict) for item in bindings):
                raise ValueError("bindings file must be an array or an object containing a bindings array")
            result = select_state_references(
                bindings, selection_id=args.selection_id,
                identity_hash=artifact_hash(load_validated_artifact(Path(args.identity_contract), "character-identity-contract")),
                era_hash=artifact_hash(load_validated_artifact(Path(args.era_contract), "era-contract")) if args.era_contract else None,
                appearance_hash=artifact_hash(load_validated_artifact(Path(args.appearance_variant), "appearance-variant-contract")) if args.appearance_variant else None,
                state_hash=artifact_hash(load_json(Path(args.state_snapshot))) if args.state_snapshot else None,
                story_order=args.story_order, required_features=args.required_feature, limit=args.limit,
            )
            report = validate_artifact(result)
            if not report["ok"]:
                raise ValueError("reference selection is invalid: " + "; ".join(report["errors"]))
            write_json(Path(args.out), result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        raise AssertionError(args.command)
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OSError, RecursionError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1



if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
