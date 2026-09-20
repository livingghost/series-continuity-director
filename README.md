# Series Continuity Director

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

Series Continuity Director plans and produces a continuing work while keeping four things straight: what is true in the story, what each participant knows, how a scene is presented, and which results the author accepted. It serves screen work, comics and prose alike: a scene is realized as shots, as pages of panels, or as passages.

It is an Agent Skill: instructions the agent follows, plus local Python tools the agent runs. The author and the agent make the narrative and expressive decisions. The tools check declared relationships, rebuild recorded state, prepare exact submissions and keep the production evidence. The skill is self-contained, with its own definitions, templates, scripts and public contracts, and it takes any generation model, any cast size and any narrative shape: a held condition, a deliberate ambiguity, a repeated action or an empty room can be the point of a scene.

## Who this project is for

Use it when a work spans more than one scene, chapter, page, shot or clip and you need the next piece to continue from what was actually accepted. The hard part is rarely remembering names and outfits. A character's knowledge changes, an event belongs to a particular story time, the camera knows less than the author, and a generated result may differ from what the plan asked for. The project keeps those distinctions written down so nothing continues from an unverified assumption.

A writer can plan scenes and draft prose with it and never generate media. A comics creator carries character state and viewpoint into page and panel decisions. A screen production connects the same scene intent to blocking, performance, camera, sound and real clip boundaries. Public contracts let selected artifacts travel to other tools without exposing this project's internal layout.

## Core production chain

```text
brief, plus the project's approved narrative, Persona and world
  -> scene purpose, story-time state and telling constraints
  -> full source reading and reusable scene Persona material
  -> shots for screen, pages and panels for comics, passages for prose
  -> visual, performance, viewpoint and continuity decisions
  -> inspection of the actual media the operation depends on
  -> director package, adapted to the real production target
  -> exact files, controls, settings and field contents
  -> approved execution and every returned variant
  -> review, repair, acceptance and scoped continuity write-back
```

**Start with what the scene is doing.** Read the narrative, the world and the complete character definitions before deciding how to depict the scene. Resolve the recorded state at the chosen story time, separate what each participant knows from what the author knows, and name the conditions the scene must hold. A scene may preserve a situation rather than change it, with any number of shots, speakers or turns.

**Carry that understanding into the medium.** A scene plot connects to passages, pages or shots before any prompt exists. During preparation the agent saves the Persona definitions the scene needs and how they apply, so drafting, performance direction and revision reuse the same reasoning. Camera position, whose knowledge the telling follows, where sound is heard from, and what information is disclosed are four separate choices, decided by the scene's intended effect.

**Base concrete direction on real inputs.** When an operation depends on an existing image, endpoint, clip or audio, inspect it before finalizing spatial or temporal instructions. The director package records the complete intention; target adaptation then places each requirement in a real field, attached image, boundary frame, performance cue, sound operation or finishing pass. A field limit on the target sends a requirement to another carrier or to explicit acceptance, never to silence.

**Review what came back and continue from what was accepted.** Submit through a prepared run with the required approval, keep every returned variant, and review the actual media. Observations, interpretations and proposed repairs are recorded apart. A chosen image or clip changes the world only through its own scoped decisions: selection, reference adoption and canonical state each have one. The next clip continues from the accepted endpoint, screen direction, contact and sound tail; the next passage continues from established knowledge and events.

## Installation

Use Python 3.11 or later. Project authoring, state and the public-contract readers use only the standard library. Media inspection needs Pillow; playable roughs and audio or video probing need `ffmpeg` and `ffprobe` on the executable search path.

The extracted archive is a plugin repository. A plugin-capable host receives the repository with its host metadata. A host that loads individual skills receives the complete [skill directory](skills/series-continuity-director/), whose entry point is [SKILL.md](skills/series-continuity-director/SKILL.md), with its scripts, assets and schemas. The [flat text adapter](skills/series-continuity-director/adapters/series-continuity-director-flat.md) gives a text-only host the instructions in one file; that host still needs Python, media tools and storage of its own to run anything.

All commands below run from the repository root, the folder containing this README, with the interpreter the host will use.

### Dependency checks

