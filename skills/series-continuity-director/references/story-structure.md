# Story Structure, Scene Function, Retention, and Series Rhythm

Series Continuity Director manages continuity so a recurring production can preserve readable story and performance. Structure labels are editorial tools, not automatic shot counts, fixed time boxes, or hidden generation controls.

## 1. Production hierarchy

Keep these units distinct:

```text
series
chapter or arc
episode or sequence
scene
shot
clip
run
variant
```

A scene is a continuous dramatic or informational unit in one time-place relation unless the project declares another rule. A shot is one camera construction. A clip is a target delivery unit and may contain one shot, several declared internal shots, or only part of a shot. A run is one exact submission. A variant is one returned result.

Do not assume one scene equals one clip or one shot equals one clip. Packaging follows the actual operation, duration choices, continuity plan, and post-production route.

## 2. Scene function

Before choosing coverage, state the scene's job in one sentence. Useful functions include:

- establish place, relationship, current state, or active objective;
- apply pressure to an existing objective;
- reveal or conceal information;
- force a decision;
- transfer an object, duty, risk, or relationship position;
- change a character, relationship, environment, wardrobe, or inventory state;
- demonstrate a process or capability;
- pay off an earlier setup;
- bridge two larger sequences;
- let a consequence settle.

If several functions are equally important, decide whether they form one causal progression. Split functions that create separate objectives, separate emotional peaks, incompatible landings, or competing viewpoint requirements.

## 3. Five story functions

A scene or short segment may use these functions in order, but they are not equal-duration boxes:

1. **Entry or setup:** establish the first playable and watchable condition.
2. **Build:** introduce pressure, desire, mismatch, risk, or a new variable.
3. **Turn trigger:** the visible or audible event that changes direction.
4. **Payoff or reaction:** the character-specific consequence of the trigger.
5. **Settle or bridge:** land on a stable image or hand action, sound, knowledge, or state to the next unit.

A procedural or informational scene may use setup, demonstration, change, confirmation, and handoff instead of dramatic labels. Preserve the function rather than forcing vocabulary that does not fit.

## 4. Segment delivery roles

Use these roles when they clarify opening and ending obligations. A scene plot names one of them. They say what job the scene does for the audience, not what product it is.

| Role | Opening obligation | Ending obligation |
|---|---|---|
| `standalone_short` | Provide an immediate hook or first watchable value. | Finish on a quiet settle, purposeful unresolved image, or complete relationship consequence. |
| `chapter_opening` | Establish the chapter's pressure, promise, or changed condition early. | Settle enough to orient the viewer or create a forward bridge. |
| `interior_segment` | Continue the prior accepted action, sound, state, or eyeline without fabricating a new hook. | Prefer an action, audio, object, occlusion, eyeline, or continuation bridge. |
| `chapter_closing` | Enter with enough context to resolve the current chapter movement. | Provide a quiet settle and a visible relationship, state, or story consequence. |

A scene can be an interior segment even when it begins a new clip. A clip boundary does not automatically create a new narrative opening.

## 5. Scene proposition

Write a scene proposition before a shot list:

```text
From [current story state], [pressure or intention] causes [character or group] to pursue [objective], producing [dominant visible change], and leaving [new relationship, state, object ownership, or question] at the end.
```

Example:

```text
From a tense repair meeting, C02 reveals the cracked pendant to C01, forcing C01 to accept responsibility while hiding a side injury, and leaving the pendant in C01's hand as the next scene's obligation.
```

The proposition explains why the scene exists. It is not target-facing text.

## 6. Narrative

The full field list for both artifacts is published once, in
[the narrative protocol](../protocols/narrative/README.md), with the turn every tradition
shares, the profiles a series may declare, the three media a scene is realized in, and the
focalization it is told through. This section is why each of those is there.

The proposition explains one scene. The narrative explains the series, and it is the top of the
chain: every layer below it names the layer above, and this one names the author's intent, which
has no source above it.

Write it as `narrative/narrative.json`:

```text
artifact_type   "narrative"
series_id       the series this covers
timeline_id     the timeline these chapters are ordered on, the same one the
                state events, snapshots and scene contexts carry
medium          prose, comics, screen or mixed; what a scene of this becomes
themes          id and statement; what the series is about
characters      id, name, the persona document in force now, the earlier phases of
                that life, what this person never does, and optionally the chapter
                they first_appears in and the chapter they are written_out_in
arcs            id, name, type (main, subplot, character, thematic), status,
                the themes and characters it carries, setup, rising, climax,
                resolution, and for a character arc the want it pursues and the
                need that would actually change it
acts            id, number from 1 without gaps, name, what it does, and the
                chapters it groups, in the order they are told
chapters        id, number from 1 without gaps, title, status, the arcs it advances,
                what it depicts that no other chapter depicts, and the story orders
                it covers as story_order_start and story_order_end
relationships   id, from, to, bond_type, what it is at the start, and the arcs it
                carries; directional, so both directions are declared
promises        id, statement, status, the chapter it was planted in and the
                chapter it was paid off in, as planted and payoff, and the arcs
                and characters it belongs to
questions       id, statement, status, the chapter it was introduced in and the
                chapter it was answered in, as introduced and resolved, and the
                arcs and characters it belongs to
knowledge       who learned which fact, and in which chapter
approved        by, at as an RFC3339 UTC time, and content_sha256
```

Validate it with `python scripts/narrative.py <narrative>`. The author decides when it is approved.
`python scripts/narrative.py approve <narrative> --by "<name>"` then records that approval with its
content hash, and lists the scene plots written against an earlier version:

```text
{"ok": true, "approved": "narrative/narrative.json", "by": "The author",
 "at": "2026-09-23T09:00:00Z", "content_sha256": "c829b39a...", "plots_behind": []}
```

### Promises, questions, and knowledge

These are the three debts a story takes on while it runs, and the three things a series loses track
of first.

| | Moves through | What it catches |
|---|---|---|
| `promise` | `planned`, `planted`, `paid-off`, `dropped` | a setup that is never fired. A promise paying off before it is planted is refused, and one planted three chapters ago with no payoff is reported |
| `question` | `open`, `answered`, `resolved`, `dropped` | an answer arriving before its question. An open question with no chapter yet is one the series intends to raise |
| `knowledge` | a fact, who knows it, and the chapter they learned it in | an ordering the story depends on. `audience` is one of the knowers, so "the audience sees the cost two chapters before the character does" is written down rather than remembered |

A knowledge entry is the reason a chapter order holds. Where a character acts on a fact, that
character is in the entry's `known_by` and the chapter they act in is not before `learned_in`.

### Where the narrative half lives

`media/` holds what the production made, `state/` holds what is true at a moment, `shots/` holds how
a moment is covered. None of them holds what the series is about. Without a directory that does, a
place goes into a character's world section, a term is written twice because two characters use it,
and the index goes wherever a JSON file is already allowed.

```text
narrative/narrative.json        the index above
narrative/personas/             one file per character, per phase of their life
narrative/world/locations/      a place, its geography, who is there, what it means
narrative/world/factions/       a group, what it wants, who belongs, how a member is recognised
narrative/world/systems/        how something works, and what it costs
narrative/world/artifacts/      an object that matters, who holds it, what it cannot do
narrative/glossary/             a term this series uses in its own way, defined once
narrative/scenes/               one scene plot per file
```

`init_project.py` creates all of it, and the punctuation rule that binds the suite's artifacts does
not bind the prose under `personas/`, `world/` and `glossary/`: a submission copies an artifact byte
for byte and does not copy those, so their dashes are the author's to choose.

### A persona is phase-fixed

A persona describes one period of a life. A character who has changed enough that the file no longer
describes them gets the next phase as its own file, because editing the old one makes the chapters
written against it unverifiable.

Each character may carry `phases`, in chapter order: an `id`, the `persona` for that phase, the
`from_chapter` it begins in, and, on every phase after the first, what `changed` and what `held`. A
phase boundary that says neither is a second file with no stated reason to exist. The character's
own `persona` is the document in force now, which is the last phase's, and a disagreement between
the two is refused rather than left for whichever file a session opens first.

### Told order and happened order

A chapter is a unit of telling. `story_order` is a unit of happening, and every shared-state
artifact carries one, with `timeline_id` saying which timeline it is on. The narrative names the
same timeline, and each chapter names the story orders it covers.

