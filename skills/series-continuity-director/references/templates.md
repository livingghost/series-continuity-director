# Production Templates and Master Checklist

The canonical operator-facing templates live under [`assets/production-templates/`](../assets/production-templates/). Use those files directly rather than copying shortened forms into a project. This reference explains when each template applies and carries the complete final checklist.

## 1. Scene and asset preparation

Use the [Scene and Asset Preparation template](../assets/production-templates/scene-and-asset-preparation.md) when required state, media, or target evidence is missing.

It preserves:

- story purpose and segment delivery role;
- current canonical state;
- hook, build, turn, payoff, and landing;
- viewpoint, axis, action, contact, and performance;
- dialogue, sound, atmosphere, and music;
- intended operation and unresolved surface facts;
- existing and missing media;
- provisional requirement transfer;
- stop conditions that prevent imaginary inspection.

Do not finalize a target submission from this template while a critical start image, endpoint, source operand, or target control remains unknown.

## 2. Character identity media request

Use the [Character Identity Media Request](../assets/production-templates/character-identity-media-request.md) to ask for identity or state-aware reference coverage.

The request provides identity and state hashes, intended use, visible obligations, effective story range, and acceptance criteria. Visual-contract authoring, reference-bundle planning, prompts, payloads and candidate manifests are settled by whatever answers that request.

The request must distinguish:

- stable identity from temporary state;
- visible features from unsupported or occluded features;
- angle and body-region coverage from scene placement;
- candidate evidence from adoption;
- current-era assets from flashback or future-era assets.

## 3. Scene, layout, and boundary media brief

Use the [Scene, Layout, or Boundary Media Brief](../assets/production-templates/scene-layout-boundary-media-brief.md) for:

- planning layout;
- literal start frame;
- composite start frame;
- end frame;
- continuation frame;
- state-corrective derivative;
- transition boundary asset.

The brief names camera, visible geography, characters, props, support, contact, light, state, frame role, and unsupported facts. A planning image does not control a target until it is submitted, converted into another submitted asset, or translated into exact text.

## 4. Boundary-frame extraction and inspection

Use the [Boundary Frame Inspection template](../assets/production-templates/boundary-frame-inspection.md) after accepting a source or finished clip.

Record direct observations only:

- camera profile, position, roll, scale, lens relation, and direction;
- visible characters, body regions, state, wardrobe, props, contact, and support;
- environment, light, atmosphere, and open paths;
- artifacts;
- audio tail;
- physically possible first action for continuation;
- planned facts disproved by the actual result;
- repair or corrective derivative required.

Extract continuation evidence after finishing, not before.

## 5. Shot director package

Use the [Shot Director Package](../assets/production-templates/shot-director-package.md) only after the relevant opening evidence and operation are inspectable.

It preserves the complete creative and continuity intent even when the target-facing prompt becomes shorter. The package includes:

- story function and accepted continuity;
- inspected evidence and uncertainty;
- shot proposition;
- causal beat chain;
- blocking and camera geometry;
- contact and prop ownership;
- performance, dialogue, sound, light, and atmosphere;
- duration and slack;
- requirement transfer;
- operation card;
- exact submission pointers;
- required, flexible, and repair criteria.

## 6. Exact submission sheet

Use the [Exact Submission Sheet](../assets/production-templates/submission-sheet.md) immediately before an operator submits a run.

It has seven required areas:

1. Target surface.
2. Operation.
3. File-to-control mapping.
4. Text fields.
5. Settings.
6. Requirements routed outside this pass.
7. Preflight.

Internal asset IDs are allowed in this operator-facing sheet. Exact model-facing text must remain self-contained or use real documented target syntax.

## 7. Exact primary prompt file

Use the [Exact Primary Prompt template](../assets/production-templates/exact-primary-prompt.txt) as the literal content of the main model-facing text field.

A strong exact prompt carries the subset that submitted media does not already supply:

```text
opening context
cause or continuing condition
dominant action and linked micro-actions
contact, ownership, and material response
camera or owner-body relation
performance change
landing
dialogue or audio only when this field owns that route
```

Do not paste internal IDs, private notes, state hashes, or inaccessible project shorthand into this file.

## 8. Separate negative or exclusion field

Use the [Separate Negative Field template](../assets/production-templates/separate-negative-field.txt) only when the exact target exposes and documents a separate field or request key.

Keep constructive camera, state, action, contact, and landing in submitted media and the primary prompt. Use concise unwanted artifact categories in the negative field. Read the final primary and negative files side by side and remove stale contradictions.

When the target has only one field, follow the integrated-exclusion rules in [`scoped-lexicon.md`](scoped-lexicon.md) and the actual target evidence.

## 9. Post-production and alternate-path plan

Use the [Post-Production and Alternate-Path Plan](../assets/production-templates/post-production-and-alternate-path.md) for every requirement not completed in the selected picture pass.

The plan covers:

- deferred requirements and their rejoin points;
- dialogue, audio, music, subtitles, and loudness;
- joins, conform, registration, masking, grade, and texture;
- identity, state, contact, prop, and background repair;
- files produced and the terminal evidence to extract after finishing.

Unsupported native behavior is not permission to delete a creative requirement.

## 10. Run observation and continuity write-back

Use the [Run Review template](../assets/production-templates/run-review.md) only after actual returned output exists.

Preserve every variant. Record direct evidence for identity, state, camera, blocking, action, contact, props, wardrobe, performance, dialogue, sound, atmosphere, landing, and artifacts. State why each variant is accepted, rejected, or repairable.

A run observation records a symptom. It does not claim a hidden model cause. A scoped tactic names exact supporting runs, the smallest concrete change, uncertainty, and a retest condition.

An accepted scene is written back to the narrative as well as to state: a promise it planted or paid off, a question it raised or answered, every beat that carried `teaches` as a knowledge entry, and the chapter and arc statuses its scenes have moved. Then approve the narrative again, because its `content_sha256` covers what it now says. [Story Structure](story-structure.md) section 6 states what each of those carries.

## 11. Documentation-grounded disclosure

Use the [Documentation-Grounded Disclosure](../assets/production-templates/documentation-grounded-disclosure.md) for a package built from current controls or official documentation that has not been executed.

The disclosure must state:

```text
Evidence state: documentation-grounded, not run.
Run status: not run.
```

It may contain actual sample files and exact proposed text. It may not narrate imaginary variants, continuity success, fidelity, or quality.

## 12. Episode or sequence archive entry

Use the [Episode Archive Entry](../assets/production-templates/episode-archive-entry.md) after picture, sound, subtitles, and finishing are accepted.

Record accepted runs, final master, opening and terminal frames, story and state changes, new and superseded assets, artifacts not canonized, unresolved risks, and the next bridge.

The archive entry points to evidence. It does not replace the asset registry, event ledger, production state, or exact run records.

## 13. Template ownership and synchronization

- Persistent project-state templates live under [`assets/project-templates/`](../assets/project-templates/).
- Operator and production templates live under [`assets/production-templates/`](../assets/production-templates/).
- Machine-readable state and viewpoint artifacts live under [`protocols/`](../protocols/).
- Examples demonstrate use but are not the canonical template source.
- Exact target files remain literal run artifacts and are never reconstructed later from a template.

When a template changes, update its validator, canonical example, contributor instructions, and generated adapters in the same release.

## 14. Master checklist

### Evidence

- [ ] Every claimed visual observation comes from media actually inspected.
- [ ] Every claimed audio observation comes from preserved audio or an explicit user run report.
- [ ] Every run has exact submitted files, text, settings, and outputs.
- [ ] Documentation-grounded examples are marked `not run`.
- [ ] Planned endpoints are not substituted for accepted finished endpoints.
- [ ] Target facts have a source, date, exact surface, and operational consequence.
- [ ] Run symptoms are not promoted to universal product limits.
- [ ] Sensitive imported material was redacted before safe remainder was stored.
- [ ] The installed suite bundle was not modified by project execution.

### Creative completeness

- [ ] The scene purpose and one-line retell are clear.
- [ ] Entry, build, turn, reaction, and landing are present when useful.
- [ ] Segment delivery role and hook obligation are explicit when relevant.
- [ ] Character-specific performance and dialogue were not erased during target rewriting.
- [ ] Relationship, state, environment, sound, and music have concrete functions.
- [ ] Independent objectives were split rather than hidden in generic prose.
- [ ] Narration, motif, and silence choices have actual production routes.

### Shot feasibility

- [ ] Opening and landing can each be visualized as one frame.
- [ ] The first action is compatible with inspected opening evidence.
- [ ] The dominant visible change can be stated in one sentence.
- [ ] Micro-actions are causally coupled rather than competing.
- [ ] Camera movement is physically available to the external rig, body owner, or device.
- [ ] Contact has ownership, occlusion, feedback, and landing.
- [ ] Off-frame geometry is not treated as inspected fact.
- [ ] Spare generated time has an intentional hold, reaction, seam, dialogue, or ambience use.

### Blocking, contact, props, and state

- [ ] Character positions, scale, facing, support, and path are camera-readable.
- [ ] Axis, screen direction, entrance, exit, and eyelines are coherent or deliberately changed.
- [ ] Moving limbs and contact ownership are unambiguous.
- [ ] A frame of two or more figures states their count and relation first, describes each figure apart, and names the carrier that keeps them apart.
- [ ] Prop owner, carrier, hand, orientation, damage, and destination are recorded.
- [ ] Cross-entity transfers are atomic.
- [ ] Wardrobe, equipment, injury, wetness, and environment state match story time.
- [ ] Flashbacks use period-correct assets.
- [ ] Concealed state remains concealed unless disclosure changes.
- [ ] Adjacent beats connect through actual end and start conditions.