<!-- readme-example: core-check -->
```sh
python skills/series-continuity-director/scripts/dependencies.py --scope core
```
<!-- end-readme-example -->

For media work, install the [media requirements](skills/series-continuity-director/requirements-media.txt) and the two executables, then check the media scope:

```sh
python -m pip install -r skills/series-continuity-director/requirements-media.txt
python skills/series-continuity-director/scripts/dependencies.py --scope media
```

The check names missing tools. Keep authored projects and generated files outside the installed repository. Initializing a project, writing a scene and running the core examples need no service account.

### Your first project

The following creates a prose project in a new sibling directory; use `--medium screen` or `--medium comics` for the other media. It creates the structure, and the author supplies the cast and the plot.

<!-- readme-example: project-start -->
```sh
python skills/series-continuity-director/scripts/init_project.py --out ../scd-first-project --series-id SERIES-01 --title "Untitled project" --medium prose
python skills/series-continuity-director/scripts/validate_project.py ../scd-first-project
python skills/series-continuity-director/scripts/narrative_coverage.py ../scd-first-project
python skills/series-continuity-director/scripts/session_entry_points.py --project ../scd-first-project --next
```
<!-- end-readme-example -->

The new directory holds the readable series, character, asset and production records beside the narrative, state and media directories:

```text
series-state.md  character-profiles.md  asset-registry.md  production-state.md
narrative/   narrative.json, design/, personas/ (c01.md, persona-template.md), world/, glossary/, scenes/
state/       events.jsonl
production/  production-task.json, production-review.json, production-selection.json
runs/        gallery.html, gallery.json
media/  shots/  work/
```

Coverage starts honest: `narrative_coverage` reports zero chapters and one gap, "the narrative is not approved", until the author declares and approves the narrative. A first request to the installed skill can be:

> Use this project and its source definitions to prepare the next scene. Preserve the stated world, character and knowledge constraints. Explain unresolved choices, save the material needed to write it, and do not send anything to an external service.

The agent establishes the story position and the scene's purpose, reads the full source definitions, resolves recorded state, and chooses a realization for the medium: a passage, a page of panels, or the camera, action and sound the scene needs.

## Planning and continuity

How a scene is understood before anything is produced: the story above the scene, Persona preparation, viewpoint, temporal state, morphology, visual contracts and the language of direction.

### The story above the scene

[narrative.json](skills/series-continuity-director/assets/project-templates/narrative/narrative.json) holds what the series is about: the themes, the arcs that carry them, the chapters that depict them with the story orders each covers, the characters with the persona in force, and the promises, questions and knowledge the series is carrying. Every scene plot names the chapter and arcs it advances, and coverage reports what the series declares that no scene covers yet. A scene plot records purpose, context, viewpoint and intended persistence or change:

```json
{
  "artifact_type": "scene-plot",
  "scene_id": "submission-gate-fixture",
  "chapter": "ch1",
  "arcs": ["a1", "a2"],
  "characters": ["C01"],
  "focalization": {"kind": "external"},
  "setting": {
    "interior_exterior": "interior",
    "location": "gate-fixture-boathouse",
    "time_of_day": "first light, before either of them has spoken"
  },
  "scene_function": "entry",
  "proposition": "From a shared boathouse before either of them speaks, one of them lights a second lantern, leaving the morning admitted rather than said."
}
```

Arc types, scene functions and delivery roles are authored text, and a project without a story clock needs no fictional timeline. [Story Structure](skills/series-continuity-director/references/story-structure.md) and [Narrative authoring](skills/series-continuity-director/references/narrative-authoring.md) describe the records and the commands that create them.

### Preserve Persona understanding in each scene

The [Persona form](skills/series-continuity-director/assets/project-templates/narrative/personas/persona-template.md) describes one character in one phase of their life, in twenty sections, with what is attested kept apart from what is inferred. Even an ordinary exchange can depend on attention, memory, values, body, voice, knowledge and partner-specific exceptions spread across it, so scene preparation reads the complete applicable originals and records the exact passages the scene needs, their conditions and dependencies, and how they apply here. The resulting `persona.md` is a working document that keeps definition, current condition, interpretation, optional performance and uncertainty distinct.