That is what makes the two orders comparable. A chapter whose span ends before the previous
chapter's span begins is told out of order, and `narrative.py` reports it as a notice rather than an
error, because a series may do it deliberately and the point of recording both orders is that a
reader can see which chapters do. It is also what lets a fact the narrative says was learned in a
chapter be checked against the state at that story order, and the reason this suite keeps no prose
timeline: both orders are data, and a hand-written third copy beside them has nothing able to say
which one is right.

### Who is in the series, and when

A character may name the chapter they `first_appears` in and the chapter they are `written_out_in`.
A series writes people in and writes them out, and a cast list that never says so leaves nothing
able to notice somebody in a scene three chapters after they left.
`narrative_coverage.py` reports a scene whose cast names a character outside that span as an error,
because the scene and the narrative disagree about whether that person is in the series.

A person the agent proposes is a candidate until the author admits them. Record the candidate in
the project's design record as `proposed`, with its revision, role, own purpose, use scope, name and
appearance basis, and create the persona and the narrative entry only after that decision, once. A
confirmation covers what it names: existence and role, the name, the appearance and the history are
separate decisions, and a request to think about supporting people permits proposals only. A person
the author names directly is an anchor and needs no such question. Consider an existing character,
an unnamed functional participant or an impersonal condition before a new person; a recurring
unnamed individual still holds a stable character ID, and naming them later keeps it.

Every character uses the same complete persona form at the depth their use needs. A mention needs
identity and the mentioned facts; a bounded scene needs that scene's judgment, appearance, voice and
knowledge; recurring appearances need prior outcomes and the person's own purposes; a consequential
choice needs the values and constraints behind it. The verified [Scene Persona](scene-persona.md)
document is the record that a persona is ready for one use, and the form's completion rule governs
a release.

### What a character never does

Each character in the narrative names its persona document and may declare prohibitions. There are
two kinds because the two are not settled the same way:

- `surface` names a phrase. The gate looks for it in the text a model will receive and refuses the
  submission when it is there.
- `judgement` names a behaviour. No string search settles it, so the gate reports it with the text
  for a person to answer rather than passing in silence.

Both belong in the narrative rather than in the persona document, because the gate reads JSON and a
persona is prose. The persona is where the rule is explained; this is where it is declared.

### What a finished scene owes the narrative

The narrative is read before a scene is planned and written after the scene is accepted. A scene
that is shot and never written back leaves the narrative describing a series that no longer exists,
and the next scene is planned against it.

When a scene is accepted, carry back what it settled:

- a promise it planted moves to `planted` and names the chapter; a promise it paid off moves to
  `paid-off` and names both chapters;
- a question it raised is added as `open` with the chapter it was introduced in; one it answered
  moves to `answered` or `resolved`;
- every beat that carried `teaches` becomes a `knowledge` entry, with `audience` among the knowers
  where the audience learned it too;
- the chapter's `status` moves when its scenes are done, and an arc's `status` moves when its
  climax is shot;
- `state_changes` and `relationship_delta` are what the next scene inherits, and belong in the
  state the project already keeps.

A scene also produces things about a person that no record holds. Classify each before it is
written anywhere:

| Difference | Handling |
|---|---|
| An existing rule realized | Reference the rule; add no duplicate. |
| A temporary outfit, fatigue, place or prop | State, not the persona. |
| Information the person acquired | A `knowledge` entry with the chapter and the effective time. |
| A new habit, preference, history or tie | A proposal for the persona's Design Ledger, applied under actual adoption. |
| A contradiction with the persona | Repair the scene within scope, or a separately scoped redesign. |
| An inferred inner state | An inference; an observed cue establishes no hidden truth. |

One line proves no habitual voice, one action proves no value, and a rendered detail adopts no
visual canon.

Then the author approves the narrative again, and `narrative.py approve` records it. Its
`content_sha256` covers what it now says, so every scene plot approved against the version before
it is behind. `python scripts/scene_plot.py behind --project <project>` lists each one with the
recorded and current hashes; each needs the author's approval again, recorded with
`scene_plot.py approve`. Run `python scripts/narrative_coverage.py <project>` to read what the series
still declares and no scene covers.

### What is declared against what is covered

Every other check reads one document. The chapter list and the scenes directory are two independent
statements about the same series, and the failure that leaves no trace in either file is the one
nobody notices: a chapter with no scene, an arc no scene advances, a fact the narrative says a
character learned in a chapter where nothing teaches it.

```text
python scripts/narrative_coverage.py <project>
python scripts/narrative_coverage.py <project> --json --strict
```

It reports three things. Contradictions are errors: a scene naming a chapter or an arc the narrative
does not carry, two scenes with the same id or the same place in a chapter, a beat teaching someone
who is in no part of the series. Each plot is checked whole in one run, and an unknown id is named
beside the declared id closest to it:

```text
narrative/scenes/sc01-plot.json: names chapter 'ch01', which the narrative does not carry; did you mean 'ch1'?
narrative/scenes/sc01-plot.json: names arc 'a01', which the narrative does not carry; did you mean 'a1'?
```

Gaps are not errors, because a series in progress has gaps by definition and the point is to name
them: a chapter nothing covers, a complete chapter that turns nothing, a chapter whose scenes neither
open nor close it, a promise nothing plants, a question the chapters ran past, a character who
appears in no scene. The third is a table of what each chapter holds, including which persona phase
is in force in it, so the shape of the series is readable without opening every file. It counts the
units the medium has: shots, pages or passages, and all three for a mixed series.

`--strict` exits nonzero on a gap, for a checkout that has decided its series is finished.

### The scene plot names its place

A scene plot carries `chapter`, the `arcs` it advances, its `scene_function` (`entry`, `build`,
`turn-trigger`, `payoff`, `settle`) and its `delivery_role` from the table in this document. It also
carries `state_changes`, what it leaves behind for later scenes, and `relationship_delta`, which
names the channel that moved from the list in the relationship progression section. A beat may carry
`teaches`, who learns something in it, which is what a knowledge entry is made from.

## 7. Scene plot

The proposition says why the scene exists. The plot says what its units take from it, and it is
approved before any shot text is written.

Start it with `python scripts/scene_plot.py draft --project <project> --scene-id <id> --chapter <chapter>`.
The command writes `narrative/scenes/<scene-id>-plot.json` with what the narrative declares: the
chapter, the next free place in it, the arcs the chapter carries with their characters and themes,
the narrative hash and the realization the medium implies. Every field the author decides holds a
`<fill: ...>` value, which the reader refuses as `placeholder not filled: <field>` until it is
replaced. Remove any candidate arc, character or theme the scene does not carry. The fields:

```text
artifact_type   "scene-plot"
scene_id        the scene this plot covers
narrative_sha256  the narrative this was written against, so a change above it
                invalidates this approval rather than passing unnoticed
chapter, order  which chapter, and where in it; a chapter's scenes run from 1
arcs            what this scene advances
characters      who is in this scene
themes          which of the series' themes this scene carries
focalization    zero, internal or external, and for internal, who it is through
setting         interior or exterior, location as an id, where inside it, time_of_day,
                optionally season and weather, and optionally scene_context
scene_function  entry, build, turn-trigger, payoff, or settle
delivery_role   what job the scene does for the audience
proposition     the proposition above, in one sentence
turn            the value that moves, and the pole it moves from and to
structure       optionally a declared profile and the beat each of its parts is
beats           id, what happens, and visible or context
exchanges       who speaks, about what, and what saying it accomplishes
placement       who or what is where, in the terms the blocking table uses
must_preserve   what the scene cannot change
free            what the scene leaves open
state_changes   what this scene leaves behind for later scenes
relationship_delta  which channel moved between whom
realization     kind, one of shots, pages or passages, and the units it breaks into
approved        by, at as an RFC3339 UTC time, and content_sha256
```

`setting` says where and when the scene happens, in the shared protocol's own words.
`environment-snapshot` already names `location_id`, `season`, `time_of_day`, `weather`,
`precipitation`, `wind`, `light_context` and `surface_conditions`, and `scene-context-snapshot`
binds one of those to a story-time range. The plot names the same things rather than a second
vocabulary for them, so one `location` id reaches the place file under `narrative/world/locations/`,
the measured environment at that story order, and the scene context that binds them.

`location` is an id under the protocol's `location_id` pattern and `where` is the part of that place
this scene uses. `time_of_day` is required because a scene with no hour is a scene whose light the
first shot decides and every later shot copies. `season` and `weather` are stated when the series
turns on them and left out when it does not. `scene_context` names a derived
`scene-context-snapshot` when one exists; `narrative_coverage.py` refuses one that is not there, and
reports a `location` no file under `narrative/world/locations/` describes.

