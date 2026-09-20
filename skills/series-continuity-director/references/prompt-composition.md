# Prompt Composition and Shot Direction

A model-facing prompt is choreography under limited attention. The full director package remains richer than one field.

## 1. Shot proposition

Write one sentence:

```text
From [visible opening and camera relation], [cause] drives [subject] through [dominant physical progression], revealing [performance or story value], and landing on [usable state].
```

## 2. Causal spine

A coherent shot may contain several linked micro-actions:

```text
object raised -> gaze follows -> hand reaches -> contact -> weight shifts -> object transfers -> both settle
```

These are one event when each step causes, prepares, confirms, or resolves the next. Adjacent beats must connect: the end pose, gaze, support, prop ownership, and camera relation of one beat are the starting conditions of the next unless a declared cut, time jump, state event, or corrective derivative changes them. Independent objectives should move to another shot or pass. When an entrance or response needs causal legibility, specify the relevant stimulus and response. An unexplained entrance, held attention, or deliberately withheld cause may instead be part of the intended effect. A causal chain can make intended gaze clearer, but must still be checked against actual output; a written cause does not guarantee a gaze direction.

## 3. Camera-specific writing

### External third person

Describe visible scene geometry, camera position, subject blocking, motion path, performance, and landing. Do not write body-caused camera behavior unless the camera actually follows that body.

### Over-the-shoulder

Name the aligned character's foreground body region, the facing subject, eyeline, contact, and visible prop relation.

### Embodied first person

Describe body-caused camera motion, visible owner limbs, subject distance, contact ownership, subjective performance, and landing.

### First and last frames

Describe the physical path between supplied endpoints. Do not create a competing endpoint.

### Edit or restyle

State what source timing, camera, contact, and action remain and what changes.

## 4. Performance

Translate intention into visible behavior from approved character vocabulary. Use the signal strength that serves the applicable persona and intended reading. Keep felt, expressed, masked, and physiological channels distinct when they differ.

### Carry a property in an action

A property does not have to be stated to be drawn. An action that can only be performed when the property holds makes the model draw the property in order to draw the action, and the shot gains a beat instead of a label. Reaching a high shelf on the toes carries a height difference; ducking under a lintel carries stature; a jar lifted with both arms carries weight; a sleeve pushed back twice carries a coat that is too big; a cup held in both hands carries cold, or small hands; a chair pulled closer before sitting carries a table that is too far. The same holds for distance, size, material, temperature, age, mood, and relation: ask what a person in the scene would visibly do because the property is true, and write that.

Prefer the carried form when a direct statement has failed to hold, when the direct word is one the surface reads loosely (a little, slightly, quite), when the property is relational and the surface tends to level the two parties, or when a plain statement would sit in the text as a fact with nothing on screen to prove it. Choose the action from the scene's own staging so it reads as behaviour, then write the action alone; adding the statement beside it gives the surface two carriers that can disagree. Keep a direct statement for a property that has no natural action in the shot, and for identity locks, which must stay explicit.

## 5. Contact

Name moving limb owner, target, side, visible contact point, occlusion order, physical response, and final state.

## 6. Sound and light

Use sound, weather, and light as causes or responses. Name source, direction, landing point, and functional relationship to action.

## 7. Exact text review

- opening and first action coexist;
- camera language matches the viewpoint profile;
- spatial relations are visible and self-contained;
- action and contact are causal;
- dialogue has a stable window or another route;
- landing is usable;
- every critical fact has a carrier;
- every word names something the frame should show. An image model reads a figure of speech as content: a camera term that names an animal draws the animal, and an instruction about where the head sits in the frame moves the head.
A prompt describes the picture the camera takes, not the scene a narrator knows. Blocking, a script, and a novel say where a character stands and faces in the world: his back to the door, facing the window, turned away from the other. A prompt says what the lens sees from where it stands: in profile at a table on the right of the frame, the back of a head in the left foreground, a face turned three-quarters toward the camera. The same world fact becomes different words for every camera position, and a blocking phrase carried into a prompt unchanged is drawn as a picture relation, with the back toward the viewer whatever the room says, because the model has no room, only the frame. Translate every orientation before it enters model-facing text: take the character's facing in the world and the camera's position, work out what the lens sees, and write that. Where the geometry already settles it, write the action and the fixture and nothing about facing at all.

