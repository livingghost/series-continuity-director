# Post-Production, Joins, Alternate Paths, and Finishing

Finishing happens before continuity extraction. Accept the picture, repair and conform it, finish joins, grade and mix, then extract the terminal frame and audio tail that seed continuation.

## 1. Boundary types and planning record

Every boundary is one of:

- **continuity join:** story time continues and the boundary should read as one physical progression;
- **scene transition:** time, place, focalization, viewpoint source, or dramatic unit changes deliberately.

Plan the boundary before generation:

```text
boundary ID
boundary type
outgoing shot and accepted endpoint requirement
incoming shot and required opening
bridge type
match point
action phase
state, wardrobe, and prop continuity
picture finishing route
audio bridge
fallback
```

A seam is part of shot design, not a problem discovered only after generation.

## 2. What separately generated clips do not promise

Do not assume that a target replays a supplied anchor frame exactly. Record whether the exact surface reuses pixels, re-synthesizes the boundary, or leaves the behavior unknown. Independent generations commonly introduce several different discontinuities:

- small near-constant shifts in framing, scale, crop, rotation, or lens relation;
- repainted fur, skin, cloth, rain, grain, texture, and local detail;
- changed state or prop geometry even when the broad pose matches;
- restarted ambience, dialogue, effects, or music;
- altered exposure, white balance, saturation, or contrast.

Pixel continuity across independent generations is an editing deliverable. Plan the boundary pose, camera state, action phase, and match point during shot and clip packing. Register against what the viewer last saw in the delivered outgoing clip, not against a planned anchor that the generator may have reinterpreted.

Match exposure, white balance, and saturation before using a dissolve, mask, or texture layer. A geometry match can still expose a cut through grade or surface repaint. A short crossfade may hide a near-still texture change but can ghost fast motion.

## 3. Continuity joins

Preferred order:

1. execute the designed action, eyeline, object, occlusion, sound, or light bridge;
2. use a registered cut when both boundaries nearly match;
3. use a masked cut with a scene-motivated transient;
4. use a short dissolve or optical-flow morph only when motion and style support it;
5. unify grade, texture, and audio bed across the join.

Useful join methods include:

- cut on action;
- eyeline cut;
- object match;
- occlusion cut;
- blink bridge when camera ownership permits it;
- light bridge;
- registered hard cut;
- masked cut;
- short dissolve for elapsed time;
- sound bridge;
- generated transition backed by a real operation.

A crossfade can hide texture repaint in a near-still shot but may ghost fast motion. Inspect the result rather than assuming it works.

## 4. Scene transitions

Use transition grammar intentionally:

- hard cut for direct contrast or continued energy;
- dissolve for elapsed time or gradual relationship;
- fade for chapter boundary, sleep, loss of consciousness, or deliberate closure;
- match cut on shape, action, color, object, or sound;
- sound bridge to connect place or time;
- blink or occlusion when consistent with camera ownership;
- generated transition only with a supported operation and inspected boundaries.

A transition used only to hide a failed continuity join remains a repair, not a story transition.

## 5. Generated transition record

A generated transition is a distinct operation. Record:

```text
bridge type: generated transition
outgoing operand
outgoing endpoint anchor
incoming operand
incoming endpoint anchor
generated bridge output
operation
story duration
generated duration
operation-card or run ID
exact source-to-control mapping
primary and auxiliary field contents
acceptance criteria
fallback edit
```

The operation must accept the required source operands or endpoint controls together. Both boundaries must be inspected and physically compatible. Otherwise preserve the intended bridge in the director package and use a conventional edit, intermediate bridge asset, or redesigned shot.

## 6. Registration and conform

- conform every boundary to delivery dimensions before submission and editing;
- register to delivered frames, not planned anchors;
- compare position, scale, rotation, crop, lens relation, state, and content;
- use a constant transform for constant drift;
- animate correction only when drift changes;
- correct on the side with available framing room;
- prefer safe crop-in over invented borders;
- record every transform.

Independent generations often repaint fur, cloth, texture, grain, and noise even when geometry matches. Match grade first, then use a shared subtle texture layer only when the approved visual language and delivery require it.

## 7. Masked-event calibration