Try the data flow in an empty sibling directory. The example's tiny subject model demonstrates processing, not a real Persona:

<!-- readme-example: authoring-material -->
```sh
python skills/series-continuity-director/scripts/create_authoring_example.py --root ../scd-authoring-demo
python skills/series-continuity-director/scripts/scene_persona.py verify --root ../scd-authoring-demo --plan scene-plan.json --bundle scene-material --require-ready
python skills/series-continuity-director/scripts/source_material.py verify --root ../scd-authoring-demo --bundle source-material
```
<!-- end-readme-example -->

`scene-material/persona.md` carries the definitions themselves, each tied to its source, lines and whole-file hash, followed by their application in the scene; `material.json` binds the document to the source files and excerpt choices. For real work, author a plan against the [scene-material plan schema](skills/series-continuity-director/schemas/authoring/scene-persona-plan.schema.json), then:

```sh
python skills/series-continuity-director/scripts/scene_persona.py inspect --root PROJECT --plan scene-plan.json
python skills/series-continuity-director/scripts/scene_persona.py build --root PROJECT --plan scene-plan.json --out scene-material
python skills/series-continuity-director/scripts/scene_persona.py verify --root PROJECT --plan scene-plan.json --bundle scene-material --require-ready
```

In the production task, select the `scene-persona` feature and list the material:

```json
"scene_materials": [
  {"plan": "scene-plan.json", "bundle": "scene-material"}
]
```

Preparation verifies the sources and carries the document into the consumer input, the exact input handed to the writer or generator. Later writing, performance direction, local repair and resumption reuse it within its reviewed scope. Any change to a complete source, quoted or not, invalidates reuse; a new participant, topic, relationship or portrayal aim can call for fresh preparation even when no file changed. When a gap appears, return to the originals. [Scene Persona Material](skills/series-continuity-director/references/scene-persona.md) gives the review and replacement rules.

### Viewpoint

A scene owns a default viewpoint, and a shot overrides it when the new view does a distinct job: geography, action, reaction, contact, reveal, emotional alignment or a bridge. Seven profiles ship: external character-aligned third person, external objective third person, external omniscient third person, over-the-shoulder, embodied first person, held-device first person, and fixed diegetic observer. A viewpoint record keeps these apart:

```text
camera ownership
knowledge scope
point of audition (where the sound is heard from)
focal character
camera position and movement
shot scale, lens and angle
axis side and screen direction
eyeline and subject visibility
start and landing anchors
knowledge visibility
```

A camera change leaves character state as it was; a state change needs its own story event. The profile definitions and camera contracts live under the [Series Viewpoint Protocol](skills/series-continuity-director/protocols/viewpoint/README.md); the editorial rules are in [Viewpoint Profiles](skills/series-continuity-director/references/viewpoint-profiles.md), [Third-Person Camera](skills/series-continuity-director/references/third-person-camera.md), [First-Person Camera](skills/series-continuity-director/references/first-person-camera.md), [Blocking and Coverage](skills/series-continuity-director/references/blocking-and-coverage.md), [Viewpoint Transitions](skills/series-continuity-director/references/viewpoint-transitions.md) and [Shot Continuity](skills/series-continuity-director/references/shot-continuity.md).

### Temporal state and canon

Canon is the set of story facts the author has accepted. The [Shared State Protocol](skills/series-continuity-director/protocols/shared-state/README.md) keeps five layers apart: species and individual morphology, stable identity, canonical story-time state, the projection visible in one shot, and the state observed in a render. Approved variable state is recorded as events in story order, and snapshots and projections are rebuilt from those events. The system represents:

- injuries, healing, scars and fatigue;
- era, form, transformation and appearance variants;
- felt emotion, expressed emotion, social masking and physiological cues;
- directional relationship state, authority, trust, conflict, intimacy and contact boundaries;
- season, weather, light, culture and locale rules;
- wardrobe layers, carried clothing, damage and repair;
- ownership, possession, equipment, loss and atomic prop transfer;
- offscreen events, delayed disclosure, flashbacks, time jumps and alternate timelines;
- character-specific state machines such as transformation, overheat, curse progression or armor mode.