- text carried over from an earlier draft is reviewed as new text; the phrase that was fine before the plate existed is the one most likely to contradict it now. The gate reports facing words (back turned, from behind, facing away) as unmeasured so they are read against the plate before sending;
- every word agrees with the geometry the inspected media fixes. Once a plate or a reference places the camera and the fixtures, a character's facing follows from where the action is: someone working at a bench along the right wall is seen from the side by a camera in the doorway, and the text does not also say which way he faces. A facing, view, or placement word that cannot be true at the same time as the fixed geometry is not ignored; the model satisfies both by rebuilding the room, moving the fixture, or inventing a second one. Name the action and the fixture it happens at, and let the camera decide the rest.

## 8. Build from inspected opening evidence

Before writing the first verb, record the actual opening:

```text
camera profile and position
visible characters and body regions
poses and facing
prop ownership
contact and support
state and wardrobe
light and atmosphere
open movement paths
occlusions and unknown off-frame space
```

Revise the action when the proposed movement conflicts with that evidence. Do not ask a clearly seated character to begin by sitting, or a closed hand to release an object it does not visibly hold. Read the fixed geometry the same way before adding any facing or view word: where the fixture stands and where the camera is decides how the character is seen, and a word that contradicts that pairing asks for an impossible frame. A reverse angle swaps the sides: a fixture on the right of one shot stands on the left of the shot that looks back, and a frame that keeps it on the right has mirrored the room, however clean it looks on its own.

## 9. Write a usable landing

A landing is a frame that can be inspected and continued. State:

- camera position, scale, angle, and roll;
- character positions, facing, and support;
- gaze and performance hold;
- prop ownership and orientation;
- contact state;
- wardrobe and environmental state;
- audio tail;
- open path for the next action.

A vague ending such as `the scene ends cinematically` provides no continuity evidence.

## 10. External camera prompt construction

For external third person, include the necessary subset of:

```text
location and visible geography
camera position and focalization
shot scale and lens behavior
subject placement and facing
cause and dominant action
camera movement, if any
performance and contact
material and environment response
landing composition
```

Example structure:

```text
External character-aligned medium shot from the doorway side of the workbench, following C01. C02 raises the cracked pendant in the right hand. C01 stops one step short, protects the left side with a guarded shoulder, and reaches with the right hand. The camera tracks half a step to keep the hands and both faces clear. C02 releases only after C01 fingers close. Finish with the pendant resting in C01 right palm and both characters holding eye contact across the bench.
```

When the surface reads a shot list rather than a scene, string the fields in the order it expects: framing and angle, then movement with its speed, then subject and action, then lens, then light, then one sentence on what the shot reveals. A camera move without a speed word or a duration has no speed; write slow, deliberate, rapid, or a count of seconds. A pan swivels in place and a dolly travels, and the surface draws the difference, so the word must be the right one. A static camera is the hardest request: say that the camera is motionless for the whole shot and give the frame other motion to spend its energy on.

## 11. Over-the-shoulder construction

Record:

- aligned character and foreground body region;
- facing subject and target eyeline;
- prop or contact position between them;
- focus and detail priority;
- foreground occlusion limit;
- screen side and axis;
- landing.

Do not let an unowned shoulder or hand enter frame. The foreground body must attach to the aligned character.

## 12. Embodied first-person construction

Record:

- camera-owner body position and support;
- gaze direction and body-caused camera movement;
- visible owner limbs and ownership;
- distance and relation to other characters;
- point of audition and physiological state;
- contact and prop transfer;
- landing body state.

A first-person prompt should not use external camera verbs such as orbit or crane unless the camera belongs to a declared mechanism capable of that motion.

## 13. Dialogue window