A flash, shadow, steam burst, passing object, screen flicker, spray, or light sweep used to mask a cut must follow the scene's own visual grammar.

Record:

- source;
- location;
- color;
- attack and decay;
- maximum intensity;
- relation to existing events;
- frames covered;
- fallback.

Light the source first and keep spill subordinate. Do not create a mask stronger than the storm, lamp, screen, steam, or passing object it claims to be.

## 8. Picture repair and alternate paths

Possible repairs include:

- crop and reframe;
- stabilization;
- retime;
- freeze or micro-extension;
- identity or state correction;
- contact and prop repair;
- background cleanup;
- paint-out;
- color and exposure match;
- compositing;
- typography and subtitle insertion.

Record source, method, parameters, result, limitations, and rejoin point. Any repair that changes final pixels occurs before terminal-frame extraction.

When a requirement was not completed in picture generation, preserve it in an alternate-path plan:

| Requirement | Why this pass did not carry it | Next operation or post path | Required source and output | Acceptance | Rejoin point |
|---|---|---|---|---|---|

Unsupported does not mean deleted.

## 9. Audio finishing

- maintain room tone or environment bed across ordinary cuts;
- use J-cuts and L-cuts intentionally;
- preserve dialogue, effects, ambience, and music as separate stems when precision matters;
- remove restarts and discontinuities;
- align contact sounds with picture;
- preserve point-of-audition transitions;
- record loudness target and true-peak limit for the actual destination;
- measure the final master.

Common starting points include approximately -14 LUFS integrated for many streaming deliveries, -16 LUFS for some spoken-audio or podcast norms, and -23 LUFS under EBU R128 broadcast practice, with true peak commonly kept at or below -1 dBTP. These are examples, not suite defaults. Verify the actual destination specification before mastering and record the selected target.

Generated audio is candidate material, not automatic authority. Choose, replace, or rebuild it according to the approved plan.

The ambient bed is the mortar between clips. A simultaneously restarting picture and audio boundary usually exposes the cut even when geometry matches.

## 10. Viewpoint-switch finishing

A viewpoint switch may require:

- registered object or eyeline match;
- audio-perspective transition;
- camera-owner breath or device sound entering or leaving;
- external reaction timing;
- state-visibility adjustment;
- motion blur or occlusion at the bridge;
- restoration of shared geography after a subjective insert.

Review whether the switch changes only camera, or also focalization, audition, knowledge, and visible state. Preserve prop ownership, action phase, relationship distance, light, and accepted geometry.

## 11. Terminal-frame and audio-tail extraction

Extract continuation evidence only from the accepted finished master.

Record:

- exact file and content hash;
- timecode or frame number;
- dimensions and aspect;
- camera profile, position, roll, lens relation, and facing;
- visible subjects and state;
- prop ownership and orientation;
- contact and support;
- light and atmosphere;
- dialogue, music, effect, and ambience tail;
- repair and conform history.

The next shot begins from this evidence or from an explicitly created, registered, and inspected corrective derivative.

## 12. Machine-first verification

Before human viewing, verify what tools can measure:

- container integrity;
- duration and frame rate;
- resolution and aspect;
- track presence;
- boundary scale, position, rotation, and content agreement;
- black frames or frozen sections;
- audio levels and clipping;
- subtitle or metadata tracks;
- file hashes;
- expected shot, state, and asset records.

Human review then focuses on motion, acting, audio content, seam belonging, taste, and acceptance. A geometry or level defect that measurement could have found first is a process failure, not normal viewing work.

## 13. Finishing record and completion check

Preserve:

```text
source clips and assets
edit timeline
boundary decisions
registration transforms
masked events
picture repairs
alternate paths and rejoin points
grade and texture
stems and mix
typography and subtitles
measured delivery properties
accepted master
extracted terminal frame and audio tail
```

Completion requires:

- every boundary has a declared type, treatment, and fallback;
- picture conforms to delivery dimensions;
- state, identity, wardrobe, props, contact, and action match across joins;
- viewpoint and audition changes are deliberate;
- audio bed and perspective are continuous or intentionally changed;
- repairs and alternate paths are recorded and reproducible;
- final master passes machine checks;
- terminal evidence comes from the finished master;
- asset registry and production state point to accepted outputs.