Returned media enters canon only through a story event the author accepts.

### Species, individual and shot morphology

A recurring subject is defined by three records rather than a species noun:

- a Species Morphology Profile for body topology, features, counts, attachments, meaningful absences, surfaces, capabilities and expression channels;
- an Individual Morphology Contract for exact proportions, feature instances, markings, asymmetries, scars, repairs, grooming, tools, personal expression behavior and approved variation;
- a resolved morphology projection for what must be visible, hidden or continued outside the crop in one shot.

This covers real species, ordinary animals, anthropomorphic animals, fictional creatures, hybrids, robots, androids and unfamiliar body plans. A change in feature count or attachment topology needs an approved morphology lineage. [Morphology and Species Contracts](skills/series-continuity-director/references/morphology-and-species-contracts.md) has the authoring rules.

### Visual contracts and shot requests

[Visual contracts](skills/series-continuity-director/references/visual-contracts.md) bind the chosen identity, morphology and state to the evidence a shot needs. A shot request names, per character, the hashes of the species profile, individual morphology, identity contract and state snapshot, plus the scene context, the viewpoint profile and camera specification, the visible feature references and obligations, the wardrobe, inventory, relationship and environment projections, the selected references and the requested deliverable. One from the worked example, trimmed:

```json
{
  "artifact_type": "shot-request",
  "request_id": "REQ-SC-WORKSHOP-01-SH01",
  "scene_id": "SC-WORKSHOP-01",
  "shot_id": "SC-WORKSHOP-01-SH01",
  "deliverable": "boundary-frame",
  "species_profile_sha256_by_character": {"C01": "4dc89f20...", "C02": "ac85f8b1..."},
  "individual_morphology_sha256_by_character": {"C01": "e4371266...", "C02": "e2588fc7..."},
  "viewpoint_profile_id": "external-character-aligned-third-person"
}
```

Changing the camera changes the visible obligations and the reference selection, and leaves stable identity untouched.

### Shot continuity and finishing

Third-person coverage adds the continuity work of a cut:

- the axis of action and deliberate crossings;
- screen direction and entrance or exit direction;
- eyeline height and target;
- matching action and prop ownership;
- body, wardrobe and environment state across cuts;
- camera path and landing composition;
- sound bed, dialogue route and audio tail;
- the join type, registration, mask, grade and repair strategy.

The suite plans these before generation and verifies the finished boundary before it becomes the next anchor. See [Shot Continuity](skills/series-continuity-director/references/shot-continuity.md) and [Post-Production](skills/series-continuity-director/references/post-production.md).

### Direction wording, dialogue and audio

Visual direction uses observable geometry, timing, contact, source and response. The [Scoped Lexicon](skills/series-continuity-director/references/scoped-lexicon.md) separates visual prose, sound wording, quality terms, simile handling, positive construction and target-specific negative syntax, so a word valid for sound or an approved style stays out of the global visual instruction. A proposed shot text from the worked example:

```text
External character-aligned third-person wide master from the frame-left workshop
doorway. C01, a tall gray wolf mechanic in a dark blue work jacket, enters from the
left and stops at the near edge of the central workbench while subtly protecting
the concealed left-side injury. C02, a russet fox archivist in a cream vest and
round brass spectacles, stands beyond the workbench holding the damaged silver
pendant P01 low in the right hand. Cool rain window light remains frame-left, warm
work lamps remain frame-right, and both full-body silhouettes, the workbench, and
the established screen direction stay readable.
```

Conversation language, package language, submitted field language, each character's dialogue language and subtitle tracks are independent choices. Subtitles default to off and travel as a sidecar or metadata track unless the author wants generated on-screen text and the target documents that route. Exact dialogue stays attached to its speaker, language, voice direction, performance window and production path even when picture and speech are generated separately, and the ambient bed, action triggers, material responses, dialogue, music and seam tail are routed apart so each can be generated, replaced, mixed and reviewed. [Dialogue and Audio](skills/series-continuity-director/references/dialogue-and-audio.md) has the diagnostics, point-of-audition rules, narration devices, music routes and localization checks.

## Production

