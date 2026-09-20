# Shared State Protocol

This directory contains public contracts for identity, morphology, variable state, references and adoption. They are usable for authoring as well as explicit data exchange. Contracts distinguish evidence ownership rather than software responsibilities: stable design, approved events, derived snapshots, proposed results and adopted media are separate records even in one project.

The agent can draft the records under author direction, seal and validate them, and realize them with the actual target operations. Only the user can approve canon or authorize spending. A supplied record follows those same rules; protocol validation does not adopt it.

## Canonical project layout

```text
series-state.md
character-profiles.md
asset-registry.md
production-state.md
state/
  events.jsonl
  processes/
  snapshots/
  scene-contexts/
  visual-projections/
  relationships/
  wardrobe/
  inventory/
  reference-selections/
  candidate-manifests/
  external-contracts/
  adoption-receipts/
  observations/
```

`state/events.jsonl` is the canonical history of variable state. Current-value snapshots are derived. Do not edit a snapshot to alter canon. Append an approved event and rebuild.

## Morphology authority

The shared protocol separates three morphology layers:

1. `species-morphology-profile`: lineage-wide topology, feature inventory, counts, attachments, surfaces, capabilities, expression grammar, meaningful absences, population variation, and near-species differentials.
2. `individual-morphology-contract`: exact recurring-subject measurements, feature instances, asymmetries, markings, damage, grooming, nails or claws, tools, personal expression behavior, mutable state paths, and unresolved fields.
3. `resolved-morphology`: the shot-visible result after active form, state, pose, wardrobe, crop, occlusion, contact, and camera are applied.

SCD events may change only approved mutable paths. A permanent topology change requires an approved form or morphology-contract revision. A crop or generated omission never deletes an approved feature from canon.

## Public exchange boundary

The installed schema registry is `protocols/contract-manifest.json`. Public schemas and their transitive references are resolved through `config/protocol-layout.json`; the semantic commitment is `protocols/semantics.md`. Internal project schemas are not inferred from public data.

Use `scripts/protocol_exchange.py` for exact artifact inspect/export/verify. A profile-aware bundle also includes its `declaration.json` and `envelope.json`; `scripts/validate_integration.py --direction consumes` checks explicitly supplied data. No command needs another installation. Unknown optional features remain opaque; unknown required features stop interpretation. Exchanging or validating data never writes canon.

## Artifact identification

The product release is versioned as one unit. Protocol artifacts do not carry an independent schema or protocol number. Each artifact is identified by `artifact_type`, validated against the schema files shipped in the installed product release, and sealed with its canonical content hash where applicable. The JSON Schema `$schema` URI selects the external validator dialect and is not a product-managed version.

## Protocol rules

1. Identity, canonical state, intended visual projection, and observed render state remain separate.
2. Returned media never becomes canon automatically.
3. Candidate Manifests are immutable candidate records. Adoption decisions are separate Adoption Receipts, whether the candidate was generated in a project operation or supplied.
4. State events distinguish story time, production record time, and disclosure time.
5. Temporary states need an expiry order, a clear event, or a process.
6. Cross-entity transfers use atomic events.
7. Old reference assets remain available for flashbacks and historical ranges.
8. Exact target bindings and observed target behavior remain in `production-state.md`.
9. Internal IDs and hashes stay in production records, not in exact model-facing prompt text unless the target documents such syntax.
10. Persisted artifacts must carry a valid canonical self-hash. An all-zero self-hash is an authoring placeholder for templates only.
11. Temporary end-order rollback is limited to reversible `set` and `replace` events. Rollback applies only while the temporary event remains the active writer for that path. Other temporary changes require an explicit clear event.
12. Surviving events cannot write the same entity path at the same story order. Process interruption and editorial supersession are explicit, validated operations.
13. Scene-context and projection assembly fail closed on missing entities, mismatched identity hashes, absent state paths, or stale snapshot bindings.
14. Prompt regeneration follows changed visible projection semantics rather than any nonvisual state hash change.
15. Character changes and processes require an explicit Character State Schema. Resolution rejects undeclared paths, wrong value types, and disallowed persistence before applying an event.
16. Nonempty state machines are unsupported until each machine names its state path and events carry an explicit transition trigger. The resolver does not infer either binding.

## Runtime utilities

```bash
python scripts/state_protocol.py validate <artifact.json>
python scripts/state_protocol.py resolve-world ... --scene-context-id SCENE --character-state-schema character-C01.schema.json
python scripts/state_protocol.py extract-character ...
python scripts/state_protocol.py build-context ...
python scripts/state_protocol.py build-projection ...
python scripts/select_state_references.py --bindings ... --out ...
python scripts/state_protocol.py make-lineage ...
python scripts/issue_adoption_receipt.py --candidate-manifest ... --decision ... --out ...
python scripts/validate_state_protocol.py
python scripts/validate_integration.py
```

The validators check structure, hashes, lineage, canonical example conformance, file evidence, and packaging integrity. They do not evaluate video quality, acting, or artistic taste.

See the [command-line interface reference](../../scripts/README.md) for complete inputs, outputs, side effects, and failure conditions.
