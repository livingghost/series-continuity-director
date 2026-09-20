# Operational Distinctions: The Operator Action Is the Difference

Short labels help index production records, but a label is never the instruction. A distinction belongs in the workflow only when it changes submitted media, the real field that receives it, exact wording, shot design, post-production, or required evidence.

For every named distinction, answer:

1. What does the operator do differently?
2. What does the target receive differently?
3. What exact text or shot design changes?
4. What failure becomes likely when the cases are confused?

## 1. A start frame is not a character reference

Same intent: a recurring wolf mechanic stands beside a workbench and receives a cracked pendant.

### Submission A: the character is already in the start frame

Operator action:

```text
workshop-with-wolf.png -> Start image control
```

The image supplies opening composition, character placement, visible pose, room geometry, light, and visible wardrobe. The exact text can concentrate on change:

```text
C02 raises the cracked pendant across the workbench. The wolf mechanic stops, shifts the guarded left shoulder back, reaches with the right hand, and closes the fingers before C02 releases. The external camera remains on the doorway side and settles with both faces and the pendant visible.
```

### Submission B: the workshop and character are separate inputs

Operator action:

```text
empty-workshop.png -> Start image control
wolf-reference.png -> documented character-reference control
```

The workshop image does not place the wolf. The text or another composite must establish placement and scale:

```text
Start from the supplied empty workshop. Place the referenced wolf mechanic one step behind the near side of the central workbench, correctly scaled to the bench, facing C02 across it. The left side remains guarded. C02 raises the cracked pendant, and the mechanic receives it with the right hand while the external camera stays on the doorway side.
```

If the target has no character-reference field, calling the second image a character reference has no operational effect. Build a composite start image, accept text-generated identity variation, use an edit route, redesign the shot, or choose another documented operation.

## 2. A planning image is not a submitted image

A storyboard, blockout, or layout can guide the director without reaching the target.

Planning-only use:

```text
The director sees the workbench at frame center and a rear-left doorway, but neither the image nor a sentence about those facts is submitted. The target is not constrained by that layout.
```

Transferred use:

```text
The start image visibly contains the central workbench and rear-left doorway.
```

or:

```text
The exact prompt states that the central workbench divides C01 and C02 and the rear-left doorway stays visible behind C01.
```

Record the transfer path from planning material to submitted media, exact text, source operand, mask, or edit instruction. Do not describe planning-only material as target-bound evidence.

## 3. A video reference is not a video operand

Same source clip: a camera follows a character through a narrow hall and turns right at the end.

### Reference use

The target observes the clip as guidance while generating new frames:

```text
hall-walk.mp4 -> documented motion-reference control
new scene and character media -> their own controls
```

Exact text identifies selective intended influence:

```text
Use the supplied motion reference for walking cadence and the single right turn. Generate a torch-lit stone corridor with C01 one pace ahead. The source walls, people, colors, and audio are not part of the intended scene.
```

Whether the target isolates those dimensions remains empirical.

### Operand use

The target edits, restyles, extends, or transforms actual source frames:

```text
hall-walk.mp4 -> source-video operand in an edit or restyle operation
```

Exact text describes the delta:

```text
Retain the source camera path, timing, walking cadence, and final right turn. Replace the modern hall with the approved stone corridor and replace the visible guide with C01 in the current wardrobe.
```

A reference may be reinterpreted. An operand may inherit frames and timing more directly. The operator action, prompt, and review are different.

## 4. A performance driver is not a generic motion reference

A dedicated performance-transfer surface may use one source for timing, gesture, face, or speech and another for character identity.

```text
driver-performance.mp4 -> documented driving-performance control
character-front.png -> documented character control
canonical-line.wav -> documented audio or speech control
```

The production package states what each source supplies:

```text
Driver supplies: body timing, head turn, right-hand gesture.
Character media supplies: identity, markings, wardrobe.
Audio supplies: exact line and timing.
Scene media or text supplies: environment and camera.
```

Review against the driver and character media separately. Calling all three files references hides speaker ownership, timing authority, and transformation behavior.

## 5. Start-only and start-plus-end submissions require different writing

Same intent: C01 moves from standing beside the bench to seated on a stool with the pendant in the right hand.

### Start image only

The endpoint exists only in direction:

```text
C01 steps around the near corner of the bench, turns enough to clear the stool, and lowers into the seat while keeping the pendant in the right palm. The stool takes the weight, the coat hem settles, and C01 finishes facing C02 across the bench.
```

### Start and end images

Both endpoint compositions are submitted:

```text
Connect the supplied start and end frames with one natural action. C01 takes the short path around the bench, turns only enough to clear the stool, and sits without changing the right-hand hold on the pendant. The stool and coat respond before the torso settles into the supplied ending.
```

The second text directs a path between visible endpoints. It should not redescribe them at length or introduce another landing.

## 6. A text continuity fact is not visual evidence

Project fact:

```text
The cracked pendant belongs to C01 after the transfer.
```

When no pendant image is submitted, the model must invent appearance from text. Ownership continuity remains required, but exact scratches, chain links, scale, and color are not visually bound.

Record the actual evidence:

```text
Ownership is canonical. The pendant is text-described in this generation. Exact surface detail may vary because no prop media is submitted.
```

When exact appearance matters, include it in a submitted start or end image, use a documented prop-reference path, or create an edit/composite. Do not delete the continuity fact, and do not claim a visual lock that does not exist.

## 7. A planned endpoint is not the next shot's opening evidence

Planned landing:

```text
C01 sits upright on the stool, pendant centered in the right palm, external camera level on the doorway side.
```

Accepted output may instead show:

```text
C01 sits farther back, the right forearm crosses the torso, the pendant hangs from the fingers, and the camera is slightly lower.
```

The next shot begins from the accepted finished geometry or from an explicitly created corrective derivative. Repeating the planned landing as if it were observed creates a seam discontinuity.

## 8. Same-pass dialogue and post-produced dialogue are different productions

Canonical line: C01 says, "I kept it."

### Dialogue generated with picture

The selected operation must support dialogue or audio direction. The exact text coordinates speech and visible action:

```text
After the pendant settles in the right palm, C01 holds still, looks toward C02, and says quietly, "I kept it." The mouth movement belongs to C01 and the workshop machinery remains underneath.
```

Review wording, speaker, mouth movement, timing, voice, and mix separately.

### Dialogue added later

The picture prompt protects a performance window:

```text
After the pendant settles, C01 holds the final pose for one second, keeps the eyes on C02, and makes only a small breath and restrained mouth movement.
```

The production plan separately stores the line, speaker, voice, timing, lip-sync or dubbing operation, and mix. Moving the line out of the picture pass does not remove its story function.

## 9. A selectable duration is not timestamp obedience

A surface may offer an eight-second duration without reliably following clauses such as `0-2 seconds` and `2-5 seconds`.

Keep these observations separate:

```text
Documented control: the operator can select an eight-second output.
```

```text
Observed run behavior: in three of four variants, the handoff completed before the line and the final hold lasted one visible beat.
```

Use precise timestamps only when the current surface documents or repeated preserved runs support that syntax. Otherwise use causal ordering and judge actual sequence. Post-production timelines may still use exact timecodes.

## 10. A model-facing prompt is not the whole production

A concise exact prompt may omit room details because the start image visibly supplies them. It may omit dialogue because the line is assigned to post. These omissions are valid only when the director package and requirement-transfer record show where each requirement went.

Completion question:

```text
Can every important story, performance, continuity, state, camera, sound, and endpoint requirement be located in submitted media, an exact target field, another operation, post-production, a neighboring shot, or an explicitly accepted variation?
```

## 11. A viewpoint label is not concrete camera direction

`external-character-aligned-third-person` is useful inside production records. Most targets need concrete direction instead:

```text
External medium shot from the doorway side of the workbench, camera at shoulder height, aligned with C01's attention. C01 remains frame-left facing C02. Track half a step right during the handoff and finish with both faces and the pendant visible.
```

Likewise, `embodied-first-person` must be translated into owner body state, visible limbs, gaze path, body-caused motion, audition, contact, and landing. Keep the profile ID for validation and continuity, not as a substitute for camera prose.

## 12. Workflow stages are evidence changes, not mental modes

Stage names are navigation headings. The concrete difference is what evidence exists and what artifact that evidence is sufficient to finish.

Before an actual start image exists:

```text
Design the required composition and write the media brief. Do not claim inspected geometry.
```

After the real start image is available:

```text
Inspect visible geometry, revise blocking to fit it, and prepare the director package and exact target submission.
```

After returned variants exist:

```text
Inspect every variant, compare the actual ending with the planned ending, finish the accepted result, and continue from its extracted endpoint.
```

Do not treat Stage A, B, or C as an invisible reasoning switch. Evidence and deliverables change; the production principles remain active throughout.

## 13. Distinction completion check

For every distinction used in a package:

- the operator action differs;
- the target receives different files, fields, or operations;
- exact wording or shot design changes;
- review evidence changes;
- the likely confusion failure is recorded;
- private labels do not substitute for actual bindings;
- unknown combinations remain unknown;
- planned, submitted, observed, and accepted states remain separate.