The evidence stages of a run, how reference media reach a target, how every requirement finds a carrier, and how an approved submission is prepared, sent and finished.

### Production evidence stages

Stage names are navigation. What separates them is which evidence exists and what it is enough to finish.

**Stage A, plan.** Use it while required media, state or target evidence is missing. Resolve the story time, the approved morphology, identity, form and state. Define the scene purpose, visible cast, dominant change and required landing. Choose the default viewpoint and only the shots with distinct jobs. Establish axis, screen direction, eyelines, contact, prop ownership and state visibility. Write briefs for the character, scene, prop, start, end, boundary or reference media that are missing, and shot requests where needs differ per shot. Stop before claiming any inspection of media that does not exist yet.

**Stage B, inspect and prepare.** Use it once the files and the target operation can be inspected. Register each file and its lineage. Inspect the actual composition, identity, camera, state, contact, light and occlusion. Revise blocking where the real opening conflicts with the plan. Write the full director package and causal shot direction, map every file and text artifact to a real control or request key, keep the exact field contents apart from production notes, and record unsupported requirements with their alternate route. End with a submission-ready package.

**Stage C, observe and continue.** Use it only after output exists. Preserve every returned variant with the exact submission. Run the machine checks before subjective viewing. Record visible and audible symptoms as observed. Compare identity, state, camera, action, contact, props, performance, sound and landing with the director package. Finish the accepted picture and sound, extract the terminal frame, write approved story events, asset lineage, observations and scoped tactics back into project state, and continue from the accepted endpoint.

### Reference media and their actual use

A file's type, its use on a target surface and its intended influence are three decisions. The Asset Registry classifies material as `C` character identity or performance media, `S` scene, layout, start, end, composite, mask or boundary media, `P` prop identity media, `V` video, motion, performance or edit source, and `A` dialogue, voice, ambience, effect, music or performance audio. Each adopted asset carries an immutable project ID, a content hash, a derivation record, an effective story range and its actual uses per run; new derivatives leave the assets behind accepted episodes in place.

The operation record names the exact control, the exact file and the operator action:

```text
C01-REFERENCE -> uploaded to the documented subject-reference control
S14-OPENING   -> uploaded to the start-image control
S15-LANDING   -> uploaded to the end-image control
V08-SOURCE    -> selected as the source operand for an edit operation
S03-LAYOUT    -> inspected by the director only and not submitted
```

The same video can be guidance in one run and an edit operand in another, with the prompt, criteria and continuity expectations changing to match.

### Deliver every critical requirement

Before a shot package is complete, every critical requirement is assigned a carrier:

- submitted media: a start image, end image, character or scene reference, source video, mask or keyframe;
- an actual target field: the primary prompt, a documented negative field, or a dialogue, audio, motion or edit instruction;
- another operation: a second generation, restyle, extension, performance transfer, repair or composite pass;
- post-production: dialogue, sound, music, subtitles, typography, grade, seam repair or cleanup;
- a neighboring shot that carries the requirement more clearly;
- an accepted variation the author agrees to leave open.

The transfer table of the worked example's director package:

```text
| Requirement      | Carrier                                              | Review                              |
| Stable identity  | shared identity contracts, angle-matched references  | face, markings, ears, spectacles    |
| Concealed injury | state snapshot plus performance projection           | guarded posture, no visible bandage |
| P01 ownership    | shot specs, transition VT-WORKSHOP-03, handoff text  | hand sequence and final owner       |
| Camera geography | viewpoint plan and continuity ledger                 | axis, screen direction, eyelines    |
| Lighting         | scene context and every shot prompt                  | cool left window, warm right lamps  |
```

The suite directs documented operations including fresh generation, image-to-video, start and end frame generation, subject-reference generation, edit, restyle, extension, composition, transition, performance transfer, lip sync and conventional post-production; [Operational Distinctions](skills/series-continuity-director/references/operational-distinctions.md) shows how they differ. A combination of controls is used once the selected surface documents or visibly exposes it, and the project records the evidence date, surface, consequence, open facts and recheck trigger: see [Runtime Capabilities](skills/series-continuity-director/references/runtime-capabilities.md), [Model-Facing Artifacts](skills/series-continuity-director/references/model-facing-artifacts.md) and [Target Adaptation](skills/series-continuity-director/references/target-adaptation.md).

