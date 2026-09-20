# Temporal Character State and Shared State Protocol

Time-varying state must not overwrite stable identity or morphology, and generated accidents must not become canon.

## 1. Five distinct records

1. Species morphology: what body plans, features, absences, counts, materials, capabilities, and expression systems are valid for the lineage.
2. Individual morphology and identity: the exact recurring subject, including feature instances, proportions, markings, asymmetries, grooming, damage, and personal expression behavior.
3. Canonical state: what is true at one story time.
4. Visual state projection: what one scene and camera should show.
5. Observed render state: what returned media actually contains.

A prompt does not prove that a state appeared. A render does not become canon automatically. A state snapshot does not prove that a feature is visible from the selected camera. A crop does not delete a body part.

## 2. Canonical and derived artifacts

```text
state/events.jsonl                 canonical event history
state/processes/                   approved progressive changes
state/snapshots/                   derived world and character state
state/scene-contexts/              derived scene context
state/visual-projections/          shot-visible state and resolved morphology
state/relationships/               relationship state and scene projections
state/wardrobe/                    resolved clothing layers and conditions
state/inventory/                   ownership, possession, equipment, and transfer state
state/reference-selections/        state-aware adopted asset selection
state/candidate-manifests/         immutable producer evidence
state/external-contracts/          content-addressed external contract references
state/adoption-receipts/           adoption decisions issued by this suite
state/observations/                non-canon render evidence and drift observations
```

Species, individual morphology, identity, era, form, and appearance contracts are approved source contracts referenced by hashes from project records and derived artifacts. They are not current-value snapshots.

Edit canon by adding or superseding approved events, then rebuild derived artifacts. Do not edit a snapshot, projection, relationship record, wardrobe record, inventory record, or selection as the source of truth.

## 3. Morphology authority and mutable boundaries

The species profile defines the valid possibility space. The individual contract chooses one exact recurring realization. The identity contract adds identity-bearing visual facts and anchors. Era, Form, and Appearance Variant Contracts declare approved changes with explicit scope.

An ordinary state event may alter only a path declared mutable. Examples include:

- wetness, dirt, flush, tears, sweat, temporary swelling, injury, healing, fatigue, and temperature response;
- hair or fur displacement, feather spread, tail pose, pupil aperture, chromatophore state, active glow, and breathing state;
- garment layers, openings, damage, carried equipment, deployed panels, and detachable tools;
- current emotion, masked emotion, relationship performance, and communication-tool state.

Feature count, attachment topology, body-region graph, permanent organ presence, limb class, or persistent individual anatomy requires an approved Form Contract, an approved morphology revision, or an explicit editorial supersession. Offscreen occurrence does not relax that requirement.

## 4. Event semantics

Every event records:

- timeline and effective story order;
- story time, production record time, and disclosure time;
- onscreen, offscreen, or editorial occurrence;
- canon status and evidence;
- preconditions;
- state changes and persistence;
- atomic multi-entity behavior when needed;
- affected morphology path when a declared mutable feature changes;
- required form or contract lineage when topology changes.

Use separate effective, recorded, and disclosed times. A character may already be injured while the viewer does not yet know it.

## 5. Persistence classes

- scene-local;
- temporary-until-cleared;
- decaying;
- progressive;
- persistent-until-superseded;
- era-level;
- form-level.

Temporary state needs an end order, clearing event, or process. Progressive state uses authored milestones. The resolver emits discrete promptable states and does not invent unsupported numerical interpolation.

A form-level change is not merely a long temporary state. It selects an approved form topology and the matching morphology evidence.

## 6. Flashbacks, jumps, branches, and development

A flashback resolves the same timeline at an earlier story order. It does not infer the past from the current appearance.

A large time jump may propose an Era Contract. Age, scale, weight, hair, fur, scars, posture, organ development, horn or antler growth, molting, panel replacement, and tool integration do not change automatically. The species profile may define developmental possibilities, but the individual history and approved era or form choose the realized state.

Alternate histories use another timeline ID. Editorial revisions supersede prior canon from a declared order and do not erase earlier historical snapshots.

