# Model-Facing Artifacts and Requirement Transfer

A target receives a particular set of files, controls, settings, and text. It does not receive the entire production history. Preserve the complete directing knowledge internally, then assign every consequential requirement to a real carrier.

## 1. Keep production artifacts distinct

### Director package

Full story, state, camera, blocking, performance, sound, asset, continuity, and acceptance direction.

### Operation card

Actual surface, controls, files, settings, media contribution, prompt responsibility, unsupported requirements, and fallback.

### Exact field contents

Literal text sent to the primary prompt, negative field, dialogue field, edit field, or API key.

### Alternate and post-production plan

Requirements routed to another generation, boundary asset, edit, audio, subtitle, grade, neighboring shot, or accepted variation.

### Run evidence

Exact submissions, all outputs, direct observations, accepted result, finishing record, extracted endpoint, and next changes.

Do not paste the director package wholesale into a target field. Do not reconstruct exact field text later from memory.

## 2. Creative requirement transfer

Before submission, map every consequential requirement:

| Requirement | Why it matters | Strongest carrier | Exact implementation | Review evidence | Fallback |
|---|---|---|---|---|---|

Carriers include:

- submitted character or scene media;
- start or end frame;
- source video;
- primary prompt;
- separate negative, edit, dialogue, or audio field;
- another generation or edit operation;
- post-production;
- neighboring shot;
- explicitly accepted variation.

A requirement is not carried merely because it appears in an internal note.

## 3. Preserve specificity by moving it, not deleting it

Suppose the director package contains this full beat:

```text
C02 raises the cracked pendant across the workbench. C01's eyes follow it before the head turns. C01 keeps the left side guarded, reaches with the right hand, and closes the fingers around the pendant before C02 releases. The metal taps the glove once. The external camera remains on the doorway side, tracks half a step to keep both faces and hands clear, and lands with the pendant in C01 right palm. After the body settles, C01 says the canonical line while the workshop machinery continues underneath.
```

A target may not carry all of that well in one field. A destructive rewrite would reduce it to:

```text
Two characters exchange a pendant cinematically.
```

A proper transfer keeps every function and assigns it to real carriers:

```text
Start or character media:
- current identities, wardrobe, and visible injury concealment;
- workbench geography and doorway-side camera relation.

Primary motion text:
- eyes before head;
- guarded left side;
- right-hand reach;
- receiver closes before giver releases;
- metal contact response;
- half-step camera track;
- final right-palm landing.

Audio or later pass:
- canonical line after the landing;
- continuous workshop bed;
- pendant click synchronized to contact.

Review:
- identity, hand ownership, transfer order, injury concealment, camera side, contact sound, landing, speaker ownership.
```

The exact prompt can be shorter than the director package because media and other passes carry part of the requirement. The production must never become less specific merely because one field is concise.

## 4. Self-contained exact text

Exact target text may omit facts clearly supplied by submitted media. Every textual reference must still resolve to:

- something visible in submitted media;
- a documented target tag or control;
- a noun phrase introduced in the text.

Weak:

```text
Use C01, preserve the approved state, and finish in the canonical landing.
```

Stronger:

```text
The gray wolf mechanic keeps the cracked pendant in the right palm, protects the left side with a guarded shoulder, and lifts the eyes toward the fox across the workbench. The external camera remains on the doorway side and finishes with both characters visible.
```

Internal asset IDs remain in operator-facing sheets and lineage records. Do not paste private IDs into target text unless the target documents that binding syntax.

### Selected guidance at submission time

Resolve target guidance and operation controls before composing the final request.
The production input selection names the exact profile, service data, optional
guidance sources, setting decisions and text spans. The renderer carries these
choices and their source hashes into the existing request seal. It does not add
recommendations after the author has reviewed the text. See
[Target Guidance](target-guidance.md) for the input shape and failure conditions.

## 5. Concise is not generic

A concise prompt can retain:

- initiating cause;
- ordered action;
- physical and material response;
- camera relation;
- performance change;
- contact or prop continuity;
- readable landing.

Remove static description already carried by media and repeated production notes. Do not remove the causal directing knowledge that the selected field must still carry.

## 6. Media contribution record

For every submitted file, state:

```text
file and content hash
actual target control
operator action
visible or audible facts supplied
facts not supplied
prompt consequence
review dimensions
fallback
```

A character reference can support identity and wardrobe while leaving camera, placement, scale, and contact unresolved. A start frame can support opening geometry while leaving later state and landing unresolved.

Reference hygiene follows the intended authority and the selected surface's declared requirements. Choose enough resolution, lighting and views to show the identity features actually needed in the shot; a sharp face or a front/three-quarter portrait is useful only when that subject has those features and the task needs them. Do not impose a face, a single figure, a plain ground, a fixed pixel count or a universal number of views on nonhuman, collective, abstract or deliberately obscured designs. Multiple subjects and contextual composition need explicit reference roles and targets, not accidental global authority. Distinguish appearance evidence from pose, framing and lighting evidence. A reference that already contains the proposed composition can bias the result toward that composition, so verify what the actual target accepts and what the actual output does; text alone is not proof that an unwanted influence was removed. When isolating a technical question, vary a controlled factor; when realizing an expression, coordinated changes may be necessary. Use accepted outputs only within their adopted scope, effective state and visible support. Do not replace the canonical identity anchor automatically with every new result or claim an unseen feature from an unsuitable view.

