# Morphology and species contracts

## 1. Purpose

This reference defines how a visual contract records species anatomy, individual anatomy, fictional body plans, expression channels, and shot-visible morphology without reducing a subject to a species name or a loose list of tags.

The system has three canonical layers:

1. `species-morphology-profile`: the valid anatomical and expressive possibility space for a species, lineage, chassis family, or original creature class.
2. `individual-morphology-contract`: the exact realization for one recurring character or one identifiable animal, creature, hybrid, robot, or android.
3. `resolved-morphology`: the shot-specific visible result after current form, state, crop, pose, clothing, occlusion, damage, and expression are applied.

A species noun is not a complete morphology contract. A familiar noun may help retrieval, but every production-critical count, attachment, shape, dimension, surface, motion range, and expression carrier must be declared or explicitly left unresolved.

## 2. Ownership and precedence

Use the following precedence order:

1. Explicit user statement.
2. Approved species or lineage profile.
3. Approved individual morphology contract.
4. Approved current state and form events.
5. Shot-specific resolved morphology.
6. Retrieval heuristics and model priors.

A lower source never silently changes a higher source. A model prior cannot add undeclared wings, tails, eyes, digits, tentacles, horns, sensors, masks, or internal organs. A reference image cannot override an explicit user species label without a disclosed correction request.

## 3. Species profile scope

A species profile may describe:

- a real biological species;
- an ordinary animal body plan;
- an anthropomorphic realization of a real animal family;
- a fictional species;
- a custom hybrid lineage;
- a creature class with no natural taxonomy;
- a robot chassis family;
- an android platform;
- an energy, fluid, modular, colonial, or distributed organism;
- a transformation form whose topology differs from the baseline form.

`reality_status` records whether the profile is real, fictional, custom, hybrid, mechanical, or otherwise authored. `taxonomy_or_origin` may use biological taxonomy, design ancestry, engineering lineage, mythic influence, or a direct original-construction statement. A fictional species does not need a real-world taxonomic substitute.

## 4. Complete feature inventory

The species profile inventories every production-relevant feature. For each feature, record at least:

- feature ID and feature kind;
- feature group or organ system;
- presence or explicit absence;
- typical, minimum, and maximum count;
- laterality or radial distribution;
- attachment site and parent features;
- attachment landmarks and branching sequence;
- length, width, thickness, spacing, and body ratio;
- measurement basis and permitted tolerance;
- shape, taper, curvature, orientation, and resting configuration;
- color, pattern, texture, material, and surface response;
- articulation and range of motion;
- functional role;
- expression or communication role;
- life-stage, dimorphic, seasonal, metamorphic, and shedding behavior;
- individual variation axes;
- cross-feature dependencies;
- continuity rules;
- views required to prove the feature;
- source confidence and unresolved questions.

Do not treat a list of present features as complete unless important absent features have also been reviewed. `inventory_completeness.explicitly_absent_or_inapplicable` records meaningful absences such as no tail, no external ears, no mouth, no wings, no eyes, or no physical hands.

## 5. Body regions and topology

The body plan defines the region graph before detail is added. Each region has:

- a stable region ID;
- a parent region or root status;
- named landmarks;
- bilateral, radial, distributed, or centerline behavior;
- continuity rules.

Examples include head, sensory crown, neck, thorax, abdomen, pelvis, limb girdle, wing root, tail base, tentacle ring, chassis core, faceplate, and detachable tool mount.

Topology is more important than surface appearance. A correct color cannot compensate for a tail attached to the lumbar spine instead of the posterior pelvis, an eye floating outside the orbital structure, or a wing connected to the forearm when the species profile declares a scapular root.

## 6. Counts and instance identity

Counts must be explicit.

Examples:

- two arms and two legs;
- four eyes in two vertical pairs;
- one primary tail and two shorter balance tails;
- six radial tentacles around a central mouth;
- no external ears;
- variable horn count from two to four under a declared polymorphism;
- one detachable sensor mast that may be temporarily absent from a scene but remains part of the individual contract.

For recurring subjects, each repeated or asymmetric feature receives stable instance IDs when necessary, such as `eye-left-upper`, `tail-secondary-right`, or `wing-dorsal-02`. Damage, markings, accessories, and state changes attach to the instance rather than to a vague feature class.

## 7. Limbs, hands, feet, digits, claws, and terminal structures

Record each limb system independently:

- count and bilateral or radial arrangement;
- upper and lower segment proportions;
- joint order and range;
- muscle, fur, scale, plate, or material distribution;
- hand, paw, hoof, fin, manipulator, or tool-interface class;
- digit count per limb;
- digit ordering, opposability, webbing, pads, claws, nails, talons, suction cups, or terminal plates;
- whether terminal structures retract, fold, detach, glow, or change under state;
- contact and load-bearing behavior.

Human nails, canine claws, feline retractable claws, avian talons, hoof walls, robotic fingertip plates, and tentacle suction cups are distinct terminal systems. Do not average them into a generic hand.

## 8. Head and sensory cluster

Record the presence, count, attachment, dimensions, and shape of:

- eyes or optical sensors;
- eyelids, shutters, nictitating membranes, pupils, apertures, or lenses;
- nose, nostrils, olfactory pits, antennae, whiskers, or chemical sensors;
- mouth, muzzle, beak, mandibles, proboscis, feeding aperture, or speaker grille;
- teeth, fangs, tusks, plates, tongue, inner mouth, or feeding tools;
- ears, auditory membranes, antennae, sonar structures, or integrated microphones;
- horns, antlers, crests, mane, cheek ruff, facial plates, and face masks.

Near-species diagnosis must prioritize structural evidence. For example, large feline and canine faces should be compared by muzzle reach and depth, muzzle shadow, ear-tip geometry, nose thickness and projection, cheek volume, and jaw shape. Coat color or generic triangular ears are insufficient.

## 9. Tails, wings, fins, tentacles, and special appendages

For every appendage, declare:

- presence and exact count;
- attachment region and base spacing;
- segment count or branching pattern;
- length, width, thickness, taper, and tip shape;
- surface and underside differences;
- resting pose and full motion range;
- load-bearing, balance, flight, swimming, grasping, display, defense, sensory, or reproductive function;
- expression role;
- clothing, harness, armor, chair, and crop clearance;
- required views that prove attachment and count.

A tail is not fully defined by color and length. The contract must state where it grows, how thick the base is, how it tapers, whether it is prehensile, how it bends, and which emotional motions are normal for the species and individual.

## 10. Skin, fur, scales, feathers, shells, and materials

Surface systems are region maps, not color names. Record:

- regions covered;
- material or integument class;
- base color logic;
- marking topology and boundary shape;
- directional growth or plate order;
- length, density, thickness, relief, and edge behavior;
- wetness, sweat, oil, reflection, subsurface, and rim-light response;
- damage, shedding, molting, rust, cracking, repair, and regeneration behavior;
- seams between surface systems.

An individual surface map resolves exact markings, scars, tattoos, notches, discoloration, worn paint, repaired panels, and asymmetries. Scene lighting may change perceived value but does not move a marking to another body region.

## 11. Special organs and capabilities

Fictional and mechanical subjects may have organs or systems not covered by ordinary anatomy. Use feature kinds such as:

- gill or respiratory organ;
- luminous organ;
- energy structure;
- fluid organ;
- shell or carapace;
- pouch;
- sensor array;
- tool interface;
- mask or faceplate;
- integrated display;
- detachable module;
- regenerative or metamorphic organ.

Each capability points to the feature carriers that physically enable it. Flight requires declared wings, control surfaces, body mass logic, and an attachment system. Bioluminescent communication requires declared luminous regions, controllable color or pulse dimensions, and readable states. A capability is invalid if its carrier features are absent.

## 12. Expression and communication grammar

Species expression is a coordinated system, not a universal human-face overlay. Record every channel the species can use:

- gaze, lids, pupils, shutters, or optic brightness;
- brows, supraorbital plates, crest angle, or faceplate movement;
- mouth, jaw, tongue, beak, mandibles, or speaker output;
- cheek color, skin flush, chromatophores, fur lift, feather spread, scale sheen, or panel light;
- ears, antennae, whiskers, horns, mane, ruff, hackles, fins, wings, tails, tentacles, or posture;
- breath, heat, scent, fluid, vibration, sound, servo cadence, fan speed, or electrical pulse;
- hands, paws, feet, manipulators, tools, signs, badges, screens, or cultural props.

For each channel, record neutral state, active configurations, controllable dimensions, timing, meanings, ambiguity, and cross-channel coordination. A single cue does not prove one emotion. Red cheeks may indicate embarrassment, attraction, exertion, heat, illness, anger, alcohol, or reflected light. Meaning is selected from the coordinated cue bundle and scene context.

Expression tools may be biological, mechanical, worn, held, cultural, assistive, or profession-specific. Examples include a robot visor, color-changing collar, sign board, handheld fan, scent dispenser, ritual mask, or communication tablet. The species profile declares the possible tool relationship. The individual contract declares the exact tool realization.