### Target capabilities and their evidence

The installed suite carries directing method, artifact contracts, templates, examples and validators. Facts about a vendor, model, account tier, editor or API live in the project's Production State, dated:

- the exact product, surface, model and account context;
- the controls observed or documented;
- accepted media types, counts, combinations, durations, aspects and settings;
- prompt rewriting, dialogue, audio, subtitle and exclusion behavior;
- output retrieval and post-production routes;
- what remains unknown, with its recheck condition.

A run symptom can justify a scoped tactic for that surface, and a documented input shows that the surface accepts it.

### Prepare a production run

A director package explains the scene and the chosen realization; a target submission contains the actual text, files, controls and settings one tool will receive. The production workflow records the chain:

```text
source definitions and applicable state
  -> scene plot, prepared Persona material and realization choices
  -> prepared production input and review criteria
  -> approved handoff and exact submission
  -> captured variants, located observations and scoped repair
  -> approved selection, optional adoption and completion
```

Inspect an executable offline text example in a new sibling directory:

<!-- readme-example: production-lifecycle -->
```sh
python skills/series-continuity-director/examples/production-execution/run_example.py --out ../scd-production-demo
```
<!-- end-readme-example -->

The run leaves hash-linked records, one per event:

```text
handoff -> candidate -> review -> authorization -> reservation -> selection -> completion
```

A review record cites what was observed and where, and ties each verdict to its criterion:

```json
{
  "event": "review",
  "data": {
    "candidate": "36091ce7f33d667434c8e3805301e05394fc4d882296f0f2cdb57ac13a8ac207",
    "review": {
      "checks": [
        {"criterion": "world", "evidence_basis": "technical-measurement",
         "observation_indices": [0], "verdict": "pass"}
      ],
      "observations": [
        {"locator": {"kind": "lines", "start": 1, "end": 1}, "method": "text-inspection"}
      ],
      "conclusion": "Synthetic positive fixture, not user approval."
    }
  }
}
```

The example's approvals are labeled synthetic fixtures; real work uses your own. [Production Execution](skills/series-continuity-director/references/production-execution.md) explains task preparation, handoff, capture, review and completion; [Production Direction](skills/series-continuity-director/references/production-direction.md) covers the authored choices that feed it.

### Approve an external generation

A dispatch needs the selected service's configuration, its credentials and current target evidence. The bundled transport is Runware; other tools are reached through an explicit external handoff that keeps the same input and result records. The submission gate checks the declared settings, media and requirements and reports both errors and what it cannot measure; "admitted" means no checked refusal was found. A dry run:

```sh
python skills/series-continuity-director/scripts/dispatch.py PROJECT/submission.json --root PROJECT --service-profiles PROJECT/service-profiles.json
```

For a live send, prepare the production run, record approval for its exact submission, and pass the receipt (the recorded approval), the actor, the output count and the cost bound:

<!-- readme-send: generation -->
```sh
python skills/series-continuity-director/scripts/dispatch.py PROJECT/submission.json --root PROJECT --service-profiles PROJECT/service-profiles.json --production-run RUN_ID --authorization RECEIPT_SHA --actor ACTOR --outputs 1 --cost-bound COST_BOUND --currency CURRENCY --send
```
<!-- end-readme-send -->

Use the real count, bound and currency. A changed input needs its own approval, an interrupted or unknown outcome is investigated from the saved run before another send, and selecting one variant among the captured ones leaves its incidental details out of canon. A target operation normally produces an operator package:

```text
shot-package/
  director-package.md
  submission-sheet.md
  submitted-text.txt
  negative-prompt.txt          only when the target exposes a separate field
  request-body.template.json   when an API recipe is relevant
  post-production.md
  inputs/
  result-log.md
```

Internal IDs stay in the director and operator records; the submitted text stands on its own with the submitted media.

### Timed video and audio

