# Runtime Target Evidence and Operations

The exact generation or editing surface is a runtime dependency. Product names alone do not prove controls, accepted combinations, duration, audio behavior, prompt rewriting, or viewpoint support.

## 1. Evidence priority and freshness

Use, in order:

1. controls visible on the exact surface;
2. current official documentation for that surface and model;
3. inspectable material supplied by the user;
4. preserved exact runs from the same workspace;
5. older notes marked for recheck.

Record date, region, account or tier when relevant, and the operational consequence.

Recheck target facts when:

- product, editor, API, model, account, tier, region, or plan changes;
- current controls contradict stored evidence;
- a package is rejected;
- documentation marks a feature changed or removed;
- the user chooses another surface;
- a required input combination was never directly verified.

Unknown remains unknown.

## 2. Separate fact, decision, and observation

Keep these statement types distinct.

### Surface fact

A control, request key, accepted file type, duration, or option is visible on the exact surface or documented by a current authoritative source.

### Production decision

A choice made because of those facts, such as which files to submit, which operation to use, or which requirement to route to post-production.

### Run observation

A direct result from preserved output, such as identity drift, contact failure, prompt rewriting, or endpoint deviation.

A run symptom can change a scoped tactic. It does not prove a permanent product limit.

## 3. Operation card

```text
Exact surface and model:
Evidence date and source:
Operation selected:
Actual controls or request keys:
Exact file or text placed in each control:
Settings:
What the media visibly or audibly supplies:
What the prompt must still establish:
Requirements routed elsewhere:
Prompt rewriting evidence:
Unknowns:
Run evidence: not run | run ID
```

A label such as `subject reference` is incomplete until the actual control, file, prompt consequence, and review are recorded.

## 4. Supported operation families and required evidence

Package an operation only when the exact surface supports the required inputs and combination.

### Text generation

No submitted image locks the opening. The text must establish visible world, character placement, current state, camera, action, and landing. Record compositional variation as an expected risk.

### Start-image generation

Inspect the exact start image. The first action must follow its visible pose, camera, prop ownership, light, and state. Facts outside the frame remain unsupported unless another carrier supplies them.

### First and last frame generation

Inspect both endpoints. Verify identity, body topology, state, wardrobe, prop ownership, camera relation, light, and physically connectable poses. The prompt describes the path between images and must not create a competing landing.

### Character or subject reference generation

Inspect identity evidence and visible support. Describe scene placement, scale, blocking, contact, and camera elsewhere. Verify that the exact surface accepts the reference media together with other required inputs.

### Video edit or restyle

Inspect source frames across the relevant duration. State what source camera, timing, action, contact, and occlusion remain, and what appearance, environment, or style changes.

### Extension

Inspect the accepted source's final seconds, terminal frame, and audio tail. The continuation begins from the finished rendered state, including pose, camera roll, prop position, and state evidence.

### Composition or transition

Inspect every source and boundary. A generated transition is valid only when the target accepts the required operands or endpoints together and the images can connect physically. Otherwise use an edit, intermediate asset, or redesigned seam.

### Performance transfer

Inspect driver media and character media. Record which source supplies body movement, face, gesture, speech, timing, camera, environment, and appearance. Review the returned result against both sources.

### Dialogue, audio, and lip synchronization

A surface that produces audio does not guarantee exact wording, correct speaker, canonical voice, timing, or mix. Record the selected route for every important line and sound.

### Post-production

Use editing, compositing, dialogue, sound, grade, subtitles, repair, or seam finishing when one generation operation cannot carry the complete requirement set.

## 5. Asset type, operation, and intended influence

Asset bookkeeping and model operation answer different questions.

```text
C: character identity media
S: scene, layout, composite, start, end, or continuation frame
P: recurring prop media
V: source or accepted video
A: audio or performance media
```

For every actual use, record:

```text
immutable asset ID and content hash
actual file
actual target control or request key
operator action
what visible or audible evidence it supplies
what text must still establish
review dimensions
fallback
```

Intended influence is a production hypothesis, not a contract the model has accepted. A character portrait may supply face, markings, and wardrobe, but it does not establish room placement, camera height, scale against furniture, or hand contact unless the submitted operation visibly carries those facts.

Where the text and a reference disagree about the same fact, the text wins. That makes paraphrase
dangerous in exactly the places it feels harmless: a garment described from memory rather than copied
from the approved record replaces the correct garment the reference was carrying, and it does so
silently, in every take, because the reference is still visibly doing its job on everything else.
Approved appearance is either quoted verbatim into the prompt or left out of it entirely.

A reference submitted without a stated job supplies everything it happens to contain. Its background, palette, lighting, and framing arrive along with the identity that was wanted. So the text states two things per reference: what it supplies, and what it must not control. The second half is the one that is usually missing.

A reference's resolution is not the number in its filename; what matters is how many pixels sit on the
feature that has to survive. A full-length figure spends nearly all of its resolution on the body, so a
face inside it may be a fraction of the frame even in a large file, and downscaling for convenience of
transport can quietly destroy the only evidence of who the character is. When a likeness has to hold
across a scene, the reference set carries a close panel of the face in addition to the full figure, and
any transport-driven downscaling is measured against the face rather than against the file.

More references do not mean more control. Past the count a surface is built for, each additional reference dilutes the features that mattered, so drop the ones whose job is already covered rather than adding one more in the hope that the model will average correctly.

## 6. Input-combination proof

Do not infer combined support from separate feature pages. Verify or leave unknown combinations such as:

```text
start image + character references
start image + end image + character references
multiple character references + scene reference
source video + character reference + audio driver
source video + first and last keyframes
native audio + separate negative field
prompt rewriting + exact text preservation
```

When a combination is unavailable or unverified, choose a concrete alternate route:

- composite identity and scene into a start frame;
- create a state-correct identity derivative of the accepted endpoint;
- split identity, motion, dialogue, or effects into separate passes;
- use edit or restyle;
- reduce the shot to the evidence the operation can carry;
- select another target;
- explicitly accept the remaining variation.

Do not mark the feature unavailable and continue with the same impossible package.

## 7. Binding syntax

A target binding is real only when the current surface exposes it:

- file placed in a named image control;
- source video selected for an edit operation;
- character image assigned to a visible subject slot;
- media URI placed in a documented request key;
- documented target tag produced by the interface.

Internal IDs such as `C01`, `SC12-SH03`, or a state hash remain in operator records. Remove them from exact model text unless the target documents that syntax. Rewrite them into self-contained visual relations.

Media transport is part of the binding. A control that names a file by identifier and a control that carries the file's bytes cost very different amounts to use, and the difference decides how freely a shot can be retried. When a surface can store media once and return a durable identifier, upload the reference set first and cite the identifiers in every later submission; a retry then costs nothing extra. Re-sending the bytes per attempt makes each retry expensive enough to distort the direction, which is the wrong reason to settle for a take. Record the identifier next to the asset ID and content hash, so the operator record still says which file the identifier stands for.

## 8. Reusable target profile

Surface facts researched for one project are worth keeping. A target profile is the durable half of the evidence: what the surface accepts and how it wants to be addressed, separate from what any one project decided to send it.

Profiles live in the suite as data, one file per exact model under `protocols/target/profiles/`, validated by
[`scripts/target_protocol.py`](../scripts/target_protocol.py) against
[the target-profile schema](../protocols/target/schemas/target-profile.schema.json). Read the profile for the selected
model before writing a director package or an exact submission; write project decisions into the project's
production state, not into the profile. A project keeps profiles of its own, such as the one `observe_schema.py`
writes, in a directory such as `target-profiles/`, which `--profiles` reads before the suite's. A profile carries:

```text
the model as its maker names it, and the evidence date
prompt structure the surface documents
camera control: named command vocabulary, or free description, and whether one move per shot is the limit
multi-shot control: whether timestamp ranges are honoured, their format, and the per-shot minimum
duration behaviour: supported range, and the shot budget per duration band
audio control: how sound and dialogue are addressed
aspect and resolution control: which parameter actually sets it
input modes and what each mode expects the text to describe
documented anti-patterns
```

Three parts of this deserve attention because a suite that ignores them plans the wrong artifacts.

**A named camera vocabulary changes the plan, not just the wording.** When a surface documents specific camera commands, those commands are the available moves; a described move outside that set is a request the surface may or may not honour. Shot planning that assumes an arbitrary camera path will silently degrade to whatever the vocabulary can express, so check the vocabulary before promising a move in the director package.

**Documented multi-shot control changes clip packing.** A surface that honours timestamp ranges can carry several shots inside one clip, which turns some seam problems into internal cuts and removes generations from the plan. A surface without it needs one generation per shot and a real edit boundary between them. The clip-packing rules above still apply inside a multi-shot clip: each internal cut declares its function, and the per-shot minimum from the profile is a hard floor, not a target.

**A documented prompt structure is a contract about what the text must carry.** When the surface names its layers, missing a layer does not produce a neutral result; it produces a default the surface invents. Unspecified audio is the common case: it generates arbitrary ambience rather than silence.

A profile states what the surface does, not how that was learned. Where documentation and behaviour disagree, the profile states the behaviour, and the date on the profile and on each offering says when that was last checked.

## 9. Clip packing

Every video surface holds identity, objects, and motion less well the longer the clip runs; the visible failures (extra fingers, shifting text, mismatched reflections, faces over long takes) are consistency failures across time rather than rendering failures in a frame. Plan in short clips of a few seconds each, one beat per clip, and join them on accepted endpoints.

Duration arithmetic does not prove shot feasibility. First verify:

- start and end can each be shown as one frame;
- the dominant visible change is one causal progression;
- camera and subjects can perform the path;
- contact has ownership, occlusion, feedback, and landing;
- the endpoint can seed continuation.

Then choose supported durations by preferring:

1. minimum overrun;
2. fewest clips;
3. useful slack near a hold, reaction, or seam;
4. boundaries at causal, camera, or story-function transitions.

Duration controls do not prove timestamp obedience. Use ordered causal language unless the surface documentation and preserved runs support precise time ranges.

Spare generated time is an intentional hold, reaction, material settling interval, dialogue window, seam allowance, or ambience tail. Record both the story duration and the selected generated duration. Do not hide overrun by claiming the generated clip is shorter than the verified control, and do not fill spare time with another independent event merely because seconds remain.

A clip is a delivery unit, not automatically one shot. If a clip contains internal cuts, declare them and explain the function of each cut. If continuity requires a real endpoint before the next clip can be finalized, render sequentially.

Past a surface's short band, a clip described as one continuous sentence drifts: the character changes, the camera wanders, and the ending does not follow from the beginning. A clip long enough to hold more than one moment is written as ordered beats, each naming what is on screen, what the camera does, and what is heard. Sound belongs inside the beat that carries it rather than gathered at the end, where it attaches to nothing in particular.

Duration is a directing choice, not a default. Generating the maximum length for every shot flattens the rhythm of a sequence and buys time the shot has no use for. Choose each shot's length from what it must show, and use the differences between those lengths as pacing.

## 10. Viewpoint and target operations

A viewpoint profile is an internal directing grammar. The target usually receives concrete camera and media instructions instead of the profile ID.

For each shot, translate:

```text
camera ownership
camera position or owner body state
focalization
point of audition
shot scale and lens
movement path
visible characters and body regions
screen direction and axis
start and landing anchors
```