Composition source and rendering. A still can be made in two steps. A composition surface draws the picture from the sheet's references, and a rendering surface redraws it from that picture as a seed image. The two outputs are two artifacts with two records: the composition source, accepted on its own as the source of the frame, and the rendering, the frame submitted onward. The composition text carries place, action, camera, and each figure's garments and state in prose beside that figure. The rendering text names the style and what the source already shows, and no garment, prop, or fixture that the source does not contain. A still of a recurring character is a character still only when an image carrier reaches the surface: a reference input or a seed image. Without one it is not, whatever seed it was made with, and the gate reports that absence before the run.

## 7. Viewpoint transfer

The generator usually receives concrete camera direction, not the internal viewpoint profile ID. Translate the profile into:

The director package keeps the world's orientations (who faces what, who has their back to whom); the exact text keeps only what the lens sees from the chosen position. The two are written in different words, and the translation from one to the other is a step of its own, done after the camera is placed.

- external or owned camera;
- owner identity when applicable;
- camera position or owner body state;
- focalization;
- point of audition;
- scale, angle, lens, and movement;
- visible limbs and subjects;
- axis, screen direction, and eyeline requirements;
- start and landing anchors.

The internal profile remains useful for validation, continuity, and review.

## 8. The shot-request

A shot-request is production-facing. It may include:

- identity and state hashes;
- shot camera and visibility obligations;
- visible identity details;
- wardrobe, inventory, relationship, and environment projection;
- selected candidate references;
- requested deliverable.

What comes back may include a still prompt, boundary-frame prompt, reference plan, correction payload, or generation package.

Before sending any of it to a target:

1. inspect the generated or selected media;
2. register it in the asset registry;
3. confirm adoption and effective story range;
4. adapt it to the real target operation;
5. preserve exact target field contents separately.

## 9. Explicit deferral

A requirement may be deferred when its route remains concrete.

```text
Requirement: exact line in canonical voice.
Picture pass: stable external reaction close-up with a one-second hold.
Audio path: approved voice generation and lip synchronization after picture acceptance.
Acceptance: the scene remains incomplete until speaker, wording, timing, and mix pass review.
```

Deferral moves a requirement. It does not delete it.

## 10. Result evidence

After a run, preserve:

- exact target surface and operation;
- submitted files and hashes;
- exact field contents;
- settings;
- prompt rewrite returned by the service, if any;
- every output variant;
- direct observations;
- accepted, rejected, or repair decision;
- finishing record;
- extracted accepted endpoint;
- state and asset write-back.

An observation is made at a scale that resolves what it claims. A contact sheet decides which frames to open. It does not support a statement about screen direction, a marking, or a count, because those are gone at that size, and an observation taken from one is recorded as not observed.

A planned result is not run evidence.

## 11. Artifact completion test

A package is ready only when:

- the director package contains the full intent;
- the operation card names real controls and files;
- every critical requirement has a carrier or accepted variation;
- exact field contents are preserved literally;
- target-facing text is self-contained;
- primary and negative fields agree;
- internal IDs are not mistaken for model bindings;
- unsupported details have concrete alternate routes;
- result status is accurate;
- run evidence points to preserved output.

## 12. Character reference sheet, and the order of regeneration

How a reference image is generated belongs to whatever seals the visual-contract-package. This suite owns when it is used.

Order of work:

1. Complete the reference sheet before any line is shot: one character per image, plain background, even
   light, the framings the coverage needs, in the outfit the episode uses. The agent drafts each sheet as an
   `asset` submission with `--purpose sheet-panel` and one subject; it is text only unless an adopted image
   already exists.
2. Register each reference image, and record which of them holds the character's identity role. The author
   adopts one image per character for the role `ID/identity`. The visual block refuses a frame that shows a
   recurring character beside another subject until that character's adopted image is bound to it.
3. Decide each shot's reference allocation before its text is written.
4. On a canonical change, regenerate the sheet from the new identity, then the shots derived from it.

Rules:

- A canonical change is not repaired shot by shot. A shot's two or three reference images are already
  allocated between face, build, clothing, the other character and the room, so changing one shot's selection
  to fix that shot silently removes what another shot relied on.
- Replacing the asset that holds an identity role makes every derived record stale; no stale shot is
  regenerated before the sheet is.
- A shot's reference count is part of its plan. Two characters in one frame divide the same limit, so each
  character is supported by fewer images than a solo frame would give it, and the prompt states what the
  images then cannot. [prompt-composition.md](prompt-composition.md) section 21 gives the text and the
  carriers for such a frame.
