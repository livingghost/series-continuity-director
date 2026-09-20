# Visual Language, Style Continuity, and Quality Direction

Visual language is part of series continuity. It includes line, shape, value, color, surface, light, lens, motion, framing, and finishing. Do not replace it with generic praise.

## 1. Series visual anchor

Record the approved visual anchor through observable dimensions:

```text
medium family
line and edge behavior
shape abstraction
value structure
color logic
surface treatment
lighting response
background density
lens and perspective behavior
motion rendering
finish and detail hierarchy
```

When a visual-contract-package supplies a concrete style family, preserve the selected family's grammar and domain realization. A shot may vary lighting, distance, or environment while remaining inside the same visual language.

The anchor says how the picture is drawn. The **visual register** says how the series is shot, and it is decided before the first shot is written, because every shot text inherits it. Record it in `series-state.md` under the series format as observable behaviour:

```text
coverage scale (the intended range or deliberate held scale; an establishing view only when useful)
camera behaviour (static, motivated moves, handheld; the surface's move vocabulary)
light and colour (direction, key, grade)
pacing (beats per clip, holds, cut rhythm)
finish (the rendering the frames must match)
```

Named registers (cinematic, documentary, music video, anime opening, manga cinematic, slice-of-life, and others in the vocabulary resource) are shorthand for a set of those behaviours, and the behaviours are what go into a prompt: a register label alone leaves every choice to the surface. An unspecified register leaves decisions unresolved; do not assert a universal provider default. Choose and observe the framing, movement, holds, and sound that serve this work. A wide master, close sequence, repeated composition, or abstract field may be suitable, but none is compulsory at a scene's beginning.

## 2. Style versus scene condition

Keep stable visual language separate from temporary conditions.

Stable example:

```text
clean tapered contour, broad rounded body masses, one hard shadow family, selective soft sheen, low-detail background
```

Scene condition:

```text
wet fur clumps, cold blue window fill, warm work lamp rim, rain beads on the sleeve
```

A rain scene should not silently replace the series style with photorealism. A flashback should not automatically become sepia or soft focus. A damaged camera look belongs only to a declared device profile or approved style.

## 3. Observable visual prose

Prefer instructions that a frame can show:

- source, direction, intensity, and landing of light;
- camera position and distance;
- silhouette and overlap;
- line weight and edge priority;
- shadow grouping;
- material response;
- background density;
- focal hierarchy;
- state-specific surface change.

Avoid empty language such as beautiful, epic, cinematic, high quality, dramatic, or atmospheric when no visible decision follows. Remove prose similes and speculative `as if` phrasing from visual construction; describe pose, path, timing, support, and material response directly. Use the function-scoped wording rules in [`scoped-lexicon.md`](scoped-lexicon.md).

Replace:

```text
cinematic lighting
```

with:

```text
a cool window key from frame-left shapes the face and shoulder; a low warm work lamp adds a narrow rim to the right forearm; the rear shelves stay one value family darker
```

## 4. Character identity under changing style conditions

Identity and style are related but not interchangeable. For every visible character, preserve:

- body plan and relative scale;
- face and head construction;
- stable markings;
- distinctive details and laterality;
- current era, form, wardrobe, and state;
- material boundaries and attachment points.

A style reference may guide line, shading, color, and detail hierarchy. It does not authorize copying unrelated identity, clothing, symbols, or scene layout.

## 5. Third-person visual hierarchy

External shots often include more environment and body information than first-person shots. Keep the focal hierarchy explicit:

```text
primary: face, active hands, or dominant body action
secondary: contact, prop, wardrobe structure, reaction
tertiary: environment evidence and continuity landmarks
```

A wide shot still needs one dominant readable event. A close-up still needs enough contextual anchor to preserve geography and screen direction.

## 6. Viewpoint-specific style translation

### External third person

Use silhouette, full-body weight, facial performance, blocking, and environment relations. The camera may use external lens and movement grammar.

### Over-the-shoulder

Keep the foreground character as a clear framing mass, lower its detail or contrast when needed, and protect the facing subject's expression and the shared prop or contact point.

### Embodied first person

Translate identity through visible limbs, clothing, fur or skin, equipment, breath, balance, shadow, reflection only when physically present, and interaction with other subjects. Do not require the camera owner's face to appear.

### Device view

Use only approved optics and recording traits for the declared device. Device artifacts must remain consistent with the device and era.

## 7. Material direction

Name material behavior where it affects identity, state, contact, or light:

- wet cloth darkens and clings;
- dry fur restores volume;
- polished metal produces small sharp highlights;
- matte leather separates through value and edge rather than broad gloss;
- scales carry structured reflections across plates;
- transparent glass preserves rim, interior, and background distortion;
- bedding compresses under weight;
- a damaged surface interrupts texture and contour at a fixed landmark.

Do not request every texture at maximum detail. Concentrate material specificity where it supports the story or continuity.