When switching viewpoint, verify that the selected operation or edit can carry the bridge. A start image may establish the first viewpoint but not a later external reaction. A multi-shot sequence may require separate clips, source edit, or conventional editing.

## 11. Rejection diagnosis

Treat submission rejection as surface-specific evidence.

1. Preserve target, operation, files, exact text, settings, date, and error.
2. Keep required media and minimum valid structure fixed.
3. Change one editable element at a time or bisect text.
4. Test the smallest reproducible token, phrase, field, or combination.
5. Preserve successful and rejected versions of the submission.
6. Scope the finding to the exact surface and date.
7. Rewrite with the shortest concrete language that preserves the intended visible result.

Do not create a universal forbidden-word list from one rejection.

## 12. Operational packaging gate

A package is ready when:

- the exact target and operation are identified;
- current evidence supports every required input and combination;
- every submitted file exists, opens, and has been inspected;
- each file maps to a real control or request key;
- exact primary and auxiliary text is preserved literally;
- media contribution and prompt responsibility are stated separately;
- boundary media matches delivery dimensions;
- the shot's opening and first action are compatible;
- state, identity, props, camera, contact, and endpoint have carriers;
- unsupported requirements have concrete alternate routes;
- result status remains `not run` until actual output exists.

## 13. Services, models, and offerings

Three records, because three things change at different times.

- A **service record** says how a service is called: endpoint, authentication shape, request envelope, operations, asynchronous delivery and polling, error shape, limits. It lives once, in the `service-profiles` pack resource, and is read from there rather than transcribed (`scripts/service_profile.py`). The record carries one `observed_at` and one `source`: it is refreshed as a whole from the service's documentation, not fact by fact. The operator adds `http_timeout_seconds`, the seconds each network wait may take; it is an operator budget rather than a documented service fact.
- A **model profile** (`protocols/target/profiles/`) says how a model behaves: prompt contract, camera vocabulary, the meaning of each input mode and which modes exclude each other, anti-patterns, observations. Nothing in it names an endpoint or a service's identifier for the model.
- An **offering** inside the model profile says how that model is exposed on one service. It records the service's identifier for the model, the request keys each input mode occupies, and the request shape: where the model identifier, the text and each media reference go. It also records the limits the service enforces for the model (a duration band, a reference count, a geometry rule), with its own `observed_at` and evidence. The same model on another service is a second offering in the same profile, and a submission names the service it will use when the profile lists more than one.

What to update when something changes: a service's endpoint, envelope, or polling behaviour changes the service record; a discovery about how a model reads text or references changes the model profile; a limit a service enforces on a model changes that offering. A new service is one entry in the service record, an offering on every profile it exposes, and a transport: the record's `"transport": "<name>"` selects `scripts/transport_<name>.py`, which implements `scripts/transport_contract.py`, and several records may share one; a model already profiled that a recorded service also exposes is one more offering. A record that fails at the service is refreshed from the documentation and its date updated. Scripts that send read the service record and the offering rather than carrying endpoints, identifiers, or limits of their own, and print the record's observation date beside what they send.

The gate checks a submission's stated `parameters` against the offering's constraints (the duration band first) and reports a video submission that states no duration as unmeasured.

An offering whose service rewrites the text unless told not to declares `as_written`: the request keys and values under which the text reaches the model as sent. The input plan explicitly selects each such setting before request construction; the transport supplies none of them implicitly. The gate reports a choice that enables rewriting. The final request carries the selected value and its reason; see [Target Guidance](target-guidance.md).

An offering may point at an **observed parameter schema**: the service's acquired schema for its exact model. The gate validates declared inputs and parameters against those constraints. A submission that names no service is checked against the model alone, and the gate reports every service-level check as unmeasured. Local evidence catalogs retain original responses, source identities, and separate envelope overlays. Use the [model evidence workflow](model-evidence.md) to import schemas, record reference sources, or attach an existing authorized trial. Each request states its validation mode and unmeasured conditions.