## 7. Emotion, relationship, and species-specific expression

Keep emotional channels separate:

- felt state;
- expressed state;
- masked social state;
- physiological cues.

Keep relationship state directional and separate from current emotion. Project approved relationship facts into distance, orientation, gaze order, contact initiation, contact boundaries, protective blocking, prop transfer, and public or private behavior.

Expression uses the subject's declared carriers. A human may use gaze, brows, mouth, hands, posture, blush, tears, or voice. An anthropomorphic animal may also use ears, whiskers, ruff, hackles, tail, wings, horns, paws, scent, or species-specific displays. A creature may use chromatophores, tentacles, fins, crests, fluid, vibration, light, heat, or specialized organs. A robot may use optics, shutters, faceplates, antennae, manipulators, panels, indicator lights, fan or servo cadence, display surfaces, and external tools.

Do not impose a universal human facial grammar on a subject whose morphology does not support it.

## 8. Environment, wardrobe, inventory, and morphology clearance

Environment includes season, time, weather, temperature, humidity, wind, precipitation, water exposure, light, surface condition, location, and approved locale rules.

Environment may produce an appearance adaptation proposal. It cannot create canon automatically.

Track wardrobe through layers and conditions such as worn, carried, removed, open, closed, rolled, loosened, wet, dry, torn, repaired, or dirty. Garment geometry must preserve clearance for tails, wings, horns, fur, shells, tentacles, gills, chassis joints, detachable tools, and other declared features.

Track objects through ownership, possession, carrying, equipment, storage, consumption, loss, damage, repair, or transfer. Cross-character transfer is one atomic event.

## 9. Scene and shot compilation

```text
species morphology + individual morphology + identity
+ era, form, and appearance contracts
+ approved events and processes
= character state snapshot

character snapshots
+ relationships, environment, wardrobe, inventory, disclosure
= scene context snapshot

scene context
+ shot camera, crop, visibility, contact, and performance
= shot visual projection with resolved morphology
```

Only the shot projection enters media and prompt construction. Do not paste full history into target text.

The projection declares visible feature instances, hidden or out-of-frame features, count and attachment proof, surface and marking state, expression channels, external tools, current state deltas, crop rules, occlusion rules, reference requirements, and uncertainties.

## 10. Within-shot and within-scene transitions

A visible change uses:

```text
start snapshot
planned transition event
end snapshot proposal
```

Route opening state to start media, change mechanics to motion direction, and landing state to endpoint media or landing text. Canonize the event only after acceptance.

When a change affects a body feature, the transition must name the carrier and valid motion or transformation path. A wing unfolds from its declared root. A tail moves without changing attachment. A panel deploys along its joint. A true topology change selects an approved form rather than morphing an undeclared body part into existence.

## 11. Reference selection and proof

Reference selection is camera-aware and morphology-aware. Select assets that visibly prove the features required by the current shot. Record unsupported sides, attachment sites, counts, materials, markings, expressions, and special organs.

Old assets remain valid for their approved era and form. Do not use a current-form portrait as proof for a flashback form. Do not use a close front portrait as proof for rear topology, tail attachment, wing roots, or underside structure.

## 12. Validation gates

The shot handoff uses `species_profile_sha256_by_character`, `individual_morphology_sha256_by_character`, `identity_contract_sha256_by_character`, `state_snapshot_sha256_by_character`, and `visible_morphology_feature_refs_by_character`.

- species and individual morphology hashes match the identity and shot request;
- every visible morphology ref exists in the approved individual contract;
- visible feature counts and attachment sites remain within the species and individual contracts;
- hidden or cropped features remain declared rather than becoming anatomical absence;
- topology changes have approved form or contract lineage;
- approved events have evidence and story order;
- temporary state has an endpoint or process;
- preconditions match prior state;
- multi-entity transfers are atomic;
- flashbacks use period-correct assets and morphology;
- signature visible changes have a carrier;
- unresolved conflicts stop packaging;
- observed state remains non-canon by default;
- every persisted artifact carries a valid canonical hash;
- applicable public declarations and typed artifacts validate; optional receipt uses the supplied declaration and payload rather than an installation.
