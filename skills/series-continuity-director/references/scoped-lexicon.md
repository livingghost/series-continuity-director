# Scoped Lexicon, Visual Prose, and Constraint Wording

Vocabulary rules are scoped by function. A word that is useful for literal sound, weather, dialogue, or an approved stylization must not become a global ban merely because the same word damages a different field. Judge the job the wording performs and the carrier that receives it.

## 1. Observable visual prose

Prefer instructions that describe something a frame or sequence can show:

- source, direction, speed, amplitude, path, and end state;
- camera position, distance, facing, and visible field;
- limb owner, contact point, occlusion, and physical response;
- silhouette, overlap, weight distribution, and support;
- light source, landing surface, shadow side, and material response;
- sound source, spatial relation, trigger, and decay;
- state change and the visible evidence that results from it.

Avoid visual-action prose that substitutes literary interpretation for construction:

- empty praise such as beautiful, stunning, amazing, epic, or cinematic without a visible consequence;
- speculative phrasing such as `as if` when the image cannot show the inferred motive;
- narrator guesses about hidden psychology when the selected focalization does not permit them;
- global mood filters standing in for blocking, light, performance, or environment;
- prose similes using `like` or `as though` when the pose, motion, timing, or material response can be written directly.

A character may use a simile in dialogue when it belongs to that character's voice. The prohibition is for production prose that a visual model must interpret.

Examples:

```text
Weak: He stands like a guard dog.
Constructive: He plants both feet shoulder-width apart, keeps the chest square to the doorway, lowers the chin, and holds one hand beside the latch.
```

```text
Weak: She receives the object as though it were sacred.
Constructive: She takes the object with both hands level at the sternum, keeps the fingertips together, lowers the breath, and does not look away until the transfer is complete.
```

## 2. Function-scoped vocabulary

Before rejecting or preserving a word, identify its function:

```text
visual action
visual quality or grade
physical atmosphere
sound relationship
dialogue
character voice
editorial note
target-specific exclusion
```

The same token may be valid in one function and harmful in another.

Examples:

- `fog` is valid when it occupies a named depth layer and affects visibility. It is weak when used as a global softness request.
- `grain` is valid when an approved analog or printed visual language requires it. It is inappropriate in a clean-realism quality profile unless deliberately selected.
- `muffled` is valid for a voice heard through a wall. It should not describe the whole image, lighting, focus, or color grade.
- `warm` is useful for a named light source or material temperature. It is weak as an unrestricted global color cast.

Do not turn a target-specific rejection symptom into a permanent suite-wide forbidden-word list. Store it as dated target evidence and test the smallest reproducible context.

## 3. Clean-realism quality profile

Use this section only when the project explicitly selects clean realism. It is not a universal style rule.

Avoid global grade phrases that often request softness, unrelated age treatment, or uncontrolled color casts:

- nostalgic grade;
- retro photo;
- old-photo look;
- film grain;
- vintage grade;
- sepia grade;
- hazy frame;
- dreamy focus;
- soft-focus image;
- global warm-tone filter;
- misty overall image.

Local physical phenomena remain valid when concrete:

- steam above a cup;
- fog beyond a bridge;
- dust in one sunbeam;
- rain on glass;
- smoke from a named source;
- condensation on a cold surface.

For clean realism, preserve a clear focal subject, neutral or intentionally balanced color, readable material texture, controlled highlights, and deep but clean shadows. Warm practical light benefits from a neutral or cool reference surface such as a wall, window, glass edge, or metal fitting.

For illustration, animation, painterly, graphic, printed, analog, or intentionally degraded styles, follow the approved visual anchor instead of applying this avoid list mechanically.

## 4. Sound words are not visual-grade words

Words such as `muffled`, `faint`, `distant`, `indistinct`, `thin`, or `compressed` are not globally forbidden. Use them only when the sound relationship itself matters and a more concrete description does not serve better.

Prefer source and path:

```text
thunder rolls beyond the closed window
```

```text
a voice reaches the room through the wall and loses its consonant edges
```

```text
footsteps sit below the steady rain bed until the door opens
```

```text
the body-camera microphone clips the nearest shout while the room behind it drops in level
```

Do not attach these sound words to the entire image, lighting, focus, color grade, or visual style unless an approved device process or visual-language contract explicitly requires that effect.

## 5. Zero-simile blocking

Blocking prose names body geometry, path, amplitude, timing, support, and landing. It does not describe one form by comparing it with another.

Delete animal comparisons, occupational comparisons, ritual comparisons, and cinematic metaphors from visual instructions when they do not change geometry.

Instead of:

```text
He crouches like a predator.
```

write:

```text
He lowers the pelvis, keeps the heels loaded, leans the torso slightly forward, and holds both hands inside the shoulder line before the first step.
```

Instead of:

```text
She stands like a commander.
```

write:

```text
She keeps the spine vertical, sets the feet apart, leaves the arms relaxed at the sides, and holds eye contact while everyone else remains one step behind her.
```