Place important dialogue where the speaker can be visually stable. A useful window has:

- settled camera or a simple related movement;
- readable face or deliberate offscreen speaker;
- limited competing hand action;
- enough hold for line length and breath;
- a chosen audio route;
- subtitle route when requested.

If the line competes with difficult movement, move it after the action, shorten it according to character grammar, split the shot, or route it to another pass.

## 14. State transition prompt

When a shot changes state, describe the visible physical chain and resulting state, not only the label.

```text
The rain reaches the exposed shoulder first. The pale fabric darkens from the seam outward and begins to cling across the upper arm. Water runs from the cuff after the hand lowers. Finish with the shoulder and sleeve visibly wet while the inner torso remains partly dry.
```

The event ledger records the canonical change. The prompt carries only the visually relevant transition.

## 15. Requirement density

Evaluate independent objectives, not word count. A detailed causal chain can be compact in meaning. Several unrelated requests can overload a short prompt even when written tersely.

When reducing density, preserve:

- identity and state carriers;
- camera relation;
- dominant action;
- contact and ownership;
- physical response;
- performance change;
- landing.

Move independent dialogue, effects, reveals, or camera changes to another shot or pass.

## 16. Revision ladder

Start with the smallest exact prompt that carries the causal spine, then add one missing layer at a time while preserving the full director package.

```text
Pass 1: dominant movement and landing
Pass 2: contact, prop, and material response
Pass 3: character-specific performance
Pass 4: light, atmosphere, or sound trigger
Pass 5: target-specific syntax or separate fields
```

If a target omits a critical fact, change one production carrier at a time:

- strengthen the start or end frame;
- select a better character reference;
- reduce competing action;
- revise the exact sentence;
- split the shot;
- use edit, restyle, or performance transfer;
- repair in post.

Replace weak prohibitions with constructive packages:

```text
Weak: Do not reveal the concealed injury.
Constructive: Keep the jacket closed across the left side, frame the body from the uninjured side, show guarded shoulder movement instead of the wound, and review every variant for unintended exposure.
```

```text
Weak: No duplicated hands.
Constructive: C01 right hand receives the pendant; C01 left hand remains planted on the bench; C02 right hand releases after contact and withdraws into view.
```

A documented negative field can reinforce the construction, but it does not replace camera, ownership, contact, state, and landing instructions. Do not answer every problem by adding more negative sentences.

When a result shows something the text never asked for, read the text before the target. The word that names the stray thing is usually there, as a figure of speech or a framing instruction; remove it or say the same thing in plain words for what the camera sees. A negative field then carries the stray thing only as insurance against a prior the text no longer feeds.

Before changing a submission, locate the actual observed result, describe its relation to the intended effect, and distinguish observed facts from causal hypotheses. A wrong clause may be one cause, but source selection, viewpoint, depicted phase, tool capability, timing or editing can also explain a mismatch. Do not pretend every defect can be traced to one phrase, and do not remove or add text blindly.

Choose a repair at the responsible layer. Isolate a change when useful for causal comparison; allow coordinated changes when pose, contact, framing or timing must change together. Record the expected effect, linked observations, affected decisions and what remains uncertain. Reprepare when pinned inputs change, then use the scoped edit or submission authority. A successful repair suggests other places to inspect; it does not prove the same cause applies everywhere.

## 17. Prompt completion check

- the prompt begins from actual evidence;
- camera language matches the selected profile;
- every pronoun and limb owner is clear;
- action has one causal progression;
- contact has ownership, occlusion, response, and landing;
- state and wardrobe changes are physically described;
- performance uses approved character vocabulary;
- light, weather, and sound have sources and functions;
- target-facing text contains no private bookkeeping shorthand;
- the landing matches supplied endpoint media when present;
- all omitted requirements have another carrier.

## 18. Rules a machine can settle

The list above is the writer's review, and most of it needs a reader. These sixteen
are different: each one can be decided from the submitted text and the target
profile alone, before anything is generated. They carry IDs because a check in
code has to say which rule it implements, and because a rule with no ID cannot be
argued with, revised, or retired.

| ID | Rule | What it refuses |
|---|---|---|
| `SUB-01` | A continuity lock surface in scope for the shot appears in the text verbatim. | A garment named from memory instead of copied. The reference keeps doing its job on everything else, so the substitution is invisible until every take carries it. |
| `SUB-02` | A lock surface appears as its own phrase, not glued inside a longer word. | `chipped white enamel mug` satisfied by `unchipped white enamel mug`. |
| `SUB-03` | The text carries no exclusion and no absence stated as a state. | A positive field carrying a negation names the thing it is trying to keep out. A line saying a place is empty has said nothing about where anyone stands, and a reference supplies a character whether or not the frame wanted one. |
| `SUB-04` | The text carries no operator vocabulary: file names, internal IDs, seeds, hashes, or state words. | The surface reads the whole submission as a description of a picture. A file name renders as characters in the frame. |
| `SUB-05` | Every permanent feature the frame will show is named. | A tail that the plate never showed and the text never named, absent from the returned frame. |
| `SUB-06` | No noun repeats inside one sentence under the same modifier. | `the table where a cup sits on the edge of the table`. A contrast between two of a thing is not this: `the far end` beside `the near end` stands. |
| `SUB-07` | The declared inputs respect the exclusivity the target profile records. | A first frame submitted beside reference images on a surface where the two modes exclude each other. An input names the request key it occupies; where it does not and the profile offers more than one mode that could hold it, the check reports the ambiguity instead of charging a conflict the submission may not have. |
| `SUB-08` | An identity reference carries enough pixels on the feature that has to survive. | A full length figure spends nearly all of its pixels on the body, so the face inside it can be a fraction of the frame even in a large file. The floor is declared and not assumed: the target profile records what its surface documents, a submission states what this run needs, and no floor is invented if neither supplies one. Every refusal names the declared number and its source; absence of a requirement remains unmeasured. |
| `SUB-09` | A parameter the submission states respects the limit the model's offering records for the service it will use. | A clip asked for at a length below the band the service accepts for that model; the refusal would otherwise arrive in the submission response and the task, polled afterwards, would report processing forever. A video submission that states no duration is reported as not settled. |
| `SUB-10` | The request the submission describes satisfies the service's own parameter schema for the offering, as observed and stored. | A width and height pair the service does not accept, a first frame sent beside reference images where the schema forbids the pair, a duration outside the band, a preset given beside explicit geometry; each is refused with the schema rule that fails. With no stored schema the rule reports itself as not settled. |
| `SUB-11` | The weighting notation in the text is one a parser has been asked to read, in the dialect that parser reads. | A surface reads attention weights only when the request names a parsing mode, and each mode has its own spelling. Written without that parameter, the notation is drawn as characters and, on the surfaces where the same parameter also governs long-prompt handling, the text past the encoder window is discarded; written in the other mode's dialect, the weights are read as words. The offering states which parameter names the mode, what each value reads, and what an absent value means, and the rule reports itself as not settled when the offering states none. A weight written on a term the vocabulary does not know is reported as well: the weight raises the term's tokens without binding them, so an unknown term under weight spreads its attribute instead of placing it. |
| `SUB-12` | The request does not argue with itself, judged against the vocabulary rather than against taste. | A term written in the primary field and in the negative field at once is refused: it asks for a thing and against it in one request, and no setting decides which half wins. Two terms from a category the vocabulary marks as single valued, and a pair the vocabulary records as opposing, are reported instead of refused, because a second figure, a mirror, or a deliberate ambiguity can make either correct. The rule reads a tag-form text; on prose it reports itself as not settled. |
| `SUB-13` | A part these models draw badly is not asked for large in frame unless the beat needs it there. | Countable small parts (fingers, toes, teeth), thin repeated geometry (chains, mesh, spokes), lettering and reflections fail in a way that scale decides: the same hand is unremarkable in a wide shot and a defect in a close insert, because the error gets the pixels. The vocabulary marks which terms name such a thing and which terms pull the subject close; the rule reports the pair and leaves the judgement, since only the beat says whether the part has to be in the frame at all. It reads prose as well as tags, because the framing is usually decided in the prose. |
| `SUB-14` | A part the text puts out of view is not described by the same text. | A character's properties hold whether or not the frame shows them; the text of one shot states what that shot shows. Closed eyes and an eye colour in one text are two statements the surface has to choose between, and it chooses by opening the eyes. The vocabulary marks which terms hide a part and which speak about one, so the pair is found without a list of pairs, and the same rule catches a face detail written under a view from behind. Refused for a single figure; reported when the text names more than one, since the description may belong to the other one. |
| `SUB-15` | A submission says whether it is a shot, and a shot belongs to a scene whose plot was approved before any wording. | A scene proposition and a blocking table say what happens and where people stand; neither records which beat put a given thing in a given frame, and neither is agreed before the text exists. Without that stop the first thing anyone sees is a finished submission, and every correction after it is made one shot at a time. `kind` is `shot` or `asset` and an undeclared kind is refused, since a reference, a sheet panel, a plate and a probe belong to no scene. A shot names the plot as `scene_plot`, itself as `shot_id`, and optionally its `scene_id`; a plot that is absent, outside the project, unreadable, invalid, unapproved, edited after its approval, or silent about this shot is refused. The plot also names who is in the scene, and a submission naming somebody the scene does not contain is a shot of a different scene or a plot that forgot who was there; either way the two documents disagree and neither is the answer. An asset belongs to no scene, so the plot rules do not apply to it, and that is also the way around them: nothing in a text says whether it is a shot. A submission that declares itself an asset and still names a scene plot, a scene or a shot is refused, and one that does not is admitted with the skipped rules reported as unmeasured rather than passed in silence. |
| `SUB-16` | The text a model receives does not break what its characters are declared never to do. | Lock surfaces and permanent features are about what the frame shows; a persona also declares what a person would never say or do, and a gate that reads only the visual obligations admits a line in which a guarded character accounts for himself. The submission names its `narrative` and the `characters` present. A `surface` prohibition names a phrase and is refused when the text carries it; a `judgement` prohibition names a behaviour, which no string search settles, and is reported with the text rather than passed in silence. A narrative outside the project, unreadable or invalid, or a character the narrative does not carry, is refused. |

