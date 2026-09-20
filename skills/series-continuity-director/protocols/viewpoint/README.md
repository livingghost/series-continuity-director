# Series Viewpoint Protocol

This protocol separates camera ownership, knowledge scope, point of audition, shot grammar, and viewpoint transitions. Series Continuity Director uses external character-aligned third person as the default profile and allows another profile per shot when the scene benefits from a different relationship to the action.

## Artifact identification

The product release is versioned as one unit. Protocol artifacts do not carry an independent schema or protocol number. Each artifact is identified by `artifact_type`, validated against the schema files shipped in the installed product release, and sealed with its canonical content hash where applicable. The JSON Schema `$schema` URI selects the external validator dialect and is not a product-managed version.

## Canonical artifacts

- `viewpoint-profile`: camera and continuity grammar for one viewpoint family.
- `scene-viewpoint-plan`: the scene default and ordered shot references.
- `shot-camera-spec`: concrete camera position, movement, axis, eyeline, crop, anchors, and visible subjects for one shot.
- `viewpoint-transition`: the editorial bridge and continuity requirements between two shots.
- `shot-continuity-ledger`: a derived ledger that carries screen direction, axis side, prop ownership, state hashes, and transition requirements across a scene.
- `shot-visual-projection`: the identity, state, wardrobe, relationship, and environment obligations that are actually visible from one camera.
- `shot-request`: the sealed request for one still, boundary frame, reference image, or production prompt. It may also carry `scene_plot_sha256`, the approved scene plot the shot was planned in, and `narrative_sha256` beside it, so whatever plans the frame names the same artifact as its source instead of starting a second approval chain for the same frame.

## Default profile

The default profile is `external-character-aligned-third-person`.

The camera remains outside all characters, but one focal character guides attention, knowledge scope, and performance emphasis. The scene may switch to over-the-shoulder, embodied first-person, a device view, an objective external shot, or a fixed in-world camera when the switch has a concrete story or continuity purpose.

## Separation rules

1. Camera ownership is physical. It states who or what carries the camera.
2. Knowledge scope is how far one shot's knowledge reaches. It states whose knowledge and attention constrain what may be revealed, and it is not the scene plot's narrative `focalization`, which is the whole scene's and is published in the narrative protocol.
3. Point of audition is sonic. It may remain objective while the camera changes, or become character-subjective without a camera cut.
4. Shot grammar is geometric. It states position, lens behavior, movement, screen direction, axis side, eyeline, visible subjects, and start and end anchors.
5. A viewpoint switch does not change canon by itself. A state change needs its own approved or planned state event.

## Third-person continuity

External shots preserve or deliberately re-establish:

- axis of action;
- screen direction;
- eyeline height and target;
- prop ownership;
- body and wardrobe state;
- start and end anchors;
- matching action and subject entrance or exit direction.

A camera move is complete only when the record states its purpose, start relation, path, speed and amplitude, subject relation, occlusion risk, and landing composition.

## First-person continuity

Embodied first-person is one profile, not the product default. The camera belongs to a declared character body, visible limbs belong to that character, and movement follows the body rather than a detached rig. An external view of the camera owner requires a separate shot, a real reflection, a display, or another deliberate construction.

## Knowledge control

A character-restricted shot may show only information that the focal character can perceive at that story moment. An external camera does not automatically grant omniscience. A deliberate reveal uses an objective or omniscient shot and records the knowledge change or lack of one.

## The shot-request

The `shot-request` carries only the state and identity obligations visible in the selected shot. Different camera angles may select different approved character references. Changing camera position does not change the stable identity contract.

## Validation

Use:

```bash
python scripts/viewpoint_protocol.py validate protocols/viewpoint/profiles/external-character-aligned-third-person.json
python scripts/viewpoint_protocol.py validate-tree examples/mixed-viewpoint-workshop/generated
```

Templates intentionally contain all-zero placeholder hashes. Runtime artifacts must contain valid canonical hashes.

Ledger construction validates every scene plan, shot, and transition before use. It rejects duplicate IDs, artifacts from another scene, shot profile/order mismatches, unknown transition endpoints, and unresolved continuity. Per-character hash maps accept only canonical lowercase SHA-256 values.

See the [command-line interface reference](../../scripts/README.md) for complete inputs, outputs, side effects, and failure conditions.