This rule applies to humans, anthropomorphic characters, animals, creatures, robots, and hybrids. Use the approved body plan directly rather than importing another species or role as shorthand.

## 6. Constructive direction before exclusions

Build the desired image, action, camera, and state positively before adding exclusions.

A weak prohibition names only the failure:

```text
Do not show the camera owner.
```

A constructive package assigns carriers:

```text
The start frame contains no mirror, reflective screen, reverse angle, or external view of the owner. The embodied camera turns only toward the workbench and ends level at chest height. Review every returned variant for reflections or external-owner drift. Use a documented negative field for selfie view or visible camera wearer only when the target provides one.
```

A weak prohibition:

```text
No duplicated hands.
```

A constructive package:

```text
C01 right hand holds the pendant throughout. C02 right hand releases only after C01 fingers close. C01 left hand remains braced against the workbench and stays visible until both characters settle.
```

An exclusion field is an additional carrier. It does not replace ownership, contact, state, framing, or landing direction.

## 7. Negative and exclusion syntax

The correct syntax depends on the actual target surface.

### Separate negative field

Use concise unwanted artifact categories when the target exposes a documented separate field:

```text
selfie view, visible camera wearer, mirror reflection, duplicate limbs, extra pendant, unreadable text
```

Read this field beside the final primary prompt. Remove stale exclusions that contradict a later revision.

### Integrated exclusions in a primary field

When the target has only one text field and tested evidence supports explicit negation, write one complete exclusion per unwanted artifact:

```text
no visible camera wearer; no mirror reflection; no duplicate pendant; no unreadable text
```

Do not compress unrelated artifacts into ambiguous grammar such as:

```text
no noise, grain
```

That phrase can be read as excluding only noise while treating grain as an ordinary noun. Use:

```text
no noise; no grain
```

only when those exclusions are actually appropriate to the selected visual language.

### Constructive translation

Whenever possible, translate a negative concern into a positive construction and retain the exclusion only as a scoped backup:

```text
Concern: extra hands.
Construction: one visible right hand from C01 closes around the pendant; C01 left hand remains on the bench; C02 right hand withdraws after release.
Scoped exclusion: duplicate hands.
```

## 8. Dialogue and character voice

Visual-prose restrictions do not erase character voice. A character may use metaphor, simile, ambiguity, repetition, dialect, fragments, or unusual rhythm when those belong to the approved character grammar.

Keep production direction and spoken text separate:

```text
Direction: He looks toward the damaged pendant, pauses for one breath, and answers without lifting the head.
Dialogue: "Looks like it survived us."
```

Do not rewrite character-specific dialogue into neutral production prose. Do not let decorative production prose contaminate exact target directions.

## 9. Scoped lexicon completion check

- every adjective changes a visible, audible, or editorial decision;
- visual prose names geometry, timing, source, contact, or response;
- similes are removed from blocking unless they are spoken dialogue;
- clean-realism avoid terms are applied only to clean realism;
- local weather and atmosphere remain available when physically placed;
- sound descriptors remain attached to sound relationships;
- target-specific wording findings remain scoped to evidence;
- positive construction exists before exclusions;
- integrated negations are grammatically complete;
- the final primary and negative fields do not contradict each other.

The vocabulary itself is the `prompt-vocabulary` resource. From this suite it is read with `scripts/vocabulary.py`: `search` while a text is being written, to find the term a surface was trained on and read what it draws; `read` when the text is finished, which walks it term by term, prints what each term draws, marks the terms the vocabulary does not know, and ends with the statements the text makes against itself. A text is not finished until it has been read back, and it is read per shot rather than per identity block, because the block is shared and the frames are not: what is visible in one shot is hidden in the next. The read is also what the user is shown, beside its rendering in their language, so the pass is not extra work. `check` remains for listing only the unknown tags. The gate runs the same check on a submission that declares `text_form` as tags and reports the unknown tags as unmeasured. A phrase that proves effective and is absent from the vocabulary is folded back into the `prompt-vocabulary` resource with a description, not kept in a project note.

A vocabulary that covers a tag set lists every part of it, including the names of characters from other works and the words for injury and explicit acts. `check` reporting a tag as known therefore says only that the term is described, never that it belongs in this submission: read the description. Two cases decide a shot. A character or work name carries that character's whole trained design and overrides the character sheet in the same text, so it is written only when the design is meant to be borrowed. And a word for a state the story does not want is drawn when it is written, whichever field it sits in; keep it out of the text rather than trusting a negative field to cancel it.

For a prose video surface the vocabulary carries phrase sets (categories `video-camera-phrases`, `video-action-phrases`, `video-scene-phrases`, `video-audio-phrases`, `video-style-phrases`, `video-character-phrases`): one-sentence shapes with the scale, the move, and what stays stable already in place. Take the shape and replace the subject; the profile's command list still decides which bracketed camera words are commands.
