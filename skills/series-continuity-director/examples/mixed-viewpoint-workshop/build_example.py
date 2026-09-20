#!/usr/bin/env python3
"""Build the deterministic mixed-viewpoint canonical example."""
from __future__ import annotations

import argparse
import filecmp
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

EXAMPLE = Path(__file__).resolve().parent
ROOT = EXAMPLE.parents[1]
SOURCE = EXAMPLE / "source"
GENERATED = EXAMPLE / "generated"

sys.path.insert(0, str(ROOT / "scripts"))
from state_protocol import (  # noqa: E402
    artifact_hash as state_artifact_hash,
    build_projection,
    build_scene_context,
    extract_character_snapshot,
    finalize_artifact as finalize_state,
    load_json,
    load_jsonl,
    resolve_world,
    validate_artifact as validate_state_artifact,
    write_json,
)
from viewpoint_protocol import (  # noqa: E402
    build_continuity_ledger,
    finalize_artifact as finalize_viewpoint,
    validate_artifact as validate_viewpoint_artifact,
)

STORY_ORDER = 10
STORY_TIME = "story:EP01-SC03-start"
SCENE_ID = "SC-WORKSHOP-01"


def require_state(value: dict[str, Any], label: str) -> None:
    report = validate_state_artifact(value)
    if not report.get("ok"):
        raise ValueError(f"invalid state artifact {label}: {'; '.join(report.get('errors', []))}")


def require_viewpoint(value: dict[str, Any], label: str) -> None:
    report = validate_viewpoint_artifact(value)
    if not report.get("ok"):
        raise ValueError(f"invalid viewpoint artifact {label}: {'; '.join(report.get('errors', []))}")


def write_state(output: Path, rel: str, value: dict[str, Any]) -> dict[str, Any]:
    require_state(value, rel)
    write_json(output / rel, value)
    return value


def write_viewpoint(output: Path, rel: str, value: dict[str, Any]) -> dict[str, Any]:
    require_viewpoint(value, rel)
    write_json(output / rel, value)
    return value


def state_schema(character_id: str, identity_hash: str, initial: dict[str, Any]) -> dict[str, Any]:
    paths = [
        ("/physical_state/left_side_injury", "physical", "object", "conditional"),
        ("/wardrobe_state/outer_layer", "wardrobe", "string", "always-when-visible"),
        ("/wardrobe_state/inner_layer", "wardrobe", "string", "always-when-visible"),
        ("/inventory_state/items", "inventory", "array", "conditional"),
        ("/emotional_state/felt", "emotion", "string", "never-direct"),
        ("/emotional_state/expressed", "emotion", "string", "conditional"),
        ("/emotional_state/masked", "emotion", "string", "conditional"),
        ("/emotional_state/physiological", "emotion", "string", "conditional"),
        ("/performance_state/posture", "performance", "string", "conditional"),
        ("/knowledge_state/knows_pendant_damage", "knowledge", "boolean", "never-direct"),
    ]
    return {
        "artifact_type": "character-state-schema",
        "state_schema_id": f"CSS-{character_id}",
        "character_id": character_id,
        "identity_contract_sha256": identity_hash,
        "state_paths": [
            {
                "path": path,
                "state_domain": domain,
                "value_type": value_type,
                "allowed_persistence": ["scene-local", "temporary-until-cleared", "persistent-until-superseded"],
                "default_value": None,
                "visual_translation": {"policy": "project only when visible or behaviorally relevant"},
                "prompt_relevance": relevance,
                "notes": "Example path for deterministic state resolution.",
            }
            for path, domain, value_type, relevance in paths
        ],
        "initial_state": initial,
        "state_machines": [],
        "environment_adaptation_rules": [],
        "projection_rules": [],
        "notes": ["The example keeps hidden injury state separate from visible performance cues."],
    }


def make_relationship(world: dict[str, Any]) -> dict[str, Any]:
    rel = world["relationships"]["REL-C01-C02"]
    return finalize_state({
        "artifact_type": "relationship-state",
        "relationship_id": "REL-C01-C02",
        "timeline_id": "main",
        "story_order": STORY_ORDER,
        **rel,
        "last_major_event": "EV-C01-INJURY",
        "relationship_state_sha256": "0" * 64,
    })


def make_environment(world: dict[str, Any]) -> dict[str, Any]:
    env = world["environments"]["ENV-WORKSHOP"]
    return finalize_state({
        "artifact_type": "environment-snapshot",
        "environment_snapshot_id": "ENV-WORKSHOP-10",
        "location_id": env["location_id"],
        "timeline_id": "main",
        "story_order": STORY_ORDER,
        "season": env["season"],
        "time_of_day": env["time_of_day"],
        "weather": env["weather"],
        "temperature_c": env["temperature_c"],
        "humidity_percent": env["humidity_percent"],
        "wind": env["wind"],
        "precipitation": env["precipitation"],
        "water_exposure": env["water_exposure"],
        "light_context": env["light_context"],
        "culture_context_refs": env["culture_context_refs"],
        "dress_norms": env["dress_norms"],
        "surface_conditions": env["surface_conditions"],
        "approved_adaptation_rules": env["approved_adaptation_rules"],
        "uncertainties": env["uncertainties"],
        "environment_snapshot_sha256": "0" * 64,
    })