Three properties bind the implementation as much as the list does.

**It knows no provider.** The submission names a target, the profile says which
request keys that target exposes and which of them exclude each other, and the
check compares the two. A surface never seen before is supported by adding a
profile, not by editing the check.

**It reports what it could not measure.** A rule that cannot be decided says so
rather than passing quietly. A check silent about the half it skipped reads
exactly like a check that found nothing wrong.

**It measures what it can open.** The resolution rule reads dimensions out of a
still image header, in PNG, JPEG, GIF, BMP, WebP or TIFF. A video reference, or a
still in a format outside that list, is reported as not settled rather than
assumed to be large enough.

`scripts/submission_gate.py` implements these sixteen and cites the ID in every
finding, except where a submission fails before any of them applies by carrying no text at
all. Nothing else in this file is machine-checkable today, and a rule that
moves into that class earns an ID here first.

## 19. What a shot's text is about, and what the sheet is for

A character sheet states what is true of the character: the eye colour, the markings, the wardrobe, the parts and
their five columns. A shot's text states what this frame shows. They are two documents with two vocabularies, and
the most common way a prompt goes wrong is to copy from the first into the second without filtering.

Ask of every property before writing it into a shot:

```text
Is this visible in this frame?
```

An eye colour is not visible when the eyes are closed. A tail marking is not visible when the tail is behind the
body. A shirt is not visible under a blanket.

Rules:

- An identity block is a source to draw from, never a block to paste.
- Write each shot's text from the sheet, then read it back against the frame it describes.
- An invisible property written into a shot's text does not add the property to the picture. It adds a second
  statement the surface has to reconcile with the first, and it reconciles by making the property visible, which
  is to say by changing the shot.

