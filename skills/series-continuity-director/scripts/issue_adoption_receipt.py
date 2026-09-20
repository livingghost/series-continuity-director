#!/usr/bin/env python3
"""Issue a sealed Series Continuity Director Adoption Receipt from an inspected Candidate Manifest.

The receipt remains separate from the immutable producer manifest. It records
consumer-side adoption and proposed Asset Registry updates without modifying the
Candidate Manifest.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from state_protocol import finalize_artifact, load_json, validate_artifact, write_json


def build_receipt(manifest: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    report = validate_artifact(manifest)
    if manifest.get("artifact_type") != "candidate-manifest" or not report.get("ok"):
        raise ValueError("invalid candidate manifest: " + "; ".join(report.get("errors", [])))

    known_candidates = {
        row.get("candidate_id")
        for row in manifest.get("candidates", [])
        if isinstance(row, dict)
    }
    adoptions = decision.get("adoptions")
    if not isinstance(adoptions, list):
        raise ValueError("decision.adoptions must be an array")
    for index, row in enumerate(adoptions):
        if not isinstance(row, dict):
            raise ValueError(f"decision.adoptions[{index}] must be an object")
        candidate_id = row.get("candidate_id")
        if candidate_id not in known_candidates:
            raise ValueError(f"unknown candidate_id: {candidate_id}")

    issued_at = str(decision.get("issued_at") or "").strip()
    if not issued_at:
        raise ValueError("decision.issued_at is required for a reproducible receipt")

    result = finalize_artifact({
        "artifact_type": "adoption-receipt",
        "receipt_id": str(decision.get("receipt_id") or f"AR-{manifest['manifest_id']}"),
        "issued_by": str(decision.get("issued_by") or "series-continuity-director"),
        "issued_at": issued_at,
        "candidate_manifest_sha256": str(manifest["candidate_manifest_sha256"]),
        "character_id": str(manifest["character_id"]),
        "adoptions": adoptions,
        "asset_registry_updates": list(decision.get("asset_registry_updates", [])),
        "adoption_receipt_sha256": "0" * 64,
    })
    validation = validate_artifact(result)
    if not validation.get("ok"):
        raise ValueError("invalid adoption receipt: " + "; ".join(validation.get("errors", [])))
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Issue an Adoption Receipt.")
    parser.add_argument("--candidate-manifest", required=True)
    parser.add_argument("--decision", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        value = build_receipt(
            load_json(Path(args.candidate_manifest)),
            load_json(Path(args.decision)),
        )
        write_json(Path(args.out), value)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