def make_wardrobe(character_id: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    wardrobe = snapshot["wardrobe_state"]
    equipment = snapshot["equipment_state"]
    layers = [
        {"item_id": f"{character_id}-outer", "state": "worn", "closure": "closed", "fastener_state": "secure", "layer_order": 2, "condition": {"description": wardrobe.get("outer_layer")}, "pocket_contents": []},
        {"item_id": f"{character_id}-inner", "state": "worn", "closure": "closed", "fastener_state": "none", "layer_order": 1, "condition": {"description": wardrobe.get("inner_layer")}, "pocket_contents": []},
    ]
    if equipment:
        layers.append({"item_id": f"{character_id}-equipment", "state": "worn", "closure": "n/a", "fastener_state": "secure", "layer_order": 3, "condition": equipment, "pocket_contents": []})
    return finalize_state({
        "artifact_type": "wardrobe-state",
        "wardrobe_state_id": f"WARD-{character_id}-10",
        "character_id": character_id,
        "outfit_variant_id": f"{character_id}-workshop",
        "layers": layers,
        "condition": {"summary": wardrobe.get("condition")},
        "wardrobe_state_sha256": "0" * 64,
    })


def make_inventory(character_id: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    items = []
    for item_id in snapshot["inventory_state"].get("items", []):
        items.append({
            "item_id": item_id,
            "owned_by": "archive",
            "possessed_by": character_id,
            "carried_by": character_id,
            "equipped_to": None,
            "stored_at": None,
            "state": "damaged",
            "condition": {"description": "cracked glass and bent silver rim"},
        })
    return finalize_state({
        "artifact_type": "inventory-state",
        "inventory_state_id": f"INV-{character_id}-10",
        "owner_id": character_id,
        "items": items,
        "inventory_state_sha256": "0" * 64,
    })


def shot_specs(state_hashes: dict[str, str]) -> list[dict[str, Any]]:
    common = {
        "artifact_type": "shot-camera-spec",
        "scene_id": SCENE_ID,
        "state_snapshot_sha256_by_character": state_hashes,
    }
    specs = [
        {
            **common,
            "shot_id": "SC-WORKSHOP-01-SH01", "order_index": 1,
            "viewpoint_profile_id": "external-character-aligned-third-person", "profile_family": "external", "camera_ownership": "external_camera", "camera_owner_character_id": None,
            "knowledge_scope": "character_restricted", "focal_character_ids": ["C01"], "point_of_audition": "objective_mix", "audition_character_id": None,
            "coverage_role": "establishing master", "camera_position": "outside the frame-left workshop doorway, looking toward the central workbench", "shot_scale": "wide full-body two-shot", "camera_height": "chest height", "angle": "level three-quarter angle", "lens_behavior": "moderate perspective that keeps both characters and the workbench readable",
            "movement": {"type": "locked", "cause": "establish geography, relationship distance, and the concealed injury performance", "start_relation": "doorway frame-left, C01 nearest and C02 beyond the workbench", "path": "remain fixed through the opening hold", "speed_and_amplitude": "no travel, minor natural stability only", "subject_relation": "C01 enters the near left area while C02 remains behind the workbench", "occlusion_risk": "doorframe may cover a narrow background edge only", "landing_composition": "both characters and P01 are readable with the workbench between them"},
            "screen_direction": "C01 faces and moves screen-right toward C02", "axis_side": "doorway side of the C01 to C02 axis", "eyeline_relation": "C01 and C02 eyelines meet across the workbench", "visible_subjects": ["C01", "C02"], "visible_body_regions": {"C01": ["full body"], "C02": ["full body"]}, "prop_ownership": {"P01": "C02 right hand"},
            "start_anchor": "C01 at frame-left doorway, C02 behind the workbench with P01 low in the right hand", "end_anchor": "C01 stops at the near workbench edge as C02 begins to raise P01", "knowledge_visibility": ["The audience sees that P01 is damaged but not the concealed bandage."], "accepted_variation": ["minor tool arrangement", "small tail movement"], "review_dimensions": ["axis continuity", "identity", "prop ownership", "injury concealment"], "camera_spec_sha256": "0" * 64,
        },
        {
            **common,
            "shot_id": "SC-WORKSHOP-01-SH02", "order_index": 2,
            "viewpoint_profile_id": "external-character-aligned-third-person", "profile_family": "external", "camera_ownership": "external_camera", "camera_owner_character_id": None,
            "knowledge_scope": "character_restricted", "focal_character_ids": ["C01"], "point_of_audition": "objective_mix", "audition_character_id": None,
            "coverage_role": "aligned medium approach", "camera_position": "frame-left of C01, parallel to the workbench", "shot_scale": "medium full", "camera_height": "upper torso height", "angle": "slight rear three-quarter on C01", "lens_behavior": "stable moderate lens that keeps C01 body language and C02 target clear",
            "movement": {"type": "track", "cause": "follow C01 final two steps and guarded left-side posture", "start_relation": "camera is outside C01 left-rear quarter", "path": "track screen-right parallel to C01 until the workbench edge", "speed_and_amplitude": "slow two-step track", "subject_relation": "keep C01 dominant while C02 remains visible beyond the workbench", "occlusion_risk": "C01 shoulder may briefly cover P01 before the next shot", "landing_composition": "C01 stops foreground-left and looks toward P01 held by C02"},
            "screen_direction": "C01 continues screen-right", "axis_side": "doorway side of the interaction axis", "eyeline_relation": "C01 gaze lands on C02 right hand", "visible_subjects": ["C01", "C02"], "visible_body_regions": {"C01": ["head", "torso", "arms", "legs"], "C02": ["head", "upper torso", "right hand"]}, "prop_ownership": {"P01": "C02 right hand"},
            "start_anchor": "C01 begins two steps from the workbench", "end_anchor": "C01 stops with the left side slightly protected and gaze on P01", "knowledge_visibility": ["C01 notices P01 damage at the landing."], "accepted_variation": ["exact step length"], "review_dimensions": ["screen direction", "guarded posture", "eyeline target", "prop ownership"], "camera_spec_sha256": "0" * 64,
        },
        {
            **common,
            "shot_id": "SC-WORKSHOP-01-SH03", "order_index": 3,
            "viewpoint_profile_id": "over-the-shoulder", "profile_family": "external", "camera_ownership": "external_camera", "camera_owner_character_id": None,
            "knowledge_scope": "character_restricted", "focal_character_ids": ["C01"], "point_of_audition": "objective_mix", "audition_character_id": None,
            "coverage_role": "over-the-shoulder pendant reveal", "camera_position": "just behind C01 right shoulder, aimed across the workbench at C02", "shot_scale": "over-the-shoulder medium close", "camera_height": "C01 eye height", "angle": "level over C01 right shoulder", "lens_behavior": "moderate compression that keeps P01 and C02 face readable",
            "movement": {"type": "locked", "cause": "reveal P01 damage through C01 attention", "start_relation": "C01 right shoulder and ear edge frame the near foreground", "path": "hold while C02 raises P01", "speed_and_amplitude": "no travel", "subject_relation": "C02 face and right hand remain beyond the pendant", "occlusion_risk": "C01 foreground shoulder must not cover P01 or C02 eyes", "landing_composition": "P01 reaches C01 eye level between the two faces"},
            "screen_direction": "C01 foreground faces screen-right and C02 faces screen-left", "axis_side": "same doorway side of the axis", "eyeline_relation": "C01 eyeline converges on P01 while C02 watches C01", "visible_subjects": ["C01", "C02"], "visible_body_regions": {"C01": ["right shoulder", "right ear edge", "partial head"], "C02": ["face", "upper torso", "right hand"]}, "prop_ownership": {"P01": "C02 right hand"},
            "start_anchor": "P01 below C02 chest with C01 shoulder foreground", "end_anchor": "P01 held at C01 eye level and C01 right hand begins to rise", "knowledge_visibility": ["P01 damage is clearly revealed; C01 injury remains concealed."], "accepted_variation": ["small foreground shoulder width"], "review_dimensions": ["foreground anatomy", "eyeline", "P01 damage", "spectacle continuity"], "camera_spec_sha256": "0" * 64,
        },
        {
            **common,
            "shot_id": "SC-WORKSHOP-01-SH04", "order_index": 4,
            "viewpoint_profile_id": "embodied-first-person", "profile_family": "embodied-first-person", "camera_ownership": "character_body", "camera_owner_character_id": "C01",
            "knowledge_scope": "character_restricted", "focal_character_ids": ["C01"], "point_of_audition": "character_subjective", "audition_character_id": "C01",
            "coverage_role": "subjective handoff insert", "camera_position": "C01 eye position facing across the workbench", "shot_scale": "first-person hand and object close view", "camera_height": "C01 eye height", "angle": "slight look down toward the handoff", "lens_behavior": "natural embodied perspective with C01 right hand entering from lower-right",
            "movement": {"type": "held", "cause": "C01 follows P01 down into the receiving hand", "start_relation": "view begins on C02 face and P01 at eye level", "path": "gaze lowers with the object as C02 places it into C01 right palm", "speed_and_amplitude": "small controlled downward gaze", "subject_relation": "C02 stays beyond the object and releases after C01 fingers close", "occlusion_risk": "hands may briefly occlude the pendant rim but ownership must remain readable", "landing_composition": "P01 rests in C01 right palm with C02 hand withdrawing"},
            "screen_direction": "C02 remains centered beyond the handoff", "axis_side": "camera owner remains on C01 side of the axis", "eyeline_relation": "gaze follows P01 from C02 face to C01 hand", "visible_subjects": ["C01", "C02"], "visible_body_regions": {"C01": ["right hand", "right wrist"], "C02": ["face", "right hand", "upper torso"]}, "prop_ownership": {"P01": "C01 right hand after visible transfer"},
            "start_anchor": "P01 in C02 right fingers at eye level", "end_anchor": "P01 in C01 right palm while C02 hand releases", "knowledge_visibility": ["C01 directly inspects the crack; concealed injury remains offscreen."], "accepted_variation": ["minor finger spacing"], "review_dimensions": ["camera-owner hand ownership", "transfer order", "P01 orientation", "subjective audition"], "camera_spec_sha256": "0" * 64,
        },
        {
            **common,
            "shot_id": "SC-WORKSHOP-01-SH05", "order_index": 5,
            "viewpoint_profile_id": "external-character-aligned-third-person", "profile_family": "external", "camera_ownership": "external_camera", "camera_owner_character_id": None,
            "knowledge_scope": "character_restricted", "focal_character_ids": ["C01"], "point_of_audition": "objective_mix", "audition_character_id": None,
            "coverage_role": "external reaction close-up", "camera_position": "workbench side, three-quarter on C01 face and right hand", "shot_scale": "close-up", "camera_height": "C01 face height", "angle": "slight right three-quarter", "lens_behavior": "gentle portrait compression with P01 low in frame",
            "movement": {"type": "locked", "cause": "show C01 controlled reaction after seeing the damage", "start_relation": "camera begins on C01 eyes and P01 in the lower frame", "path": "hold through one breath and a small ear response", "speed_and_amplitude": "no travel", "subject_relation": "C01 face dominates while C02 remains soft in background", "occlusion_risk": "P01 must remain visible below the muzzle", "landing_composition": "C01 eyes lift from P01 to C02 while the right hand keeps the pendant"},
            "screen_direction": "C01 faces screen-right toward C02", "axis_side": "same doorway side of the axis", "eyeline_relation": "C01 gaze moves from P01 to C02", "visible_subjects": ["C01", "C02"], "visible_body_regions": {"C01": ["face", "ears", "right hand", "upper torso"], "C02": ["soft background face"]}, "prop_ownership": {"P01": "C01 right hand"},
            "start_anchor": "C01 looks down at P01 in the right hand", "end_anchor": "C01 looks up at C02 with guarded concern", "knowledge_visibility": ["The audience reads concern and guarded posture without seeing the injury."], "accepted_variation": ["small eye timing"], "review_dimensions": ["face identity", "left ear clip", "P01 ownership", "masked emotion"], "camera_spec_sha256": "0" * 64,
        },
        {
            **common,
            "shot_id": "SC-WORKSHOP-01-SH06", "order_index": 6,
            "viewpoint_profile_id": "external-character-aligned-third-person", "profile_family": "external", "camera_ownership": "external_camera", "camera_owner_character_id": None,
            "knowledge_scope": "shared_restricted", "focal_character_ids": ["C01", "C02"], "point_of_audition": "objective_mix", "audition_character_id": None,
            "coverage_role": "external landing master", "camera_position": "slightly wider on the same doorway side, centered on both characters and the workbench", "shot_scale": "medium wide two-shot", "camera_height": "chest height", "angle": "level three-quarter", "lens_behavior": "stable moderate lens matching the opening geography",
            "movement": {"type": "dolly", "cause": "restore shared geography and create a continuation-ready landing", "start_relation": "camera begins close on C01 reaction side", "path": "dolly back a short distance along the same axis side", "speed_and_amplitude": "slow one-meter retreat", "subject_relation": "keep both characters on their established screen sides", "occlusion_risk": "workbench edge remains below both hands", "landing_composition": "C01 holds P01 at the near workbench edge while C02 waits across from them"},
            "screen_direction": "C01 remains screen-left facing right; C02 remains screen-right facing left", "axis_side": "doorway side of the axis", "eyeline_relation": "both characters look toward each other across P01", "visible_subjects": ["C01", "C02"], "visible_body_regions": {"C01": ["head", "torso", "arms", "hands"], "C02": ["head", "torso", "arms", "hands"]}, "prop_ownership": {"P01": "C01 right hand"},
            "start_anchor": "C01 reaction close-up with P01 in hand", "end_anchor": "both characters settle across the workbench with P01 visibly in C01 right hand", "knowledge_visibility": ["Both characters and the audience know the pendant damage; injury remains concealed."], "accepted_variation": ["minor stance width"], "review_dimensions": ["re-established geography", "prop ownership", "state continuity", "continuation endpoint"], "camera_spec_sha256": "0" * 64,
        },
    ]
    return [finalize_viewpoint(item) for item in specs]


def transition_specs() -> list[dict[str, Any]]:
    raw = [
        ("VT-WORKSHOP-01", "SC-WORKSHOP-01-SH01", "SC-WORKSHOP-01-SH02", "external-character-aligned-third-person", "external-character-aligned-third-person", "C01 begins the final two steps toward the workbench", "match-on-action", False, False, False, "none", [], ["C01 continues screen-right", "P01 remains in C02 right hand", "C01 injury state remains concealed"]),
        ("VT-WORKSHOP-02", "SC-WORKSHOP-01-SH02", "SC-WORKSHOP-01-SH03", "external-character-aligned-third-person", "over-the-shoulder", "C01 gaze lands on P01 as C02 raises it", "eyeline-cut", False, False, False, "C01 learns the visible extent of P01 damage", [], ["P01 remains in C02 right hand", "axis side remains unchanged", "C01 shoulder foreground aligns with the prior position"]),
        ("VT-WORKSHOP-03", "SC-WORKSHOP-01-SH03", "SC-WORKSHOP-01-SH04", "over-the-shoulder", "embodied-first-person", "P01 reaches C01 eye level and C01 right hand rises", "match-on-action", True, False, True, "none", ["EV-TRANSFER-P01"], ["P01 transfer state changes from C02 to C01 during the shot", "C02 remains beyond P01", "warm work light stays frame-right"]),
        ("VT-WORKSHOP-04", "SC-WORKSHOP-01-SH04", "SC-WORKSHOP-01-SH05", "embodied-first-person", "external-character-aligned-third-person", "C02 hand withdraws and C01 breath catches once", "sound-bridge", True, False, True, "none", [], ["P01 remains in C01 right hand", "C01 posture continues to protect the left side", "C02 remains across the workbench"]),
        ("VT-WORKSHOP-05", "SC-WORKSHOP-01-SH05", "SC-WORKSHOP-01-SH06", "external-character-aligned-third-person", "external-character-aligned-third-person", "C01 raises the eyes from P01 to C02", "re-establishing-cut", False, True, False, "none", [], ["P01 remains in C01 right hand", "screen sides return to the established master", "injury state remains concealed"]),
    ]
    result = []
    for tid, frm, to, fp, tp, trigger, bridge, own, foc, aud, know, events, reqs in raw:
        result.append(finalize_viewpoint({
            "artifact_type": "viewpoint-transition",
            "transition_id": tid,
            "scene_id": SCENE_ID,
            "from_shot": frm,
            "to_shot": to,
            "from_profile": fp,
            "to_profile": tp,
            "trigger": trigger,
            "bridge_type": bridge,
            "changes_camera_ownership": own,
            "changes_knowledge_scope": foc,
            "changes_point_of_audition": aud,
            "knowledge_change": know,
            "state_change_event_ids": events,
            "continuity_requirements": reqs,
            "transition_sha256": "0" * 64,
        }))
    return result


def shot_projection(shot: dict[str, Any], c01_projection: dict[str, Any], c02_projection: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    shot_id = shot["shot_id"]
    c01_visible = [item.get("wording") for item in c01_projection["visible_identity_features"]]
    c02_visible = [item.get("wording") for item in c02_projection["visible_identity_features"]]
    visible_identity = []
    if "C01" in shot["visible_subjects"]:
        if shot["profile_family"] == "embodied-first-person":
            visible_identity.append("C01 right hand, glove, wrist proportions, and fur colors remain consistent with approved references")
        else:
            visible_identity.extend(c01_visible)
    if "C02" in shot["visible_subjects"]:
        visible_identity.extend(c02_visible)
    state_obligations = []
    if shot_id in {"SC-WORKSHOP-01-SH01", "SC-WORKSHOP-01-SH02", "SC-WORKSHOP-01-SH03"}:
        state_obligations.append("P01 remains in C02 right hand")
    else:
        state_obligations.append("P01 is visibly supported in C01 right hand as the planned post-handoff state")
    state_obligations.append("C01 concealed left-side injury affects posture but remains covered")
    projection = {
        "artifact_type": "shot-visual-projection",
        "shot_id": shot_id,
        "scene_id": SCENE_ID,
        "scene_context_sha256": context["context_snapshot_sha256"],
        "camera_spec_sha256": shot["camera_spec_sha256"],
        "viewpoint_profile_id": shot["viewpoint_profile_id"],
        "state_snapshot_sha256_by_character": shot["state_snapshot_sha256_by_character"],
        "visible_identity_obligations": visible_identity,
        "visible_state_obligations": state_obligations,
        "wardrobe_and_inventory_obligations": ["C01 dark mechanic jacket and fingerless gloves remain stable", "C02 cream vest, rolled white sleeves, and brass spectacles remain stable"],
        "relationship_and_performance": ["trusted colleagues maintain cautious distance across the workbench", "C01 masks concern with professional control", "C02 handles P01 gently and watches C01 reaction"],
        "environment_and_lighting": ["cool rain window remains frame-left", "warm work lamps remain frame-right", "humid workshop air and dry interior surfaces remain consistent"],
        "occluded_or_unavailable": ["C01 bandage and injury remain under clothing", "unseen rear markings are not inferred"],
        "reference_requirements": ["angle-matched C01 identity reference when C01 face is visible", "angle-matched C02 identity and spectacles reference", "hand detail reference for the handoff shot"],
        "projection_sha256": "0" * 64,
    }
    return finalize_viewpoint(projection)


def shot_request(shot: dict[str, Any], projection: dict[str, Any], identity_hashes: dict[str, str], state_hashes: dict[str, str], context: dict[str, Any], species_hashes: dict[str, str], individual_hashes: dict[str, str]) -> dict[str, Any]:
    deliverable = "boundary-frame" if shot["order_index"] in {1, 4, 6} else "shot-reference"
    return finalize_viewpoint({
        "artifact_type": "shot-request",
        "request_id": f"REQ-{shot['shot_id']}",
        "scene_id": SCENE_ID,
        "shot_id": shot["shot_id"],
        "deliverable": deliverable,
        "species_profile_sha256_by_character": species_hashes,
        "individual_morphology_sha256_by_character": individual_hashes,
        "visible_morphology_feature_refs_by_character": {cid: (["carrier"] if cid in shot["visible_subjects"] else []) for cid in identity_hashes},
        "identity_contract_sha256_by_character": identity_hashes,
        "state_snapshot_sha256_by_character": state_hashes,
        "scene_context_sha256": context["context_snapshot_sha256"],
        "camera_spec_sha256": shot["camera_spec_sha256"],
        "shot_projection_sha256": projection["projection_sha256"],
        "viewpoint_profile_id": shot["viewpoint_profile_id"],
        "visible_identity_obligations": projection["visible_identity_obligations"],
        "visible_state_obligations": projection["visible_state_obligations"],
        "selected_reference_candidates": [],
        "required_output": {
            "prompt_language": "English",
            "aspect_ratio": "16:9",
            "camera_and_crop": f"{shot['shot_scale']}, {shot['camera_position']}, {shot['angle']}",
            "style_family_policy": "Use the approved series style family as one coherent finish grammar and keep it stable across all shots.",
            "state_lineage_required": True,
        },
        "request_sha256": "0" * 64,
    })


def prompt_for_shot(shot: dict[str, Any]) -> str:
    prompts = {
        "SC-WORKSHOP-01-SH01": "External character-aligned third-person wide master from the frame-left workshop doorway. C01, a tall gray wolf mechanic in a dark blue work jacket, enters from the left and stops at the near edge of the central workbench while subtly protecting the concealed left-side injury. C02, a russet fox archivist in a cream vest and round brass spectacles, stands beyond the workbench holding the damaged silver pendant P01 low in the right hand. Cool rain window light remains frame-left, warm work lamps remain frame-right, and both full-body silhouettes, the workbench, and the established screen direction stay readable.",
        "SC-WORKSHOP-01-SH02": "Track slowly screen-right beside C01 for the final two steps toward the workbench. Keep the camera external at upper-torso height and preserve the same axis side. C01 remains the focal character, the left side guarded and breathing controlled, while C02 and the damaged pendant stay visible beyond the workbench. Land as C01 stops and looks toward C02 right hand.",
        "SC-WORKSHOP-01-SH03": "Over C01 right shoulder, hold a medium-close view across the workbench. C01 shoulder and ear edge form a clean foreground frame while C02 raises the damaged silver pendant in the right hand to C01 eye level. Keep C02 green eyes, brass spectacles, fox muzzle, and careful hand structure clear. P01 remains between the two faces and the concealed injury stays hidden.",
        "SC-WORKSHOP-01-SH04": "Embodied first-person view from C01 eye height. Follow the damaged pendant down with a small controlled gaze movement as C02 places it into C01 right palm. C01 gloved right hand enters from the lower-right; C02 right fingers release only after C01 fingers close. Keep C02 beyond the object, preserve P01 orientation and damage, and let the workshop sound become briefly character-subjective with one restrained breath.",
        "SC-WORKSHOP-01-SH05": "External character-aligned reaction close-up from the workbench side. C01 holds P01 low in the right hand, studies the crack, takes one guarded breath, then raises amber eyes toward C02. Preserve heavy brows, pale muzzle, subject-left ear clip, concealed injury posture, and controlled professional expression. C02 remains soft in the background across the workbench.",
        "SC-WORKSHOP-01-SH06": "Return to an external medium-wide landing master from the established doorway side. Dolly back slowly until both characters are readable on their original screen sides. C01 remains screen-left with P01 visibly supported in the right hand; C02 remains screen-right across the workbench. Both settle into a quiet continuation-ready hold under cool rain light from frame-left and warm work light from frame-right.",
    }
    return prompts[shot["shot_id"]]


def build(output_root: Path) -> None:
    generated = output_root / "generated"
    for sub in ("shots", "transitions", "shot-projections", "shot-requests", "proposed-text"):
        (generated / sub).mkdir(parents=True, exist_ok=True)

    identity_c01 = load_json(SOURCE / "character-identity-C01.json")
    identity_c02 = load_json(SOURCE / "character-identity-C02.json")
    require_state(identity_c01, "identity C01")
    require_state(identity_c02, "identity C02")
    identity_hashes = {"C01": state_artifact_hash(identity_c01), "C02": state_artifact_hash(identity_c02)}

    species = {cid: load_json(SOURCE / f"species-morphology-{cid}.json") for cid in ("C01", "C02")}
    individuals = {cid: load_json(SOURCE / f"individual-morphology-{cid}.json") for cid in ("C01", "C02")}
    species_hashes = {cid: state_artifact_hash(v) for cid, v in species.items()}
    individual_hashes = {cid: state_artifact_hash(v) for cid, v in individuals.items()}
    world_base = load_json(SOURCE / "world-state-base.json")
    events = load_jsonl(SOURCE / "events.jsonl")
    for event in events:
        require_state(event, event["event_id"])
    world_snapshot = resolve_world(base_state=world_base, events=events, processes=[], timeline_id="main", story_order=STORY_ORDER, story_time=STORY_TIME, snapshot_id="WORLD-main-10", scene_context_id=SCENE_ID, character_state_schemas=[state_schema(cid, identity_hashes[cid], world_base["characters"][cid]) for cid in ("C01", "C02")])
    write_state(generated, "world-state-snapshot.json", world_snapshot)

    snapshots = {}
    for cid in ("C01", "C02"):
        identity = identity_c01 if cid == "C01" else identity_c02
        schema = state_schema(cid, identity_hashes[cid], world_base["characters"][cid])
        require_state(schema, f"state schema {cid}")
        write_json(generated / f"character-state-schema-{cid}.json", schema)
        snapshot = extract_character_snapshot(world_snapshot, character_id=cid, species_profile_hash=species_hashes[cid], individual_morphology_hash=individual_hashes[cid], identity_hash=identity_hashes[cid], era_hash=None, form_hash=None, appearance_hash=None, snapshot_id=f"{cid}-main-10")
        snapshots[cid] = write_state(generated, f"character-state-snapshot-{cid}.json", snapshot)

    relationship = write_state(generated, "relationship-state.json", make_relationship(world_snapshot["entities"]))
    environment = write_state(generated, "environment-snapshot.json", make_environment(world_snapshot["entities"]))
    for cid in ("C01", "C02"):
        write_state(generated, f"wardrobe-state-{cid}.json", make_wardrobe(cid, snapshots[cid]))
        write_state(generated, f"inventory-state-{cid}.json", make_inventory(cid, snapshots[cid]))

    scene_request = load_json(SOURCE / "scene-context-request.json")
    context = build_scene_context(scene_request, world_snapshot, [snapshots["C01"], snapshots["C02"]])
    write_state(generated, "scene-context-snapshot.json", context)

    projection_c01 = build_projection(identity_c01, species["C01"], individuals["C01"], snapshots["C01"], context, load_json(SOURCE / "projection-request-C01.json"), None)
    projection_c02 = build_projection(identity_c02, species["C02"], individuals["C02"], snapshots["C02"], context, load_json(SOURCE / "projection-request-C02.json"), None)
    write_state(generated, "visual-state-projection-C01.json", projection_c01)
    write_state(generated, "visual-state-projection-C02.json", projection_c02)

    state_hashes = {cid: snapshots[cid]["state_snapshot_sha256"] for cid in snapshots}
    shots = shot_specs(state_hashes)
    transitions = transition_specs()
    for shot in shots:
        write_viewpoint(generated, f"shots/{shot['shot_id']}.json", shot)
    for transition in transitions:
        write_viewpoint(generated, f"transitions/{transition['transition_id']}.json", transition)

    scene_plan = finalize_viewpoint({
        "artifact_type": "scene-viewpoint-plan",
        "scene_id": SCENE_ID,
        "story_order": STORY_ORDER,
        "default_viewpoint_profile_id": "external-character-aligned-third-person",
        "default_knowledge_scope": "character_restricted",
        "default_focal_character_id": "C01",
        "default_point_of_audition": "objective_mix",
        "coverage_strategy": "motivated sparse coverage with one first-person handoff insert",
        "axis_of_action": "C01 to C02 across the central workbench",
        "shots": [{"shot_id": s["shot_id"], "order_index": s["order_index"], "coverage_role": s["coverage_role"], "viewpoint_profile_id": s["viewpoint_profile_id"], "camera_spec_file": f"generated/shots/{s['shot_id']}.json"} for s in shots],
        "transition_ids": [t["transition_id"] for t in transitions],
        "knowledge_policy": "Follow C01 knowledge by default. Reveal P01 damage through C01 attention. Keep the concealed injury undisclosed.",
        "scene_plan_sha256": "0" * 64,
    })
    write_viewpoint(generated, "scene-viewpoint-plan.json", scene_plan)

    shot_projections = []
    requests = []
    for shot in shots:
        projection = shot_projection(shot, projection_c01, projection_c02, context)
        shot_projections.append(projection)
        write_viewpoint(generated, f"shot-projections/{shot['shot_id']}.json", projection)
        request = shot_request(shot, projection, identity_hashes, state_hashes, context, species_hashes, individual_hashes)
        requests.append(request)
        write_viewpoint(generated, f"shot-requests/{shot['shot_id']}.json", request)
        (generated / "proposed-text" / f"{shot['shot_id']}.txt").write_text(prompt_for_shot(shot) + "\n", encoding="utf-8", newline="\n")

    ledger = build_continuity_ledger(scene_plan, shots, transitions)
    write_viewpoint(generated, "shot-continuity-ledger.json", ledger)

    index = {
        "example": "mixed-viewpoint-workshop",
        "run_status": "not run",
        "story_order": STORY_ORDER,
        "identity_contract_sha256_by_character": identity_hashes,
        "state_snapshot_sha256_by_character": state_hashes,
        "scene_context_sha256": context["context_snapshot_sha256"],
        "scene_plan_sha256": scene_plan["scene_plan_sha256"],
        "shot_continuity_ledger_sha256": ledger["ledger_sha256"],
        "shot_ids": [s["shot_id"] for s in shots],
        "transition_ids": [t["transition_id"] for t in transitions],
        "shot_request_sha256_by_shot": {r["shot_id"]: r["request_sha256"] for r in requests},
        "canon_boundary": "The pendant transfer remains planned and non-canon until a returned result is accepted.",
    }
    write_json(generated / "example-index.json", index)

    director = f'''# Mixed Viewpoint Workshop - Director Package

Status: documentation-grounded, not run

## Story and state

C01 enters the humid workshop with a concealed left-side injury already approved in canon. C02 holds the damaged pendant P01. The scene presents the damage, transfers P01 as a planned event, and lands with both characters facing each other across the workbench. The transfer remains non-canon until an actual result is accepted.

- world snapshot: `{world_snapshot['world_state_sha256']}`
- C01 state snapshot: `{state_hashes['C01']}`
- C02 state snapshot: `{state_hashes['C02']}`
- scene context: `{context['context_snapshot_sha256']}`
- scene viewpoint plan: `{scene_plan['scene_plan_sha256']}`
- continuity ledger: `{ledger['ledger_sha256']}`

## Viewpoint design

1. External character-aligned wide master establishes geography and concealed injury performance.
2. External aligned medium follows C01 approach while preserving screen direction.
3. Over-the-shoulder coverage reveals P01 damage through C01 attention.
4. Embodied first-person insert carries the handoff and character-subjective audition.
5. External character-aligned close-up shows C01 reaction and stable identity.
6. External landing master restores shared geography and a continuation-ready endpoint.

## Axis and continuity

The camera remains on the doorway side of the C01 to C02 axis in every external shot. C01 remains screen-left and C02 screen-right. P01 begins in C02 right hand and changes to C01 right hand only during SH04. The concealed injury affects posture but remains covered in every shot.

## Requirement transfer

| Requirement | Carrier | Review |
|---|---|---|
| Stable identity | shared identity contracts and angle-matched references | face, markings, ears, spectacles, proportions |
| Concealed injury | state snapshot plus performance projection | guarded posture without visible bandage |
| P01 ownership | shot specs, transition VT-WORKSHOP-03, handoff prompt | hand sequence and final owner |
| Camera geography | viewpoint plan and continuity ledger | axis, screen direction, eyelines |
| Lighting | scene context and every shot prompt | cool left window, warm right lamps |
| Canon boundary | result log and project state | no transfer event approved before acceptance |

## Target status

No target surface is selected. The proposed shot text is not claimed as submitted, and no output result is claimed.
'''
    (output_root / "director-package.md").write_text(director, encoding="utf-8", newline="\n")

    submission = '''# Mixed Viewpoint Workshop - Submission Plan

Run status: not run

## Target surface

Unresolved. No controls, input combinations, durations, or prompt behavior are claimed.

## Prepared artifacts

- six sealed shot camera specifications;
- five sealed viewpoint transitions;
- one sealed shot continuity ledger;
- six sealed shot visual projections;
- six sealed public shot requests;
- six proposed shot text files.

## Required next evidence

1. Select an exact target surface and record current controls.
2. Generate or adopt angle-matched character and scene media.
3. Inspect the actual files.
4. Map files and text to real controls.
5. Submit and preserve every returned variant.
6. Accept or reject the planned pendant transfer from direct evidence.
'''
    (output_root / "submission-sheet.md").write_text(submission, encoding="utf-8", newline="\n")

    result = '''# Mixed Viewpoint Workshop - Result Log

Run status: not run

No media was submitted and no generated result is claimed. The scene state, viewpoint plan, shot prompts, and public shot-request records are documentation artifacts only.

The proposed pendant transfer remains outside approved canon.
'''
    (output_root / "result-log.md").write_text(result, encoding="utf-8", newline="\n")


def file_map(root: Path) -> dict[str, bytes]:
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        # Input fixtures are scoped to this example, not to the checkout's parents.
        if path.is_file() and path.name not in {"build_example.py", "README.md"} and relative.parts[0] != "source":
            result[relative.as_posix()] = path.read_bytes()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        with tempfile.TemporaryDirectory(prefix="scd-example-") as tmp:
            temp_root = Path(tmp) / "mixed-viewpoint-workshop"
            temp_root.mkdir(parents=True)
            build(temp_root)
            expected = file_map(EXAMPLE)
            actual = file_map(temp_root)
            if expected != actual:
                missing = sorted(set(expected) - set(actual))
                extra = sorted(set(actual) - set(expected))
                changed = sorted(k for k in set(expected) & set(actual) if expected[k] != actual[k])
                print(json.dumps({"ok": False, "missing": missing, "extra": extra, "changed": changed}, indent=2))
                return 1
        print(json.dumps({"ok": True, "example": "mixed-viewpoint-workshop"}, indent=2))
        return 0

    if GENERATED.exists():
        shutil.rmtree(GENERATED)
    for name in ("director-package.md", "submission-sheet.md", "result-log.md"):
        (EXAMPLE / name).unlink(missing_ok=True)
    build(EXAMPLE)
    print(json.dumps({"ok": True, "out": str(EXAMPLE)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
