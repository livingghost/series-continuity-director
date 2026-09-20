#!/usr/bin/env python3
"""Exercise every way the reference activation gate can refuse.

Each case starts from a package and an activation that are admitted, damages one
thing, and declares the code the refusal must carry. Matching the code rather
than the count keeps a case from passing on a different rule. The first case
damages nothing and must be admitted.

Usage:
  python <suite>/scripts/reference_activation_gate_smoke_test.py
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integration_contract import content_hash  # noqa: E402
from reference_activation_gate import gate  # noqa: E402


def sealed(value: dict[str, Any], field: str) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result[field] = content_hash(result, field)
    return result


def authority(scope: str, mode: str = "external-reference") -> dict[str, Any]:
    return sealed({
        "artifact_type": "reference-visual-authority",
        "authority_id": "AV-01",
        "authority_mode": mode,
        "guide_scope": scope,
        "locked_dimensions": ["marking-layout"],
        "free_dimensions": ["lighting"],
    }, "visual_authority_sha256")


def binding(from_order: int, to_order: int | None, **extra: Any) -> dict[str, Any]:
    value = {
        "artifact_type": "state-aware-reference-binding",
        "binding_id": "BIND-01",
        "effective_story_range": {"from_order": from_order, "to_order": to_order},
        "visibly_supported_state": ["wardrobe"],
        "unsupported_or_occluded_state": [],
        "unsupported_assumptions": [],
        "superseded_for_future_scenes": False,
    }
    value.update(extra)
    return sealed(value, "binding_sha256")


def reference(name: str, scope: str, **extra: Any) -> dict[str, Any]:
    value: dict[str, Any] = {"reference_id": name}
    auth = extra.pop("authority", None) or authority(scope)
    bind = extra.pop("binding", None) or binding(100, 900)
    value["visual_authority"] = auth
    value["visual_authority_sha256"] = auth["visual_authority_sha256"]
    value["state_binding"] = bind
    value["binding_sha256"] = bind["binding_sha256"]
    value.update(extra)
    return value


def build_package(references: list[dict[str, Any]]) -> dict[str, Any]:
    plan = sealed({
        "artifact_type": "reference-use-plan",
        "plan_id": "RUP-01",
        "transport_mode": "multi-image",
        "selected_records": ["REC-01"],
        "reference_items": [item["reference_id"] for item in references],
        "surface_lighting_plan": None,
        "surface_lighting_plan_sha256": None,
    }, "reference_use_plan_sha256")
    return sealed({
        "artifact_type": "prepared-reference-set",
        "set_id": "PRS-01",
        "transport_mode": "multi-image",
        "target_model": "a-surface",
        "reference_selection": None,
        "reference_selection_sha256": None,
        "reference_use_plan": plan,
        "reference_use_plan_sha256": plan["reference_use_plan_sha256"],
        "surface_lighting_plan_sha256": None,
        "zero_reference_reason": None,
        "reference_preamble": "the references below carry the identity",
        "prompt_artifacts": [],
        "selected_references": references,
        "single_board": None,
    }, "prepared_reference_set_sha256")


def fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    package = build_package([
        reference("REF-IDENTITY", "identity"),
        reference("REF-GEOMETRY", "shot-geometry"),
    ])
    activation = {
        "activation_id": "ACT-01",
        "package": "package.json",
        "story_point": 400,
        "uses": [
            {"reference": "REF-IDENTITY", "settles": ["identity"]},
            {"reference": "REF-GEOMETRY", "settles": ["shot-geometry"]},
        ],
    }
    return package, activation


Damage = Callable[[dict[str, Any], dict[str, Any]], None]


def package_was_edited(package: dict[str, Any], _activation: dict[str, Any]) -> None:
    package["reference_preamble"] = "edited after sealing"


def a_declared_hash_stopped_matching(package: dict[str, Any], _activation: dict[str, Any]) -> None:
    package["reference_use_plan"]["plan_id"] = "RUP-02"
    package["prepared_reference_set_sha256"] = content_hash(package,
                                                            "prepared_reference_set_sha256")


def the_shot_added_its_own_reference(_package: dict[str, Any], activation: dict[str, Any]) -> None:
    activation["uses"].append({"reference": "REF-OF-MY-OWN", "settles": ["identity"]})


def the_shot_dropped_one_in_silence(_package: dict[str, Any], activation: dict[str, Any]) -> None:
    activation["uses"] = activation["uses"][:1]


def a_reference_is_asked_outside_its_scope(_package: dict[str, Any],
                                           activation: dict[str, Any]) -> None:
    activation["uses"][0]["settles"] = ["shot-geometry"]


def a_locked_dimension_is_reopened(_package: dict[str, Any], activation: dict[str, Any]) -> None:
    activation["uses"][0]["overrides"] = ["marking-layout"]


def a_text_only_authority_is_asked_to_prove(package: dict[str, Any],
                                            _activation: dict[str, Any]) -> None:
    item = package["selected_references"][0]
    auth = authority("identity", mode="text-only")
    item["visual_authority"] = auth
    item["visual_authority_sha256"] = auth["visual_authority_sha256"]
    package["prepared_reference_set_sha256"] = content_hash(package,
                                                            "prepared_reference_set_sha256")


def the_shot_sits_before_the_range(_package: dict[str, Any], activation: dict[str, Any]) -> None:
    activation["story_point"] = 10


def the_shot_sits_after_the_range(_package: dict[str, Any], activation: dict[str, Any]) -> None:
    activation["story_point"] = 5000


def the_reference_was_superseded(package: dict[str, Any], activation: dict[str, Any]) -> None:
    """Superseded, and the binding does not say from where."""

    item = package["selected_references"][0]
    bind = binding(100, None, superseded_for_future_scenes=True)
    item["state_binding"] = bind
    item["binding_sha256"] = bind["binding_sha256"]
    package["prepared_reference_set_sha256"] = content_hash(package,
                                                            "prepared_reference_set_sha256")
    activation["story_point"] = 400


def the_story_point_is_not_an_order(
    _package: dict[str, Any], activation: dict[str, Any]
) -> None:
    activation["story_point"] = "412"


def the_embedded_type_is_unknown(
    package: dict[str, Any], _activation: dict[str, Any]
) -> None:
    item = package["selected_references"][0]
    item["visual_authority"] = dict(item["visual_authority"], artifact_type="something-new")
    package["prepared_reference_set_sha256"] = content_hash(
        package, "prepared_reference_set_sha256"
    )


def a_superseded_reference_past_its_end(
    package: dict[str, Any], activation: dict[str, Any]
) -> None:
    """One fact, one refusal: the range covers it and supersession rides along."""

    item = package["selected_references"][0]
    bind = binding(100, 300, superseded_for_future_scenes=True)
    item["state_binding"] = bind
    item["binding_sha256"] = bind["binding_sha256"]
    package["prepared_reference_set_sha256"] = content_hash(
        package, "prepared_reference_set_sha256"
    )
    activation["story_point"] = 5000


def the_state_is_not_visible(package: dict[str, Any], activation: dict[str, Any]) -> None:
    item = package["selected_references"][0]
    bind = binding(100, 900, unsupported_or_occluded_state=["identity"])
    item["state_binding"] = bind
    item["binding_sha256"] = bind["binding_sha256"]
    package["prepared_reference_set_sha256"] = content_hash(package,
                                                            "prepared_reference_set_sha256")
    del activation


def the_package_is_another_artifact(package: dict[str, Any], _activation: dict[str, Any]) -> None:
    package["artifact_type"] = "reference-bundle-plan"


CASES: list[tuple[str, Damage | None, str]] = [
    ("a complete activation", None, ""),
    ("the package was edited after sealing", package_was_edited, "PACKAGE_ALTERED"),
    ("a declared hash stopped matching", a_declared_hash_stopped_matching, "HASH_MISMATCH"),
    ("the package is another artifact", the_package_is_another_artifact,
     "PACKAGE_NOT_CANONICAL"),
    ("the shot added its own reference", the_shot_added_its_own_reference,
     "REFERENCE_NOT_IN_PACKAGE"),
    ("the shot dropped one in silence", the_shot_dropped_one_in_silence,
     "REFERENCE_DROPPED_SILENTLY"),
    ("a reference is asked outside its scope", a_reference_is_asked_outside_its_scope,
     "OUTSIDE_AUTHORITY"),
    ("a locked dimension is reopened", a_locked_dimension_is_reopened,
     "LOCKED_DIMENSION_REOPENED"),
    ("a text-only authority is asked to prove", a_text_only_authority_is_asked_to_prove,
     "NO_VISUAL_EVIDENCE"),
    ("the shot sits before the range", the_shot_sits_before_the_range, "BEFORE_STORY_RANGE"),
    ("the shot sits after the range", the_shot_sits_after_the_range, "AFTER_STORY_RANGE"),
    ("a superseded reference with an open ended range is reported, not refused",
     the_reference_was_superseded, "unmeasured:open ended"),
    ("the state is not visible", the_state_is_not_visible, "STATE_NOT_VISIBLE"),
    ("a superseded reference used past its end is refused once",
     a_superseded_reference_past_its_end, "AFTER_STORY_RANGE"),
    ("a story point that is not a story order is reported, not refused",
     the_story_point_is_not_an_order, "unmeasured:is not a story order"),
    ("an embedded object of an unknown type is reported, not refused",
     the_embedded_type_is_unknown, "unmeasured:self-hash field"),
]


def main() -> int:
    results = []
    failures = []
    for name, damage, expected in CASES:
        wants_note = expected.startswith("unmeasured:")
        package, activation = fixture()
        if damage is not None:
            damage(package, activation)
        with tempfile.TemporaryDirectory(prefix="scd-activation-") as directory:
            root = Path(directory)
            (root / "package.json").write_text(
                json.dumps(package, ensure_ascii=False), encoding="utf-8", newline="")
            verdict = gate(activation, root)
        codes = [row["code"] for row in verdict["errors"]]
        results.append({
            "case": name,
            "status": verdict["status"],
            "codes": codes,
            "unmeasured": len(verdict["unmeasured"]),
        })
        if damage is None:
            if verdict["errors"]:
                failures.append(f"{name}: a complete activation was refused: {codes}")
            continue
        if wants_note:
            # What cannot be settled is reported, not refused. Admitting it and
            # saying nothing would be the same verdict as admitting it because
            # everything held.
            note = expected.split(":", 1)[1]
            if codes:
                failures.append(f"{name}: refused where it can only report: {codes}")
            elif not any(note in item for item in verdict["unmeasured"]):
                failures.append(f"{name}: no note about {note!r}: {verdict['unmeasured']}")
            continue
        if not codes:
            failures.append(f"{name}: nothing was refused")
        elif expected not in codes:
            failures.append(f"{name}: refused, but not for {expected}: {codes}")

    print(json.dumps({
        "ok": not failures,
        "checks": len(results),
        "results": results,
        "errors": failures,
    }, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