`characters` names who is in the scene. Statements say what a frame shows and beats say what
happens, and neither of those is a list. Without a list, nothing answers whether a character the
series declares ever appears anywhere, or whether a submission names somebody the scene does not
contain. The gate refuses the second; `narrative_coverage.py` reports the first.

Three kinds of statement belong to the scene, because they do not change between its units. Each
list carries at least one entry.

| Kind | Level | What it states | Names its beats |
|---|---|---|---|
| `placement` | scene | who or what is where, in the terms the blocking table uses | yes |
| `must_preserve` | scene | what the scene cannot change | yes |
| `free` | scene | what the scene leaves open | no, this is what the beats leave open |

What a unit carries depends on what the unit is, because a shot has a camera, a page has an edge the
reader turns, and a passage is either shown at the pace it happens or told in less time. Every unit
carries an `id` and a `focal_beat` naming one visible beat.

| Realization | A unit also carries |
|---|---|
| `shots` | `shows`, what is in this frame, and `composition`, how the frame is arranged |
| `pages` | `shows`, and `panels`, how many it holds, with optional `spread` and `ends_on_turn` |
| `passages` | `covers`, what it narrates, and `mode`, either `scene` or `summary` |

`shows`, `composition` and `covers` are statement lists, and so are `placement`, `must_preserve`
and `free`. An entry in one is `{statement, from}`, where `from` is an array of beat ids, except in
`free`, which carries `statement` alone because it is what the beats leave open.

The other entries a scene carries have their own shapes:

| Field | An entry carries |
|---|---|
| `beats` | `id`, `beat` saying what happens, `visibility` of `visible` or `context`, and optionally `teaches`, an array of who learns something in it |
| `exchanges` | `id`, `between` as an array of character ids, `about`, `achieves` saying what saying it accomplishes, and `from` as an array of beat ids |
| `state_changes` | `target`, `change`, and `from` |
| `relationship_delta` | `channel`, `between` as an array of at least two character ids the scene contains, `change`, and `from` |
| `focalization` | `kind`, and for internal focalization `through`, naming a character the scene contains |
| `turn` | `value`, `from` and `to`, which are the two poles it moves between |

Placement is a scene statement for the same reason the blocking table is: shots of one scene that
each decide the arrangement separately are how two frames of the same moment end up mirrored.

Rules:

- A statement names the beats it follows from, so what reaches a frame is traceable rather than
  invented. Only `free` has no source, because it is what nothing decided.
- A beat marked `context` cannot be the source of anything. It is true of the scene and the frame
  does not show it.
- A beat marked `visible` that nothing takes anything from is an error. Either the scene or a shot
  carries it, or it is context.
- `approved.content_sha256` is the hash of the plot without its own approval. An approval that names
  only a time is a claim about a document that can change after the claim, so a plot edited after
  approval is refused. Once the author approves a plot, `python scripts/scene_plot.py approve <plot>
  --by "<name>"` records it: the command binds the plot to the current narrative, writes the hash,
  and refuses a plot with any failed check or undeclared id, listing every one.
- The plot names no target and no model. It is approved first and the interface is chosen after,
  because what a surface can hold changes the plan and not only the wording.
- Where the chosen interface cannot hold what the plot asks for, return that to whoever approved it
  rather than absorbing it silently.

Not every submission is a shot. A reference image, a sheet panel, a location plate and a probe
belong to no scene, so a submission says which it is: `kind` is `shot` or `asset`, and saying
nothing is refused rather than treated as the exempt case. A shot also names its plot as
`scene_plot` and itself as `shot_id`, and may name `scene_id` to be told when the two disagree.

Validate one with `python scripts/scene_plot.py <plot>`.

## 8. One dominant change per unit

A shot can contain several micro-actions when they form one physical or emotional chain:

```text
pendant rises -> gaze follows -> hand reaches -> contact -> fingers close -> prior owner releases -> receiving hand settles
```

These actions belong together because each step causes, prepares, confirms, or completes the same transfer.

Competing actions consume separate attention:

```text
transfer pendant + cross the room + reveal a wound + introduce a third character + speak a long line + orbit the camera
```

When overloaded, preserve the full scene plan and make a real editorial change:

- split the shot;
- move an independent reveal later;
- hold the camera while difficult hand contact occurs;
- create a start or end frame;
- use an edit, source performance, or separate dialogue pass;
- simplify coverage while keeping physical response and performance;
- place dialogue after the action lands.

Do not solve overload by deleting the mechanics that make the action legible.

## 9. Hooks and early value

A hook is required only when the segment role or publishing format needs one. Chapter openings and standalone shorts usually benefit from early value. Interior segments may continue prior action without a new anomaly.

Useful hook types:

- **Composition hook:** the opening frame already contains the relationship or problem.
- **Action hook:** the first visible movement has immediate consequence.
- **Line hook:** a character-specific line creates pressure, conflict, or promise.
- **Sound hook:** a sound precedes and causes a visible response.
- **Anomaly hook:** normal context and the wrong or surprising element share the opening.
- **Knowledge hook:** the camera reveals a fact that the selected focalization is allowed to show.

Avoid process-only openings such as entering, unpacking, or walking toward the interesting event unless that process is the emotional or informational event.

When a hook is required, the first few seconds should contain a small change worth noticing: an ear turns, a hand stops, an object reacts, a light reveals a silhouette, a line lands oddly, or an established routine breaks.

## 10. Turn and emotional peak

A useful turn changes the scene's direction. Common forms include:

- reversal;
- escalation;
- reveal;
- intrusion;
- choice;
- failed expectation;
- transfer of control;
- recontextualization.

The label is optional. Keep it only when it changes trigger, reaction, or ending.

One short scene usually carries one emotional or informational peak. If several moments need equal emphasis, distribute them across shots or scenes so each has a readable cause, reaction, and landing.

## 11. Relationship progression

A relationship changes through observable actions, not abstract score updates alone. Record the canonical relationship state, then show only the scene-relevant delta. A scene plot names the channel that moved, from this list and no other:

- `initiates-contact`, who reaches first;
- `gives-ground`, who yields;
- `shares-information` and `withholds-information`, what is told and what is kept;
- `carries-the-object`, who holds the shared thing;
- `public-distance` and `private-distance`, how close each is allowed in company and alone;
- `interruption-tolerance`, who may cut across whom;
- `eye-contact`, who looks and who looks away.

Duty, debt, trust, fear, resentment and affection are expressed through those channels rather than recorded as a score beside them.

A scene may increase temporary conflict without reducing long-term trust. Keep current emotion, interaction state, social mask, and persistent relationship state separate.

## 12. Reveal control

A reveal requires three decisions:

```text
what becomes known
who learns it
when the audience learns it
```

Camera access and character knowledge are separate. An external camera does not automatically authorize a reveal. Use focalization and the scene's disclosure plan.

For a concealed state, choose one of:

- remain fully concealed;
- show behavioral consequence only;
- show partial visual evidence;
- reveal directly to the audience but not all characters;
- reveal to one character through action or dialogue;
- disclose retrospectively in a later scene.

Record knowledge change in a viewpoint transition, scene record, or state event when the reveal crosses a shot boundary.

## 13. Long-form continuity

Across episodes and chapters:

- hooks belong at meaningful openings, not every internal cut;
- repeated locations need approved asset lineage and state-aware updates;
- motifs may recur with deliberate variation;
- accepted endpoint state controls the next opening;
- time jumps require era and state resolution before shot design;
- flashbacks use period-correct assets and knowledge scope;
- open arcs remain proposals until placed in the approved ledger;
- a scene can preserve unresolved tension without pretending the story is complete.

Use the episode ledger to track purpose, accepted change, endpoint, and next bridge. Do not let a generated accident define a future arc without approval.

## 14. Narration and retrospective structure

When narration is part of the series, separate the narrator's present-time position from depicted scene time.

Record:

- narrator identity and story time;
- depicted timeline and state snapshot;
- whether narration is reliable, limited, or knowingly selective;
- exact language and voice route;
- visual scene dialogue, if any;
- subtitle and localization routes;
- music behavior under narration.

Keep the depicted past visually alive and state-correct. Do not imply memory or age through an unapproved degraded grade.

Useful techniques:

- **Cold narration over a warm scene:** the narrator speaks from the present with controlled tone while the depicted past remains materially alive, warm, and immediate. The emotional distance comes from performance and timing, not visual degradation.
- **Scoring around narration:** hold low sustained texture under a sentence and let melodic material answer in the gaps.
- **Play the heaviest line dry:** remove music entirely for one line when bare voice and room sound carry the intended weight.
- **In-world metronome:** let knitting needles, sword practice, workshop tools, footsteps, a fire, or another diegetic rhythm keep time instead of adding a drum pattern.
- **Cross-episode motif arc:** allow a motif to appear complete, fragmented, off-key, withheld, varied, and finally complete when that sequence tracks approved character or relationship state.

These techniques are optional. Record their exact production route and do not apply them mechanically.

## 15. Sound and music as structure

During scene analysis, record:

```text
ambient bed
turn effect
dialogue or narration window
music function
closing or bridge sound
```

Sound should cause, reveal, connect, or settle something. A sound bridge can carry continuity across a viewpoint cut even when picture changes sharply.

Music may support:

- expectation before a turn;
- release after a decision;
- recurring character, relationship, or location identity;
- chapter-level arc;
- contrast between narrator-present and depicted-past time.

Do not restart a motif automatically at every generated clip. Plan music at sequence or chapter level when separate generations would create distracting restarts.

## 16. Multi-clip stitching and generated transitions

A clip is a delivery unit, not automatically one shot. Default to one continuous shot per clip unless internal cuts are deliberately planned and supported.

For every ordinary seam, record:

```text
outgoing clip and accepted endpoint
incoming clip and required opening
bridge type
action phase
prop and state continuity
ambient bed and audio tail
picture finishing route
fallback
```

A generated transition is a distinct operation, not another name for a cut. Record:

```text
bridge type: generated transition
outgoing operand
outgoing endpoint anchor
incoming operand
incoming endpoint anchor
generated bridge output
operation and operation-card ID
story duration
generated duration
exact controls and files
acceptance criteria
```

Use a generated transition only when the actual surface supports the required inputs together and both boundaries have been inspected. Otherwise use a conventional edit, intermediate bridge asset, or redesigned boundary.

## 17. Duration, slack, and spare generated time

Clip packing is delivery arithmetic after shot feasibility has been established.

When a supported duration exceeds the required story time, use the slack intentionally for:

- a breath;
- a reaction;
- material settling;
- ambience tail;
- a stable dialogue window;
- a seam or endpoint hold.

Spare generated time is an intentional hold or ambience tail. Do not hide it by claiming the generated clip is shorter than the verified selected duration. Record both story duration and generated duration.

Do not fill spare time with another independent action merely because seconds remain.

## 18. Retellability check

Write the scene in one sentence from memory. It should state relationship, pressure, change, and result rather than list every shot.

Weak:

```text
They enter, talk, show the pendant, switch camera, and leave.
```

Stronger:

```text
C02 makes C01 take custody of the damaged pendant, and C01's controlled reaction exposes responsibility while the hidden injury remains private.
```

If the retell is unclear, simplify the scene before adding coverage.

## 19. Publishing tie-ins

When a standalone scene or episode will be published independently, the approved opening frame may also serve as a cover image when it already contains the relationship, problem, or promise. The one-line retell may seed a title or description.

Publishing copy remains separate from generation text, target submission fields, canon, and subtitle content. Do not add a false hook, generated title card, or explanatory line to an interior segment solely because the delivery platform expects promotional copy. Create the publishing artifact from the accepted episode and its approved retell instead.

Record any crop, text-safe area, alternate cover frame, or platform-specific derivative in the asset and delivery records.

## 20. Scene completion gate

- the scene has one clear purpose;
- the segment role and opening obligation are explicit when relevant;
- the opening begins at the first watchable state;
- the dominant change is visible or audible;
- the selected focalization controls reveals;
- state changes have events or proposals;
- relationship changes are behaviorally expressed;
- every shot has a distinct function;
- the peak and landing are readable;
- clip slack has an intentional use;
- generated transitions have operation-backed records;
- the endpoint can seed the next unit;
- dialogue, sound, music, and narration have actual production routes.

### Comparing uncommitted possibilities

Use [Creative Alternatives](creative-options.md) for source-bound alternative plans. A selected plan is still a plan, not an accepted story event. The planning workspace cannot mutate narrative records or state. There is no mandatory conflict, cast, duration, or number of alternatives.
