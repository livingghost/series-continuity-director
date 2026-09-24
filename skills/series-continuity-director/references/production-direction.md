# Purpose, portrayal and production choices

**Preparation and reuse:** Full applicable sources govern initial characterization and a changed scope. While preparing a scene, save actual definitions and applications using [Scene Persona](scene-persona.md); during writing or resumption in the reviewed scope, verify complete-source commitments and use that document. The instruction below to read the full Persona applies to preparation rather than repeated scoped execution. Reopen for new participants, topics, knowledge or portrayal intent, even when source hashes are unchanged.

A correct inventory of states is still short of a realized work. For the
requested asset or interval, connect **purpose -> choice -> realization -> actual observation -> repair**
inside the production task and its receipt chain rather than in a parallel
scoring database. `schemas/authoring/production-direction.schema.json` is the
authoring shape, enforced by `scripts/production_direction.py`.

## 1. Authoring a direction

Write a free-form `purpose` and an `intended_effect`, both distinct from an
observed response. `basis` links each applied source ID to its applicability in
this work. Full persona, body/world design, experience, relationships and
authorial intent stay whole in the snapshotted source documents rather than
collapsed into emotion labels or one stock gesture shared by distinct people.
An invented persona or body-part inventory is needed only where the work has
individuals.

A `decision` records:

- question;
- realizable options;
- selected option;
- reason;
- verification criteria.

Set `compare: true` where a material branch requires comparison; otherwise one
considered realization suffices. A generated candidate per option is optional:
compare effects and trade-offs rather than manufacturing a fixed number of shots
or images. Sustaining a condition, holding a frame, exaggerating, repetition,
abstraction or withholding a reveal can all be purposeful; nothing requires an
emotional turn or a smallest permitted gesture. Record coordinated relationships
together when they carry one expression, as one interaction rather than
unrelated one-part changes.

In `authored-rendition`, put each selected option's exact `realization` text into
the authored delivery. In `bounded-context`, the consumer includes only the
selected realization and explicit effect/criteria/limits; the full source
record, alternatives and private author notes travel only by explicit choice.
The implementation verifies transport integrity only; inspect the provider's
declared controls for whether it can realize an instruction.

`departures` records the source, scope, reason and preserved conditions of an
intentional departure, which leaves source and canon as they were.
`action_context`, when useful for an instant, gives the phase, before/after and
free-form relations among participating subjects; contacts, support, occlusion
or ownership can be represented independently of species or anatomy. State in
`verification_limits` what the artifact leaves open: a still image or a pair of
stills, for instance, leaves the feasibility of a movement between them open.

## 2. Observe, interpret, repair

Criteria say what matters and which evidence modality can establish it:

- `any`;
- `image`;
- `video`;
- `audio`;
- `text`.

Inspect the actual files before review. A time-bearing video requirement passes
only on actual video, and an audio requirement only on an actual audio stream,
each in an explicitly cited measured interval. A still, an essay, a whole-file
hash or a byte prefix fails it. A measured duration says nothing about acting,
meaning or synchronization quality.

Reviews cite actual candidates and locators:

- whole artifact;
- descriptive region;
- 1-based inclusive text/byte range;
- normalized still-image region;
- measured half-open media interval in seconds, with its stream.

Each observation states what was seen/heard/read/measured and the method. Each
check links observations, verdict, reason and `evidence_basis`, distinguishing
reviewer interpretation, actual audience report and technical measurement.
Unmeasured or proxy expression stays unresolved rather than passing by
intention. Structural validation leaves a claim of having watched or listened
unauthenticated.

A failed review supplies a repair proposal or an explicit unresolved issue. A
repair points back to decisions and observation indices and states operation,
scope, reason and expected evidence. Let the observed problem choose the repair:

- framing;
- portrayal phase;
- source choice;
- local edit;
- timing;
- production method.

More prompt text or total regeneration is right only when the problem calls for
it. A revised purpose/source/delivery prepares a new run; local authorized
execution under unchanged purpose may add a candidate to the same run, reviewed
anew.

`production_workflow.py impact` reports only actual changed/missing files and
declared dependencies; aesthetic consequences remain an inference. Hashes,
schema admission and completed bookkeeping prove nothing about personality,
attractiveness or effect.

## 3. Repairs, unchanged states and observations

Arc kinds, structure names and expression channels are open authored labels.
A scene may maintain a state or a silence; characters and a story clock are
optional. Check declared identifiers and relationships rather than inventing a
want/need, a turn or a canonical structure the work leaves unused.

A repair records exact `targets` beside its human-readable `scope`, so a new
preparation can be checked against the reviewed proposal; see Production Repair.
A passed video/audio check cites the measured interval that section 2 requires.


## 4. Scoped visual choices

The required `visual_language` field is null for nonvisual production. For images
and video it binds the selected `visual anchor` and `visual register` to existing
decisions, applied source IDs, scopes, actors and observable dimensions. The
linked decision supplies the actual realization, reason and criteria. Preparation
and final-request construction preserve that application in the ordinary consumer
and request seal. See [Visual Language](visual-language.md) section 16 for the
shape, mixed treatments and source-change behavior.