## 20. What each refusal is called

A refusal prints a code, and a code a reader cannot look up is a code that says nothing.
Each one names the rule above that it implements.

| Rule | Code | What was found |
|---|---|---|
| `SUB-01` | `LOCK_SURFACE_ABSENT` | A declared lock surface is not in the text the model receives. |
| `SUB-02` | `LOCK_SURFACE_GLUED` | A lock surface is inside a longer phrase, so the surface is not separable. |
| `SUB-03` | `EXCLUSION_WORDING` | The text asks for an absence in words a surface answers unreliably. |
| `SUB-04` | `OPERATOR_VOCABULARY` | The text carries an internal id or a planning word the model will render. |
| `SUB-05` | `PERMANENT_FEATURE_UNNAMED` | A permanent feature the frame will show is not named. |
| `SUB-06` | `REPEATED_WORD_IN_SENTENCE` | One sentence repeats a noun, which reads as two of the thing. |
| `SUB-07` | `INPUT_MODE_CONFLICT` | The target profile forbids this combination of inputs. |
| `SUB-08` | `IDENTITY_REFERENCE_TOO_SMALL` | An identity reference is too small to hold a likeness. |
| `SUB-09` | `DURATION_NOT_INTEGER` | The offering records whole seconds and the submission states something else. |
| `SUB-09` | `DURATION_OUT_OF_BAND` | The stated duration is outside the band the offering records. |
| `SUB-10` | `SCHEMA_REFUSAL` | The service's own parameter schema refuses the request this submission describes. |
| `SUB-12` | `SELF_CONTRADICTION` | One term is asked for and asked against in the same request. |
| `SUB-14` | `HIDDEN_PART_DESCRIBED` | The text puts a part out of view and describes it in the same breath. |
| `SUB-15` | `ASSET_CARRIES_SHOT_FIELDS` | It declares itself an asset and still names a scene plot, a scene or a shot. |
| `SUB-15` | `CHARACTER_NOT_IN_SCENE` | The submission names somebody the scene does not contain. |
| `SUB-15` | `SCENE_ID_MISMATCH` | The submission and the plot name different scenes. |
| `SUB-15` | `SCENE_PLOT_BEHIND_NARRATIVE` | The plot was approved against a narrative that has since changed. |
| `SUB-15` | `SCENE_PLOT_EDITED_AFTER_APPROVAL` | The plot changed after it was approved. |
| `SUB-15` | `SCENE_PLOT_INVALID` | The scene plot does not answer its contract. |
| `SUB-15` | `SCENE_PLOT_MISSING` | A shot names no scene plot. |
| `SUB-15` | `SCENE_PLOT_OUTSIDE_ROOT` | The scene plot path leaves the project. |
| `SUB-15` | `SCENE_PLOT_UNAPPROVED` | The scene plot carries no approval that holds. |
| `SUB-15` | `SHOT_NOT_IN_SCENE_PLOT` | The shot is not one the scene plans, or the scene is not realized as shots. |
| `SUB-15` | `SUBMISSION_KIND_UNDECLARED` | The submission says neither 'shot' nor 'asset'. |
| `SUB-16` | `CHARACTER_NOT_IN_NARRATIVE` | The submission names somebody the series does not carry. |
| `SUB-16` | `NARRATIVE_INVALID` | The narrative does not answer its contract. |
| `SUB-16` | `NARRATIVE_OUTSIDE_ROOT` | The narrative path leaves the project. |
| `SUB-16` | `PROHIBITED_SURFACE` | The text carries a phrase a character is declared never to say. |

A submission carrying no model-facing text at all is refused as `TEXT_MISSING`, which names
no rule: it fails before any of them can be applied, and a rule field that carried an empty
string there would be a third thing a reader has to tell apart from a rule and from nothing.

What the gate cannot settle it reports as `unmeasured` rather than passing it, and those
carry no code because they are not refusals: they are the questions nobody answered.