## 13. Individual morphology contract

The individual contract resolves one subject from the species possibility space. It records:

- life stage, sex or role morph, and active baseline form;
- overall scale and proportions;
- exact feature count and stable instance IDs;
- exact measurements and tolerances;
- exact attachment offsets and angles;
- individual colors, markings, scars, tattoos, notches, missing segments, repairs, prosthetics, and modifications;
- exact hair, grooming, nail, claw, horn, feather, panel, and surface treatment;
- individual expression habits and timing;
- individual communication tools;
- stable asymmetries;
- identity-priority features;
- approved variation fields;
- mutable state paths;
- unresolved features and their permitted treatment;
- differences from similar individuals.

Do not copy every species feature into prose. Store one feature realization per production-relevant species feature and preserve the reference to the species definition. The individual record states what is different, exact, damaged, selected, or personally characteristic.

## 14. Identity versus state

Use this boundary:

- species invariant: valid for the species or lineage;
- individual identity: stable for this subject across ordinary scenes;
- form identity: stable while one approved form is active;
- state: changes with events, time, environment, injury, emotion, grooming, clothing, or equipment;
- shot projection: visible in this shot after crop and occlusion.

Examples:

- one tail at the posterior pelvis: species and individual morphology;
- dark tail tip pattern: individual morphology;
- tail temporarily bandaged: state;
- tail outside a waist-up crop: shot projection;
- tail cut off by an approved event: state change that may later require a revised individual or form contract after canon review.

Unknown information remains unknown. Do not convert an occluded feature into an absence or invent an exact shape that the source does not support.

## 15. Near-species and near-individual differentials

Each species profile may contain structured comparisons with commonly confused species. Each individual contract may contain comparisons with similar individuals.

A useful differential names:

- shared traits;
- diagnostic differences;
- reliable views;
- misleading views or lighting;
- common model errors;
- constructive correction guidance.

Examples include feline versus canine face scaffolds, wolf versus fox ear and muzzle proportions, leopard versus jaguar rosette topology, bird wing versus draconic membrane attachment, tentacle versus tail articulation, organic eye versus display lens, and two characters with similar coat color but different markings and asymmetry.

## 16. Fictional species workflow

When the user introduces a species that has no established taxonomy:

1. Preserve the supplied name as the canonical species or lineage name.
2. Mark the reality status and origin as original, fictional, hybrid, mechanical, or other declared class.
3. Build the region map and body topology before styling.
4. Inventory all visible and production-relevant features.
5. Record important absences.
6. Declare feature counts and attachments.
7. Declare materials and surfaces.
8. Declare locomotion, manipulation, feeding, sensing, communication, and expression systems.
9. Declare developmental, polymorphic, and form-change rules.
10. Declare near-species or near-design differentials when confusion is plausible.
11. Resolve one individual contract without silently turning optional species variation into this character's identity.
12. Generate coverage requirements that prove count, attachment, front, profile, rear, underside, and special-organ behavior.

The system does not require a real animal label. Direct geometry and topology are authoritative.

## 17. Resolved morphology for a shot

`resolved-morphology` combines the approved species profile, individual contract, current state, and shot request. It contains:

- active form;
- body plan;
- visible feature instances;
- hidden or out-of-frame feature references;
- resolved feature relationships;
- surface and marking map;
- active expression channels and tool states;
- identity invariants;
- current state deltas;
- inventory proof for count and attachment;
- visible obligations;
- crop and occlusion requirements;
- unresolved uncertainties.

Every visible feature must exist in the individual contract. Hidden features remain declared rather than disappearing from the body plan. A crop may omit a leg, tail, wing, or antenna from the image, but the prompt and review contract must prevent the generator from interpreting the crop as anatomical absence or truncation.

## 18. Coverage planning

A reference bundle should prove:

- full front and rear body topology;
- left and right profile or three-quarter head structure;
- attachment sites for tails, wings, horns, tentacles, and special organs;
- hands, paws, feet, hooves, fins, digits, nails, claws, talons, or manipulators;
- surface and marking continuity;
- asymmetries and identity accessories;
- expression channels in neutral and active states;
- tool-mediated signals;
- any underside or hidden structure that later scenes must reproduce.

A single flattering portrait is not sufficient evidence for a complex fictional species.

## 19. Which authority settles what

Species, individual, identity, form and appearance contracts settle different scopes of visual design. Narrative, persona and world records settle the intended subject and telling. Approved events settle variable state; projections settle what an operation can show; adopted media settles what a file visibly proves. All of these can be authored in one project. They are not responsibility assignments to different applications.