Timed production keeps four clocks apart: story position, performance timing, source-media time and edited presentation time. The built-in renderer assembles declared image holds, source clips, trims, retiming, layers and audio placement through FFmpeg and extracts actual frames or sound intervals for review, with source hashes and measured durations binding each operation to real media. A rough proves only what it contains: a still hold says nothing about motion, two endpoint frames say nothing about what happened between them, and a review cites image regions and media intervals. [Timed Production](skills/series-continuity-director/references/timed-production.md) describes the render and inspection commands.

### Repair and revision

A repair opens a scoped child run from the latest candidate review, keeps the parent link, and accounts for the same approval across preparations. Timed outputs are retained before publication and can be recorded after an interruption without rerendering. [Production Repair](skills/series-continuity-director/references/production-repair.md) has the commands.

## Review and evidence

### Review actual results

A review keeps direct observation, interpretation, limitations and proposed repair apart. A failed hard criterion prevents selection, a changed task or candidate gets its own review, and a repair links to the earlier run and states what may change and what stays fixed. The HTML evidence export brings the recorded inputs, candidates, observations and decisions together on one page. [Evidence Review](skills/series-continuity-director/references/evidence-review.md) explains it.

### Investigate repeated failures

[Repair Analysis](skills/series-continuity-director/references/repair-analysis.md) groups repeated reviews by the criterion's actual definition and keeps the source run, its freshness and review receipt, the cited observations and locations, and the reviewer's reason. A cause hypothesis names its evidence groups, alternatives, protected requirements, proposed change, scope and acceptance check, in the readable report as well as the JSON, and stays a proposal until a review confirms it.

### Evaluate an explicitly selected agent

The optional [Agent Evaluation](skills/series-continuity-director/references/agent-evaluation.md) runner executes a host command you select and records logs, outputs, timing and any telemetry the host supplies. Process execution, evidence completeness, source understanding and expressive quality are judged separately: a missing output or a truncated log makes the trial incomplete whatever the exit code, and expressive quality waits for a human review. The runner gives each trial a fresh directory, not a sandbox; run trusted commands.

### Import existing manuscripts and notes

For an existing manuscript or notes, author a source plan naming the documents and the spans to analyze. Ingestion preserves the original bytes and records each span as `complete`, `partial` or `unknown`. Extraction proposals quote actual passages and mark each as a source statement, speech, observation, inference or unresolved matter, so the author reviews them before anything updates the narrative or its state. A partial passage stays partial, and disagreement between speakers stays visible. [Source Material](skills/series-continuity-director/references/source-material.md) gives the plans and operations.

### Explore alternatives without adopting them

[Creative alternatives](skills/series-continuity-director/references/creative-options.md) compares competing directions or continuations against pinned source bytes, separates durable intent from current focus, and keeps every alternative outside accepted work until the author chooses.

### Exchange public artifacts

Collaboration with another system goes through public schemas and exchange artifacts. Export and verify the material from the earlier demo:

<!-- readme-example: public-exchange -->
```sh
python skills/series-continuity-director/scripts/protocol_exchange.py export --root ../scd-authoring-demo --artifact scene-material/material.json --out public-exchange
python skills/series-continuity-director/scripts/protocol_exchange.py verify --root ../scd-authoring-demo --bundle public-exchange
```
<!-- end-readme-example -->

The receiver accepts the snapshot and its limits explicitly, without knowing which product made it or resolving the producer's private paths.

## Project data

### Complete material and explicit budgets

A project is valid however long its sources are. Originals and source media are kept in full, scene documents contain the definition text itself, evaluation logs are retained whole, and a large image is measured without decoding its whole canvas. Where you set an explicit budget and the material exceeds it, the tool reports the conflict and stops; where a real limit such as memory, storage, a decoder or a service quota is hit, it reports that limit. [Resource handling](skills/series-continuity-director/references/resource-handling.md) lists the operator options and separates content limits from format rules and working buffers.

### Project state and ownership

Four readable files, an append-only event ledger and the media, state and shot directories hold what the production made and what is true at a moment; the `narrative/` half holds what the series is about.

