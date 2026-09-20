# Visual contracts, and the shot-request that binds them

Visual design specifies what a subject is; shot direction specifies how it appears at a particular story point. Develop the design from the brief, persona and world, then choose the view, performance and references that express the scene's purpose. Use contracts to retain the approved decisions and expose unresolved details.

A content hash identifies a record. Approval establishes its use; media inspection establishes what a particular image or recording supports. Keep those conclusions separate.

## 1. Which authority settles what

Use the narrowest relevant authority for each decision. The [responsibility layers](state-and-trust.md#21-responsibility-layers) distinguish intent, facts, direction, execution, observation and acceptance; a public data representation does not change a record's role:

| Evidence | What it can settle |
|---|---|
| Approved narrative, persona, and world design | Story purpose, identity, character intent, knowledge, and the author's portrayal choices |
| Species Morphology Profile | The declared body-plan possibility space, capabilities, and meaningful absences |
| Individual Morphology and Character Identity Contracts | This subject's declared realization and enduring appearance |
| Era, Form, and Appearance Variant Contracts | Approved changes with explicit applicability and lineage |
| Approved events and processes | Variable state at the requested story point |
| Scene context, camera, and projection | What this shot can show and which features need visible support |
| Adopted media and observed endpoints | What a particular file actually proves, in its recorded scope |
| Target observations and exact submissions | What was bound, sent, returned, and measured for this operation |

An event cannot rewrite stable anatomy through an undeclared state path. A generated image cannot approve a new body feature, a relationship, or a story event. A declaration of intended appearance cannot prove that media depicts it.

## 2. Visual design and the morphology stack

For a new recurring subject, develop the persona and world context with the author, record stable visual anchors in `character-profiles.md`, and use the bundled schemas and templates when a machine-readable morphology or state binding is needed. Draft missing fields explicitly; do not fill them from a species label or from assumed human anatomy. An unresolved field stays unresolved until the needed decision or evidence exists.

Draft the applicable Species, Individual, Identity, Era, Form and Appearance documents. After substantive review, validate and seal each artifact with `scripts/state_protocol.py finalize INPUT --out OUTPUT`, then validate it. Sealing identifies the bytes; approval is still a separate author decision. Keep superseded accepted records for their historical ranges.

```text
species morphology profile
+ individual morphology contract
+ character identity contract
+ applicable era, form, and appearance contracts
+ approved state at a story point
+ scene, pose, clothing, visibility and camera
= shot-resolved morphology and identity
```

A species profile owns possibilities, not a compulsory instance. An individual contract owns stable feature IDs, measurements, markings, asymmetries, expression carriers, mutable paths and unknowns. A projection owns only the selected visible result. A hidden feature remains in the body plan.

Before using a record, establish its approval status, supporting evidence and applicable story range. For prose and comics, apply the visual contracts needed by the intended panels or passages; do not impose shot geometry on prose.

## 3. Per-shot request

A `shot-request` records the image evidence required for a shot. It binds the applicable design, state, scene and camera to visible obligations and a deliverable. Sending a generation request requires the separate submission approval.

It carries:

```text
species_profile_sha256_by_character
individual_morphology_sha256_by_character
identity_contract_sha256_by_character
state_snapshot_sha256_by_character
visible_morphology_feature_refs_by_character
scene_context_sha256
camera_spec_sha256
shot_projection_sha256
scene_plot_sha256 and narrative_sha256 when linked
viewpoint_profile_id
visible_identity_obligations and visible_state_obligations
selected_reference_candidates
deliverable and required_output (including aspect_ratio when applicable)
```

Validate the exact request and its referenced files with `scripts/shot_request.py`. Use `--require-complete` when all named bindings must be checked before handoff. A request inspected alone reports unverified bindings, not a complete approval. Empty character maps are valid for a character-free view; never invent a protagonist to fill them.

### The narrative contract

[The narrative protocol](../protocols/narrative/README.md) describes what the series is about. The author controls the narrative; the agent can propose and edit it under that direction. `scripts/narrative.py`, persona records and `scripts/scene_plot.py` read the production's narrative and scene evidence. Screen scenes are realized as shots, comics as pages and panels, and prose as passages. Derive each shot's purpose and permitted disclosure from its approved scene plot.

### Where the shot came from

Within a narrative project, a scene plot names its narrative and the chapter it realizes. When a shot request carries `scene_plot_sha256`, it records the approved plot content; `narrative_sha256` records the narrative underlying that plot. Both links travel together. A request not linked to a narrative may omit these hashes. A narrative-linked submission requires both. Report missing provenance as unmeasured rather than inventing it.

Camera `knowledge_scope` describes the information reach of one shot. Scene-plot `focalization` describes whose knowledge limits the telling. Neither can silently substitute for the other.

## 4. Camera-dependent morphology and reference selection

Changing camera does not change stable identity; it changes the evidence the frame needs.

- A front close-up needs the visible facial or sensory features and expression carriers.
- A profile needs visible projection, attachment and depth, not unsupported front-view inference.
- A rear shot needs rear markings, attachment sites, clothing and harness paths.
- Full-body action needs declared counts, proportions, contacts and appendage clearance.
- First-person direction concerns the environment and declared visible limbs or tools; it does not require an unseen owner's face.
- Contact needs ownership and contact surfaces for each participating structure, tool, garment and support.

Select adopted references that visibly support those requirements from useful views. A portrait does not prove a hidden attachment. When a selected reference bundle has identity and performance panels, assign their roles separately and record their actual target controls. A performance pose does not redefine identity. If only text establishes a feature, retain the text anchor without claiming visual proof. The author decides whether to create missing reference media under the submission rules.

## 5. Candidate and adoption separation

A Candidate Manifest records a particular generation or import result. Once sealed, it is immutable evidence of that candidate set. Do not edit it to record approval. A separate Adoption Receipt records the actual selection, scope, registry updates, effective story range and supersession.

For morphology-bearing assets, record the contracts and view-specific features the adopted file supports, the unsupported regions or states, its applicable form and story range, and any derivation or accepted repair. The fact that a file passed structure or hash validation does not approve its content. Importing an envelope also does not create an adoption receipt.

A text fact can be canon without an image. It becomes a visual lock only when an adopted carrier proves the relevant appearance. Planned end states and observed endpoint geometry remain distinct.

## 6. State, form, and offscreen change

Resolve approved events and processes in story order, not in the order shots are shown. Temporary state, interruptions, expiry and editorial supersession have explicit rules in the public state contract. Ordinary changes affect declared mutable paths; permanent anatomy or topology changes need approved form or identity lineage.

For a flashback, select the era, form and state valid at that point. For a continuation, inspect the accepted terminal media for the seam while retaining the correct identity and story-state authorities. Use the observed terminal frame to verify the seam; the projected endpoint remains the intended result.

## 7. Drift routing

When a review is requested, identify which authority needs attention. A wrong species declaration goes back to species design; an individual discrepancy goes back to that individual contract; a wrong state goes back to events, processes or resolution. A crop or occlusion does not change anatomy. A failed performance, contact or composition is a shot realization issue. A repeatedly lost feature may justify a target-scoped tactic.

Preserve the candidate and the observation. Present returned work before reviewing it, and do not trigger another paid run from an unrequested self-review. A repair or new generation requires the user's applicable authorization. Deliberate portrayal variation must be distinguished from accidental drift using the approved narrative and character intent.

## 8. Public artifact delivery

When the request includes artifact exchange, select the artifact type, required features and exact referenced content. Use `scripts/protocol_exchange.py` to inspect or export the artifact with its schema contract, and to verify a received bundle. `protocols/contract-manifest.json` lists the public types and `config/protocol-layout.json` resolves their schemas.

For profile-aware exchange, `scripts/build_interchange_envelope.py` writes `artifact.json`, `declaration.json` and `envelope.json`. Validation checks the profile, identifiers, required features and content commitments. Preserve unknown optional features as uninterpreted evidence; stop if a required feature cannot be interpreted.

Record source provenance, approval status and effective range before adopting supplied evidence. Verification is not media inspection, adoption or submission permission. See [Interchange](../protocols/interchange/README.md) for the commands and file contract.

## 9. Re-anchor ladder

Before a shot is realized, reconcile:

1. Approved narrative, portrayal intent and current persona.
2. Applicable identity, morphology and variation contracts.
3. Approved state at the selected story point.
4. Adopted identity and performance carriers with their visible support and limits.
5. Shot geometry, crop, contact, blocking and knowledge scope.
6. Accepted seam media for continuity geometry, never as a replacement for identity.
7. Exact text anchors for details not proved by the selected view.

This is a reconciliation order, not permission to hide a conflict. Stop at the earliest unresolved dependency needed by the operation. Do not average identities or promote an accidental feature.

## 10. Reference activation obligations

When a `visual-contract-package` is selected for an operation, use `scripts/reference_activation_gate.py` before submission.

**The prepared reference set is the reference truth.** Bind the selected set by hash. Do not add or silently drop references during activation. Rebuild a newly reviewed selection when the set genuinely changes.

**Authority is record-scoped.** A reference can settle only its declared dimensions. Identity guidance does not settle shot geometry; text-only authority is not visible evidence. Do not reopen a locked dimension through an undocumented override.

**Activation is reconciled with state.** Observe effective story ranges, supersession and the supported or occluded state. Carry unproved assumptions into the requested review rather than silently settling them.

Unprovided evidence is unmeasured. Check the applicable narrative, submission, target and media-evidence requirements before proceeding.
