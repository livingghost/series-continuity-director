# {{SERIES_TITLE}} - Asset Registry
series_id: {{SERIES_ID}}
updated_at: {{UPDATED_AT}}

## Registry rules

Each record states what a file visibly or audibly supports, what it does not support, its origin and derivation, effective story range, actual submitted uses, rights or consent notes when applicable, and supersession. Asset type does not determine target operation. The same file can be a planning reference in one run, a submitted reference in another, and an edit operand in a third. Record each binding separately.

Do not erase media that produced an accepted scene. Supersede it through lineage and effective range.

Every record carries a `role` and a `status`. The role is the job the asset holds, written as `scope/function`, for example `C01/identity`, `e02-s03/start-frame`, `e02-s03/take`, `e02/edit`. The status is one of `candidate`, `accepted`, `superseded`, or `stale`. Exactly one asset is `accepted` for a role at a time. Write the record when the file arrives, not when it is accepted, and do not begin the next generation run while a previous output is unregistered.

When the asset holding a role is replaced or marked `stale`, every record whose `derived from` names it becomes `stale`, and the rule applies again to those records. Clear a `stale` mark only by inspecting the asset against the current upstream, then record the upstream asset it was checked against.

## Asset records

### C01-IDENTITY - [character identity asset or approved identity set]
- type: character media
- role:
- status: candidate
- files and views:
- SHA-256 per file:
- Species Morphology Profile ID and SHA-256:
- Individual Morphology Contract ID and SHA-256:
- Character Identity Contract ID and SHA-256:
- active Era, Form, and Appearance Contract IDs:
- content directly observed:
- morphology feature refs visibly proved:
- counts and attachment sites visibly proved:
- identity, form, state, surface, marking, grooming, and expression facts visibly supported:
- unsupported, occluded, out-of-frame, or ambiguous morphology and identity facts:
- approved effective story range:
- created from:
- derived from:
- upstream inspected against:
- supersedes:
- superseded by:
- actual submitted uses:
  - none
- consent, source, and licensing notes when applicable:
- known limitations:

### S01-SCENE - [scene, layout, composite, or boundary asset]
- type: scene, layout, composite, start frame, end frame, or continuation frame
- role:
- status: candidate
- file:
- SHA-256:
- content directly observed:
- camera, geography, state, and contact visibly supported:
- facts outside the frame or unsupported:
- approved effective story range:
- created from:
- derived from:
- upstream inspected against:
- supersedes:
- superseded by:
- actual submitted uses:
  - none
- consent, source, and licensing notes when applicable:
- known limitations:

### P01-PROP - [recurring prop asset]
- type: prop media
- role:
- status: candidate
- files and views:
- SHA-256 per file:
- content directly observed:
- shape, material, scale, markings, damage, attachment, and operating state visibly supported:
- unsupported sides, mechanisms, text, or interior structure:
- canonical owner or storage relation:
- approved effective story range:
- created from:
- derived from:
- upstream inspected against:
- supersedes:
- superseded by:
- actual submitted uses:
  - none
- source and licensing notes when applicable:
- known limitations:

### V01-VIDEO - [accepted source, reference, or result video]
- type: video media
- role:
- status: candidate
- file:
- SHA-256:
- duration, frame rate, dimensions, and aspect as inspected:
- track presence and audio layout:
- visible action and camera:
- character identity, wardrobe, props, state, and environment visibly supported:
- accepted opening frame:
- accepted terminal frame:
- audio tail:
- actual submitted uses:
  - none
- accepted visible or audible story events:
- visible or audible artifacts not canonized:
- approved effective story range:
- created from:
- derived from:
- upstream inspected against:
- supersedes:
- superseded by:
- performer, consent, source, and licensing notes when applicable:
- known limitations:

### A01-AUDIO-PERFORMANCE - [audio, voice, or driving performance asset]
- type: audio, voice reference, motion performance, facial performance, or driving-performance media
- role:
- status: candidate
- file:
- SHA-256:
- speaker or performer:
- language, exact line, timing, and duration:
- voice, gesture, face, body, or rhythm visibly or audibly supported:
- facts not supplied by this asset:
- actual submitted uses:
  - none
- approved effective story range:
- created from:
- derived from:
- upstream inspected against:
- supersedes:
- superseded by:
- consent and licensing notes, including permitted uses and restrictions when applicable:
- known limitations:
