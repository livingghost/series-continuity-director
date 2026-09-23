# State artifacts

`events.jsonl` is the append-only canonical variable-state ledger.

Every JSON file under `state/` is a managed protocol artifact and must declare `artifact_type`. The ledger is the only format exception: each non-comment line in `events.jsonl` must be a `state-event` object. Keep unrelated notes or application configuration outside managed artifact directories.

The requests the state commands read and do not seal carry no `artifact_type`: the world-state base, the scene-context request and each projection request. Keep them under `work/state-inputs/`. A scene context takes its scene's id, so the request's `scene_context_id` and the `--scene-context-id` given to `resolve-world` are the `scene_id` the scene's shots name.

Every initialized project also contains these canonical state subdirectories:

- `processes/` for approved progressive changes and their milestones;
- `snapshots/` for derived world and character state;
- `scene-contexts/` for derived scene context;
- `visual-projections/` for shot-visible state;
- `relationships/` for directional relationship state and scene projections;
- `wardrobe/` for resolved clothing layers and conditions;
- `inventory/` for ownership, possession, equipment, storage, and transfer state;
- `reference-selections/` for state-aware adopted asset selection;
- `candidate-manifests/` for immutable evidence received from a visual-contract-package;
- `external-contracts/` for content-addressed external contract references, interpretation status, adoption state, and valid story ranges;
- `adoption-receipts/` for Series Continuity Director adoption decisions;
- `observations/` for non-canon render evidence and drift observations.

Do not edit a sealed derived artifact to change canon. Add or supersede an approved event, then rebuild the affected derived artifacts.