### Performance and dialogue

- [ ] Selected performance details change interpretation and perform different jobs.
- [ ] Signals belong to approved anatomy and current state.
- [ ] Felt, expressed, masked, and physiological channels remain distinct.
- [ ] Name-masking and function tests pass.
- [ ] Common synthetic-dialogue tells were reviewed.
- [ ] Exact line, speaker, language, speech stage, and voice are preserved.
- [ ] Dialogue has a stable visual window or an alternate route.
- [ ] Silent reaction was considered where stronger than another line.
- [ ] Recent scenes were checked for beat-template fatigue when relevant.
- [ ] Subtitle and localization routes are separate from picture generation unless deliberately combined.

### Camera and viewpoint

- [ ] Every external shot has a concrete camera position.
- [ ] Every owned shot has a camera owner or declared device.
- [ ] Camera ownership, focalization, audition, and shot grammar are separate.
- [ ] External shots preserve or deliberately repair axis and screen direction.
- [ ] Embodied first-person movement is body-caused.
- [ ] First-person gaze reveals only what the current angle can see.
- [ ] Device faults match the declared device and use at most one deliberate fault per beat.
- [ ] Viewpoint switches have triggers, bridges, knowledge decisions, and continuity requirements.
- [ ] Camera changes do not create state changes by accident.

### Visual language and wording

- [ ] Visual language is described through observable line, shape, value, color, surface, light, lens, motion, and finish.
- [ ] Scene condition does not overwrite stable identity or style.
- [ ] Similes and speculative psychology are absent from visual blocking prose.
- [ ] Clean-realism avoid terms are applied only when clean realism is selected.
- [ ] Sound words remain attached to sound relationships, not global visual grade.
- [ ] Positive construction exists before exclusions.
- [ ] Integrated negations are complete and unambiguous.
- [ ] Text, logos, and symbols follow the selected production route and rights policy.

### Target adaptation and requirement transfer

- [ ] The selected operation carries the hardest evidence.
- [ ] Every submitted file maps to a real control or request key.
- [ ] Media contribution and prompt responsibility are stated separately.
- [ ] Input combinations are documented or directly observed rather than inferred.
- [ ] Exact primary and auxiliary field contents are preserved literally.
- [ ] Target-facing text resolves through submitted media, documented syntax, or introduced nouns.
- [ ] Primary and negative fields agree.
- [ ] Internal IDs are not mistaken for target bindings.
- [ ] Prompt rewriting or hidden transformation is recorded when known.
- [ ] Every critical requirement has a carrier, alternate route, neighboring shot, or accepted variation.
- [ ] Adaptation moved detail rather than deleting it.

### Clip packing, delivery, and transitions

- [ ] Shot feasibility was checked before duration arithmetic.
- [ ] Selected durations and settings are supported on the exact surface.
- [ ] Story duration and generated duration are both recorded.
- [ ] Timestamp language is not treated as guaranteed without evidence.
- [ ] Internal cuts are declared and each performs a visible function.
- [ ] Every boundary has a type, bridge, match point, and fallback.
- [ ] Generated transitions have operands, anchors, operation, durations, and run or operation-card IDs.
- [ ] Boundary media is conformed to delivery dimensions.

### Finishing and joins

- [ ] Registration uses delivered frames rather than planned anchors.
- [ ] Masked events follow the scene's own light and material grammar.
- [ ] Picture repairs and transforms are recorded.
- [ ] Ambient bed or deliberate silence bridges audio correctly.
- [ ] Dialogue, effects, ambience, and music authority are clear.
- [ ] Loudness and true peak are measured for the destination.
- [ ] Machine-checkable defects were checked before human review.
- [ ] Terminal frame and audio tail were extracted after finishing.

### Submission and authority

- [ ] Applicable state, morphology and viewpoint artifacts validate; exchange validation ran only for a selected public handoff.
- [ ] The exact submitted text is self-contained with the submitted media.
- [ ] The submission gate ran on that text and inputs, and every refusal and unmeasured finding was reported.
- [ ] The user confirmed the complete submission, or the plan that names it, and nothing was sent outside that confirmation.
- [ ] No returned output was regenerated on an unrequested self-assessment.
- [ ] No planned result is described as observed.
- [ ] Project state holds no unapproved canon.
- [ ] No Unicode em dash or en dash appears in runtime files.

### Run review, archive, and state

- [ ] Every returned variant was preserved and reviewed.
- [ ] Acceptance criteria are observable.
- [ ] Accepted visible and audible events are separated from artifacts.
- [ ] Generated accidents and inferred motives were not canonized.
- [ ] Scoped tactics point to exact runs and concrete changes.
- [ ] Asset registry records V and A assets with rights, consent, and limitations where applicable.
- [ ] State events, adoption records, and supersession preserve lineage.
- [ ] Episode archive points to accepted master and evidence.
- [ ] The next shot begins from the accepted finished endpoint and current resolved state.
