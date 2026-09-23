#!/usr/bin/env python3
"""Select state-valid adopted reference assets from explicit SCD bindings."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from state_protocol import (
    artifact_hash,
    load_validated_artifact,
    select_state_references,
    validate_artifact,
    write_json,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Select state-aware reference assets.")
    parser.add_argument("--bindings", required=True)
    parser.add_argument("--selection-id", required=True)
    parser.add_argument("--identity-contract", required=True)
    parser.add_argument("--era-contract")
    parser.add_argument("--appearance-variant")
    parser.add_argument("--state-snapshot")
    parser.add_argument("--story-order", required=True, type=int)
    parser.add_argument("--required-feature", action="append", default=[])
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        raw = json.loads(Path(args.bindings).read_text(encoding="utf-8"))
        bindings = raw.get("bindings", []) if isinstance(raw, dict) else raw
        if not isinstance(bindings, list) or not all(isinstance(item, dict) for item in bindings):
            raise ValueError("bindings must be an array or an object with a bindings array")
        identity = load_validated_artifact(
            Path(args.identity_contract), "character-identity-contract"
        )
        era = load_validated_artifact(Path(args.era_contract), "era-contract") if args.era_contract else None
        appearance = load_validated_artifact(
            Path(args.appearance_variant), "appearance-variant-contract"
        ) if args.appearance_variant else None
        state = load_validated_artifact(
            Path(args.state_snapshot), "state-snapshot"
        ) if args.state_snapshot else None
        value = select_state_references(
            bindings,
            selection_id=args.selection_id,
            identity_hash=artifact_hash(identity),
            era_hash=artifact_hash(era) if era else None,
            appearance_hash=artifact_hash(appearance) if appearance else None,
            state_hash=artifact_hash(state) if state else None,
            story_order=args.story_order,
            required_features=args.required_feature,
            limit=args.limit,
        )
        report = validate_artifact(value)
        if not report.get("ok"):
            raise ValueError("invalid reference selection: " + "; ".join(report.get("errors", [])))
        write_json(Path(args.out), value)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