| File | Owns |
|---|---|
| [Series State](skills/series-continuity-director/assets/project-templates/series-state.md) | Approved canon, chronology, series format, scene and episode ledger, open arcs, continuity status. |
| [Character Profiles](skills/series-continuity-director/assets/project-templates/character-profiles.md) | Stable identity pointers, behavior, voice, performance vocabulary, relationship boundaries, approved reference pointers. |
| [Asset Registry](skills/series-continuity-director/assets/project-templates/asset-registry.md) | Adopted media with support, accepted boundaries and events, actual uses, consent or licensing evidence, effective range, derivation and supersession. |
| [Production State](skills/series-continuity-director/assets/project-templates/production-state.md) | Dated target evidence, operation cards, exact submissions, returned variants, observations, scoped tactics. |
| [State event ledger](skills/series-continuity-director/assets/project-templates/state/events.jsonl) | Approved variable-state history for the project timeline. |

State files are project data. Project work leaves the installed suite untouched, imported sensitive text is redacted before the safe remainder is kept, and a session without prior canon reports continuity as unverified and returns complete updated state when continuity matters. The layout is documented in the [state template README](skills/series-continuity-director/assets/project-templates/state/README.md); the trust rules are in [State and Trust](skills/series-continuity-director/references/state-and-trust.md) and [Temporal State](skills/series-continuity-director/references/temporal-state.md).

## Troubleshooting

**Coverage gaps.** Distinguish unfinished authoring from an invalid reference. A declared open question may be intentional; repair the link or definition the diagnostic names.

**Stale scene material.** A source changed, or the scene's scope did. Return to the complete originals, review the prepared scope and rebuild the material.

**Refused generation.** Check the prepared run, the submission and the approval. `--send` needs the receipt, actor, output count and cost bound with it. Resolve a recorded unknown result before another request.

**Missing media tools.** Planning works under the core scope. Media inspection, rendering and the aggregate validation need their declared tools, and the check names which are missing.

## Validation

The README smoke test runs the marked offline commands above in temporary directories, checks local links and checks the live command signature without contacting a service:

```sh
python skills/series-continuity-director/scripts/readme_smoke_test.py
```

For a source checkout or the repository-shaped release, regenerate the derived files and run the aggregate check, which needs the media environment:

```sh
python skills/series-continuity-director/scripts/build_flat.py
python skills/series-continuity-director/scripts/build_example.py
python skills/series-continuity-director/scripts/build_host_packages.py
python skills/series-continuity-director/scripts/validate_skill.py
```

These cover structure, contracts, source and result hashes, state, authority, generated files and the executable workflows. The [Mixed-Viewpoint Workshop](skills/series-continuity-director/examples/mixed-viewpoint-workshop/README.md) is the worked continuity example. Its third-person scene moves through an establishing master, a tracking medium, an over-the-shoulder reveal, an embodied first-person insert, a reaction close-up and a landing master. The example carries event-sourced state, a proposed atomic prop transfer, camera specifications, transitions, a continuity ledger, projections, shot requests, a director package, a submission plan and an explicit `not run` result log.

## Scope and limitations

Series Continuity Director makes continuity requirements explicit, places each in the strongest available carrier, observes the result and continues from what was accepted. Whether a model obeys an instruction, preserves pixels or produces a seamless long sequence is settled by the actual output, and a structurally consistent scene is judged for meaning by people. Source and content hashes detect changes to recorded inputs; understanding, truth and approval are recorded as separate decisions.

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) describes the development checkout, the source layout, the test commands, the generated adapters and the release build. A contribution states its intended behavior and adds a regression test for the defect it addresses, regenerates derived files with the builders, keeps contracts, documentation and executable examples aligned, and keeps private project state, media and credentials out of the product.

## Release management

Releases use the CalVer scheme `YYYY.MM.DD.N` in UTC. [package-manifest.toml](package-manifest.toml) owns the release identity, and the generated host metadata is checked against it. [CHANGELOG.md](CHANGELOG.md) records each release under its version heading; [CONTRIBUTING.md](CONTRIBUTING.md) documents the build and tag checks.

## License

Series Continuity Director is free software under the GNU GPLv3. The full text is in [LICENSE](LICENSE).

## Support

If this project is useful, you can support its development.

- GitHub Sponsors https://github.com/sponsors/livingghost
