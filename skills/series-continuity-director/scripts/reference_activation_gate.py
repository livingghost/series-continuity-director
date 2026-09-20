#!/usr/bin/env python3
"""Settle what a visual-contract-package permits before a shot uses it.

Three features the package may require of whoever reads it name three
obligations, and this refuses an activation that breaks one:

  canonical-prepared-reference-set
      One artifact is the reference truth for the shot. The shot activates
      the references that artifact carries, neither adding one it selected for
      itself nor dropping one without saying so, and the hashes the artifact
      declares match the objects it carries.

  record-scoped-reference-authority
      Each reference is authoritative for stated dimensions and not for the
      rest. A shot that asks a reference to settle a dimension outside its scope
      is using evidence that does not exist, and a dimension the package locked
      is not a shot's to reopen.

  state-reconciled-reference-activation
      A reference depicts a state that holds over a story range. Activating it
      outside that range, or after it was superseded, dresses the wrong moment in
      the right character.

The obligations and the artifact shapes both belong to the package. This reads
only the fields those three features name and leaves everything else untouched,
so a change outside them is not a change here.

Its verdict is evidence for the user's decision, and not that decision. What it
cannot measure it reports as unmeasured rather than passing.

Usage:
  python <suite>/scripts/reference_activation_gate.py <activation.json> [--json]

The activation names the package, the story point the shot sits at, and, for each
reference it intends to use, the dimensions it is asking that reference to settle:

  {
    "activation_id": "...",
    "package": "handoff/PRS-EP01-SH04.json",
    "story_point": 412,
    "uses": [
      {"reference": "REF-IDENTITY-01", "settles": ["identity"]},
      {"reference": "REF-GEOMETRY-02", "settles": ["shot-geometry"], "overrides": []}
    ]
  }
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integration_contract import content_hash  # noqa: E402

PACKAGE_ARTIFACT = "prepared-reference-set"

# The self-hash field of each artifact this reads. A hash cannot be checked
# without knowing which field it lives in, and knowing that for the artifacts
# named by a supported feature is what supporting it means.
SELF_HASH_FIELD = {
    "prepared-reference-set": "prepared_reference_set_sha256",
    "reference-selection": "selection_sha256",
    "reference-use-plan": "reference_use_plan_sha256",
    "surface-lighting-plan": "surface_lighting_plan_sha256",
    "reference-visual-authority": "visual_authority_sha256",
    "state-aware-reference-binding": "binding_sha256",
}

# What a guide scope permits a reference to settle. The scopes are the
# producer's vocabulary; the mapping to what a shot asks for is this consumer's.
SCOPE_SETTLES = {
    "identity": frozenset({"identity"}),
    "appearance-state": frozenset({"appearance-state"}),
    "shot-geometry": frozenset({"shot-geometry"}),
    "identity-and-shot": frozenset({"identity", "shot-geometry"}),
    "reference-evidence": frozenset({"identity", "appearance-state", "shot-geometry"}),
}


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    row = {"code": code, "message": message}
    row.update(extra)
    return row


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def check_declared_hash(
    holder: dict[str, Any],
    field: str,
    embedded: Any,
    label: str,
    errors: list[dict],
    unmeasured: list[str],
) -> None:
    """One declared hash against the object it is a hash of.

    A declared hash with nothing beside it is not a failure: the object may be
    carried elsewhere. It is unmeasured, and saying so is the point.
    """

    declared = holder.get(field)
    if declared is None:
        return
    if not isinstance(embedded, dict):
        unmeasured.append(f"{label}: {field} is declared and the object it names is not here")
        return
    kind = str(embedded.get("artifact_type") or "")
    self_field = SELF_HASH_FIELD.get(kind)
    if self_field is None:
        # The hash excludes the object's own self-hash field, and which field that
        # is belongs to the artifact. For a type this consumer does not know, any
        # answer would be a guess presented as a mismatch.
        unmeasured.append(
            f"{label}: {field} names an object of type {kind or 'unstated'!r}, whose "
            "self-hash field this consumer does not know"
        )
        return
    actual = content_hash(embedded, self_field)
    if actual != declared:
        errors.append(finding(
            "HASH_MISMATCH",
            f"{label}: {field} does not match the object it names",
            declared=declared,
            actual=actual,
        ))


def check_canonical_set(
    package: dict[str, Any],
    errors: list[dict],
    unmeasured: list[str],
) -> dict[str, dict[str, Any]]:
    """The package is one settled artifact, and its own hashes hold.

    Returns the references it carries, keyed by the id a shot names them by.
    """

    kind = str(package.get("artifact_type") or "")
    if kind != PACKAGE_ARTIFACT:
        errors.append(finding(
            "PACKAGE_NOT_CANONICAL",
            f"the package is {kind!r}, and the reference truth for a shot is "
            f"one {PACKAGE_ARTIFACT}",
        ))
        return {}

    self_field = SELF_HASH_FIELD[PACKAGE_ARTIFACT]
    declared = package.get(self_field)
    if not isinstance(declared, str):
        errors.append(finding("PACKAGE_UNSEALED", f"the package declares no {self_field}"))
    elif content_hash(package, self_field) != declared:
        errors.append(finding(
            "PACKAGE_ALTERED",
            "the package does not hash to what it declares, so it is not the "
            "artifact that was sealed",
            declared=declared,
            actual=content_hash(package, self_field),
        ))

    plan = package.get("reference_use_plan")
    check_declared_hash(package, "reference_selection_sha256",
                        package.get("reference_selection"), "package", errors, unmeasured)
    check_declared_hash(package, "reference_use_plan_sha256", plan, "package", errors, unmeasured)
    if isinstance(plan, dict):
        check_declared_hash(plan, "surface_lighting_plan_sha256",
                            plan.get("surface_lighting_plan"), "reference use plan",
                            errors, unmeasured)
    else:
        unmeasured.append(
            "reference use plan: not carried in the package, so authority and story range "
            "are read from the references alone"
        )

    references: dict[str, dict[str, Any]] = {}
    carried = package.get("selected_references")
    if not isinstance(carried, list):
        errors.append(finding("PACKAGE_HAS_NO_REFERENCES",
                              "the package carries no selected_references array"))
        return references
    for index, item in enumerate(carried):
        if not isinstance(item, dict):
            errors.append(finding("REFERENCE_MALFORMED",
                                  f"selected_references[{index}] is not an object"))
            continue
        name = str(item.get("reference_id") or item.get("binding_id") or item.get("role") or "")
        if not name:
            errors.append(finding(
                "REFERENCE_UNNAMED",
                f"selected_references[{index}] carries no id a shot could name it by",
            ))
            continue
        if name in references:
            errors.append(finding("REFERENCE_DUPLICATED",
                                  f"{name} appears more than once in the package"))
            continue
        references[name] = item
    return references


def check_activation_covers_the_set(
    uses: list[dict[str, Any]],
    references: dict[str, dict[str, Any]],
    errors: list[dict],
) -> None:
    """Every reference the package carries is used, or its absence is declared."""

    named = {str(use.get("reference") or "") for use in uses}
    for extra in sorted(named - set(references) - {""}):
        errors.append(finding(
            "REFERENCE_NOT_IN_PACKAGE",
            f"{extra} is activated and the package does not carry it, so the shot is "
            "assembling a reference set of its own",
        ))
    declined = {
        str(use.get("reference") or "")
        for use in uses
        if use.get("declined")
    }
    for dropped in sorted(set(references) - named - declined):
        errors.append(finding(
            "REFERENCE_DROPPED_SILENTLY",
            f"{dropped} is in the package and the activation neither uses it nor says "
            "why it is declined",
        ))


def authority_of(reference: dict[str, Any]) -> dict[str, Any] | None:
    value = reference.get("visual_authority")
    return value if isinstance(value, dict) else None


def check_record_scoped_authority(
    uses: list[dict[str, Any]],
    references: dict[str, dict[str, Any]],
    errors: list[dict],
    unmeasured: list[str],
) -> None:
    for use in uses:
        name = str(use.get("reference") or "")
        reference = references.get(name)
        if reference is None or use.get("declined"):
            continue
        authority = authority_of(reference)
        if authority is None:
            unmeasured.append(f"{name}: carries no visual authority, so its scope is unstated")
            continue
        check_declared_hash(reference, "visual_authority_sha256", authority, name,
                            errors, unmeasured)
        scope = str(authority.get("guide_scope") or "")
        permitted = SCOPE_SETTLES.get(scope)
        if permitted is None:
            unmeasured.append(f"{name}: guide scope {scope!r} is not one this consumer knows")
            continue
        for dimension in sorted({str(item) for item in use.get("settles") or []}):
            if dimension not in permitted:
                errors.append(finding(
                    "OUTSIDE_AUTHORITY",
                    f"{name} is asked to settle {dimension!r} and its authority is "
                    f"{scope!r}, which does not cover it",
                    reference=name,
                    guide_scope=scope,
                ))
        if str(authority.get("authority_mode") or "") == "text-only":
            for dimension in sorted({str(item) for item in use.get("settles") or []}):
                errors.append(finding(
                    "NO_VISUAL_EVIDENCE",
                    f"{name} is text-only and is asked to settle {dimension!r}, which "
                    "needs a view that proves it",
                    reference=name,
                ))
        locked = {str(item) for item in authority.get("locked_dimensions") or []}
        reopened = locked & {str(item) for item in use.get("overrides") or []}
        for dimension in sorted(reopened):
            errors.append(finding(
                "LOCKED_DIMENSION_REOPENED",
                f"{name} locks {dimension!r} and the activation overrides it",
                reference=name,
            ))


def binding_of(reference: dict[str, Any]) -> dict[str, Any] | None:
    value = reference.get("state_binding")
    return value if isinstance(value, dict) else None


def story_bounds(story_range: dict[str, Any]) -> tuple[Any, Any]:
    """The range as `state-aware-reference-binding` declares it.

    `to_order` is nullable and a null one is open ended.
    """

    return story_range.get("from_order"), story_range.get("to_order")


def check_state_reconciliation(
    uses: list[dict[str, Any]],
    references: dict[str, dict[str, Any]],
    story_point: Any,
    errors: list[dict],
    unmeasured: list[str],
) -> None:
    if story_point is None:
        unmeasured.append(
            "story point: the activation states none, so no story range can be reconciled"
        )
    elif not isinstance(story_point, int) or isinstance(story_point, bool):
        unmeasured.append(
            f"story point: {story_point!r} is not a story order, so no story range "
            "can be reconciled"
        )
        story_point = None
    for use in uses:
        name = str(use.get("reference") or "")
        reference = references.get(name)
        if reference is None or use.get("declined"):
            continue
        binding = binding_of(reference)
        if binding is None:
            unmeasured.append(f"{name}: carries no state binding, so its story range is unstated")
            continue
        check_declared_hash(reference, "binding_sha256", binding, name, errors, unmeasured)
        story_range = binding.get("effective_story_range")
        superseded = binding.get("superseded_for_future_scenes") is True
        if not isinstance(story_range, dict):
            unmeasured.append(f"{name}: its binding states no effective story range")
            if superseded:
                unmeasured.append(
                    f"{name}: marked superseded for later scenes, and with no story range "
                    "there is nothing to say which scenes those are"
                )
        elif story_point is not None:
            start, end = story_bounds(story_range)
            past_the_end = isinstance(end, int) and not isinstance(end, bool) and story_point > end
            if isinstance(start, int) and not isinstance(start, bool) and story_point < start:
                errors.append(finding(
                    "BEFORE_STORY_RANGE",
                    f"{name} holds from {start} and the shot sits at {story_point}",
                    reference=name,
                ))
            if past_the_end:
                # One fact, one refusal. A superseded reference used past its end
                # is already refused by the range, and saying it twice makes two
                # findings out of one thing to fix.
                errors.append(finding(
                    "AFTER_STORY_RANGE",
                    f"{name} holds until {end} and the shot sits at {story_point}"
                    + (", and it was superseded for later scenes" if superseded else ""),
                    reference=name,
                    superseded=superseded,
                ))
            elif superseded and end is None:
                unmeasured.append(
                    f"{name}: marked superseded for later scenes, and its range is open ended, "
                    "so which scenes are later is unstated"
                )
        unsupported = [str(item) for item in binding.get("unsupported_or_occluded_state") or []]
        asked = {str(item) for item in use.get("settles") or []}
        for item in sorted(set(unsupported) & asked):
            errors.append(finding(
                "STATE_NOT_VISIBLE",
                f"{name} does not show {item!r} and is asked to settle it",
                reference=name,
            ))
        assumptions = [str(item) for item in binding.get("unsupported_assumptions") or []]
        if assumptions:
            unmeasured.append(
                f"{name}: the package records assumptions it did not prove: "
                + ", ".join(sorted(assumptions))
            )


def gate(activation: dict[str, Any], root: Path) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    unmeasured: list[str] = []

    package_path = activation.get("package")
    package: dict[str, Any] = {}
    if not isinstance(package_path, str) or not package_path:
        errors.append(finding("PACKAGE_MISSING", "the activation names no package"))
    else:
        resolved = Path(package_path)
        if not resolved.is_absolute():
            resolved = root / resolved
        try:
            loaded = load_json(resolved)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(finding("PACKAGE_UNREADABLE", f"{package_path}: {exc}"))
        else:
            if isinstance(loaded, dict):
                package = loaded
            else:
                errors.append(finding("PACKAGE_MALFORMED",
                                      f"{package_path} does not hold an object"))

    uses = [item for item in activation.get("uses") or [] if isinstance(item, dict)]
    references = check_canonical_set(package, errors, unmeasured) if package else {}
    if package:
        check_activation_covers_the_set(uses, references, errors)
        check_record_scoped_authority(uses, references, errors, unmeasured)
        check_state_reconciliation(uses, references, activation.get("story_point"),
                                   errors, unmeasured)
    if not uses:
        unmeasured.append("uses: the activation names no reference and no dimension")

    return {
        "gate": "reference-activation",
        "activation_id": activation.get("activation_id"),
        "package": package_path,
        "references": len(references),
        "status": "refused" if errors else "admitted",
        "errors": errors,
        "unmeasured": unmeasured,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refuse an activation that breaks a package's stated reference obligations."
    )
    parser.add_argument("activation", help="Path to the activation JSON.")
    parser.add_argument("--root", help="Directory relative paths resolve from. "
                                       "Defaults to the activation's own directory.")
    parser.add_argument("--json", action="store_true", help="Print the verdict as JSON.")
    arguments = parser.parse_args(argv)

    path = Path(arguments.activation)
    try:
        activation = load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"{path}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(activation, dict):
        print(f"{path}: the activation must be an object", file=sys.stderr)
        return 2

    root = Path(arguments.root) if arguments.root else path.resolve().parent
    verdict = gate(activation, root)
    if arguments.json:
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
    else:
        print(verdict["status"])
        for row in verdict["errors"]:
            print(f"  {row['code']}: {row['message']}")
        for row in verdict["unmeasured"]:
            print(f"  unmeasured: {row}")
    return 1 if verdict["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