Author missing design here under the user's direction. A public artifact supplied for use is inspected under the same evidence rules. Bind species, individual, identity and state by hash; name visible feature refs and scene, camera and projection evidence when needed. A state event does not rewrite species anatomy, and a visual result does not establish a story event. Topology revisions and canon changes require explicit approval and new lineage.

## 20. Review checklist

Before approving a species or individual contract, confirm:

- every major body region has been considered;
- meaningful absences are explicit;
- feature counts are explicit;
- repeated features have stable instance IDs when needed;
- attachments are named by landmark;
- measurements use declared references;
- surfaces and markings have stable region paths;
- expression channels fit the body plan;
- external expression tools are declared;
- life stage and polymorphism do not silently change identity;
- state boundaries are clear;
- near-species differences are diagnostic rather than color-based;
- fictional capabilities have physical carriers;
- coverage views can prove the anatomy;
- unresolved information remains unresolved;
- the shot projection carries only approved visible changes.

## 21. Storage and pointers

The body plan is not duplicated in prose here. Project records point to the approved artifacts and hashes:

- Species Morphology Profile ID and SHA-256;
- Individual Morphology Contract ID and SHA-256;
- Character Identity Contract ID and SHA-256;
- active Era, Form, and Appearance Variant Contracts;
- adopted reference sets that visibly prove the declared feature inventory;
- unresolved morphology questions that still block a shot or asset adoption.

`character-profiles.md` keeps these pointers and a human-readable differential summary. The exact feature inventory remains in the machine-readable contracts. `asset-registry.md` records which adopted files visibly prove each view, count, attachment site, marking path, surface, appendage, tool, or expression channel. A text statement may establish canon, but it is not a visual lock unless adopted media or another accepted carrier proves the relevant appearance.

## 22. Temporal changes and topology revisions

Ordinary state events may alter only paths declared mutable by the individual contract or the active form contract. Examples include wetness, flushing, pupil aperture, feather spread, tail pose, temporary swelling, deployed tools, damaged clothing, dirt, temporary injury, and reversible mechanical configuration.

A change to feature count, attachment topology, body-region graph, organ presence, limb class, or permanent individual anatomy requires one of the following:

1. an approved Form Contract whose topology change is already permitted by the species and individual contracts;
2. an approved revision of the Individual Morphology Contract;
3. an approved new species or lineage profile when the prior profile never allowed the form;
4. an editorial supersession event that explicitly changes canon and records lineage.

An offscreen event can change state. It cannot silently rewrite anatomy. A crop can hide a tail, wing, limb, horn, or sensor. It cannot make the feature cease to exist. A generated omission remains observed drift until approved as a canon change.

## 23. The shot-request and visible morphology obligations

For every visual shot, the current state is resolved here and the shot-request carries:

- `species_profile_sha256_by_character`;
- `individual_morphology_sha256_by_character`;
- `identity_contract_sha256_by_character`;
- `state_snapshot_sha256_by_character`;
- `visible_morphology_feature_refs_by_character`;
- shot camera, crop, occlusion, contact, and deliverable evidence;
- visibility obligations for counts, attachment sites, surfaces, markings, tools, and expression channels;
- accepted references whose visible support matches the shot.

The feature refs are not a decorative list. They determine which feature instances must be proved in the shot and which may remain outside frame. A full-body shot may require limb count, tail attachment, and foot structure. A close profile may require one ear, muzzle projection, nostril geometry, cheek volume, eye profile, horn root, or side-mounted sensor while declaring other features out of frame.

Resolve these explicitly selected inputs into `resolved-morphology`, then validate the same species, individual, identity, state, scene and camera bindings before packaging the target operation. An explicitly supplied projection follows that same check; its source does not change the rule.

## 24. Public artifact exchange

Public schemas define data, not the internal layout or responsibilities of an application. `protocols/contract-manifest.json` records the installed schema closure and semantic commitments. `scripts/protocol_exchange.py` inspects or exports a selected artifact and verifies a supplied bundle without reading an installation or a private registry.

For a declared feature profile, use an `interchange-envelope` and its supplied `declaration.json`. `external-contract-reference` records the payload hash, profile, required and optional features, interpretation, adoption status and valid story range. Unknown optional meaning can be retained as opaque evidence; unknown required meaning cannot be acted on.

`python scripts/validate_integration.py` validates the bundled capability declaration. To inspect a real incoming bundle, supply `--direction consumes --envelope FILE --declaration FILE --payload-root DIR`. There is no software discovery step. Design and generation do not require exchange. See [Visual contracts](visual-contracts.md) for the design and reference-activation paths.