## 8. Weather and atmosphere

Atmosphere is physical, not a global mood filter. Build it from:

```text
far carrier
near carrier
body or object interaction
sound or light consequence
```

Example:

```text
rain crosses the rear windows; drops strike the metal awning; one wet shoulder darkens; water runs from the cuff onto the workbench; the awning impact becomes the scene's steady sound bed
```

Keep the focal subject readable. Local fog, steam, snow, dust, spray, or smoke should have a source and depth position.

## 9. Night and low light

Night is not unreadable black. Record:

- practical sources;
- environmental fill;
- silhouette separation;
- movement path visibility;
- reflective anchors;
- shadow detail policy;
- state details that must remain visible.

A source must land somewhere. A rim light needs a plausible source direction or an approved stylized grammar.

## 10. Text, logos, and symbols

Accurate text and typography are separate deliverables unless the exact target supports them reliably and the user deliberately chooses generated text.

- Keep subtitles and captions outside picture generation by default.
- Preserve exact signage or title text for post-production.
- Treat logos, signatures, and franchise identifiers as rights-sensitive assets.
- Use abstract emblem or non-legible interface treatment when exact text is unnecessary.
- Record who owns a symbol and its effective story range when it is a recurring prop or costume detail.

## 11. Quality direction by medium

### Illustration and animation

Specify line, shape, value, color, surface, background, and motion language. Do not append photorealistic camera jargon unless the approved hybrid style calls for it.

### Clean live-action or realism

Specify neutral or deliberate color balance, focal plane, material texture, practical light, clean shadows, and lens behavior. Keep local atmosphere physically located.

### Painterly or graphic work

Specify brush or edge hierarchy, plane grouping, palette limits, texture placement, and detail concentration. Do not treat all softness or texture as a universal quality improvement.

### Intentional degradation

State the actual process: low-resolution security recording, analog tape breakup, printed halftone, rough charcoal, or another approved method. Apply it consistently and only through a profile that supports it.

## 12. Negative and exclusion language

Construct the desired image positively first. Use a separate negative or exclusion field only when the exact target exposes one. When a target has only one field and tested evidence supports explicit negation, write one complete exclusion per artifact rather than compressed grammar. See [`scoped-lexicon.md`](scoped-lexicon.md).

Good division:

```text
Primary: stable external three-quarter camera, both hands visible during the transfer, pendant remains centered between them.
Separate exclusion field: duplicate hands, extra pendant, unreadable text overlay.
```

Read the final primary and negative fields together. Do not exclude a camera move, prop, state, or style element requested in the primary prompt. Do not write ambiguous integrated forms such as `no noise, grain`; write `no noise; no grain` only when both exclusions are appropriate to the selected style.

## 13. Grounded tone and production-prose cleanup

Ground tone in character behavior, physical consequence, and sensory evidence.

- Humor comes from character instinct, timing, social mismatch, or circumstance rather than narrator quips, generic jokes, or decorative reaction icons unless those belong to the approved format.
- Use a nonvisual sense when it materially changes the scene: sound, temperature, pressure, weight, smell, texture, balance, or breath. Do not add a sense merely to decorate prose.
- Replace abstract emotion labels with character-specific body language, dialogue behavior, state, and relationship action.
- Require a quiet settling image only when the segment role needs one. Interior segments may finish on continuing action, audio, eyeline, object, occlusion, or another deliberate bridge.

Fix these on sight in production prose:

- repeated functionless micro-gestures;
- negative action prose such as `does not move` when a positive held pose is clearer;
- speculative psychology or `as if` wording that the selected focalization cannot support;
- dialogue that explains visible room layout, lore, or action instead of performing character function;
- consecutive beats built from the same sentence shape;
- repeated eye-level or camera calibration after geography is already established;
- ornament, camera motion, or environmental detail with no visual, character, state, continuity, or story function.

Do not remove useful detail merely to shorten the package. Rewrite decorative or ambiguous detail into concrete direction and preserve the production knowledge that changes the result.

## 14. Style continuity review

Across shots and clips, compare:

- line weight and edge softness;
- face and body abstraction;
- palette and white balance;
- shadow count and hardness;
- highlight scale and density;
- material separation;
- background detail density;
- lens and perspective character;
- motion rendering;
- finishing grain, texture, or sharpening.

Record visible drift without inventing a hidden cause. Route the smallest correction to the visual contract, the target packaging, post-production, or asset selection.

## 15. Visual completion gate

Before submission:

- the visual anchor is named through observable grammar;
- scene conditions do not overwrite identity or style accidentally;
- focal hierarchy is clear at the selected shot scale;
- every light and atmosphere effect has source and depth;
- material responses support state and contact;
- reference images contribute only what the operation can use;
- generated text is not relied on for exact typography unless approved;
- primary and negative instructions agree;
- style continuity has review criteria.
