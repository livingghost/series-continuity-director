# Production stages

Stage names are navigation headings, not hidden reasoning modes. The operative difference is the evidence that exists and the artifact that evidence is sufficient to finish. The same trust, state, continuity, ownership, and requirement-transfer rules remain active in every stage.

## 1. Stage A: Canon, state, assets, and scene design

Use when required media, state, or target evidence is missing.

1. Read project state and resolve the current story time.
2. Develop missing persona, world and visual design from the brief. Select or draft the Species, Individual, Identity, Era, Form and Appearance contracts needed by this operation. Resolve any design decisions that block the scene with the author. Validate the applicable records, then apply approved events and processes to derive current state.
3. Define the scene's intended effect, participants when present, what changes or deliberately holds, and its relation to surrounding scenes. Realize it as shots, pages or passages according to the medium; only visual operations need the following camera and media steps.
4. Choose an applicable viewpoint and visual register from the intended telling, not a fixed third-person default. Use no camera requirements for nonvisual work; record deliberate holds, recurrence, or withheld information.
5. Compose the needed views, durations, repetitions, omissions and sounds. Each has a purpose, but need not add a new event or differ in scale.
6. Define the axis of action, screen direction, eyelines, prop ownership, contact, and state visibility.
7. Add per-shot overrides and viewpoint transitions with concrete triggers and bridges.
8. Create missing character, scene, prop, start, end, boundary, or reference media briefs. A frame that shows two or more recurring characters needs each one's identity sheet adopted first, as [model-facing-artifacts.md](model-facing-artifacts.md) section 12 orders it, so brief the sheets before the shared frames.
9. Write a shot-request per shot when visual state, visible morphology, camera angle, crop, contact, or reference needs differ. Carry species, individual, identity, and state hashes plus visible morphology feature refs. `scripts/shot_chain.py` builds the state from a chain file and writes those hashes into the camera, shot projection and request.
10. Stop before claiming inspection of media that does not exist.

## 2. Stage B: Inspect, direct, and rewrite for the target

Use when the target operation is inspectable, with any real media the submission sends. A text-only submission, such as a first identity sheet, has no media to inspect and starts here once its brief exists.

1. Register every submitted file with an immutable asset ID, content hash, and lineage.
2. Inspect actual composition, identity, camera, state, props, contacts, light, and occlusions.
3. Revise the first action or camera plan when the real opening conflicts with the plan.
4. Write the full director package, including state, shot function, camera geometry, action chain, performance, sound, and landing.
5. Map real files to real controls or request keys.
6. Transfer every critical requirement to the strongest available carrier. For two or more figures in one frame, [prompt-composition.md](prompt-composition.md) section 21 ranks the carriers that keep them apart.
7. Preserve exact primary and auxiliary field contents separately from production notes. For every shot, write two statements and keep both: the scene as the world has it (who stands where, facing what) and the shot as the lens sees it from the placed camera (what fills the frame, in what facing to the camera). Only the second is sent; the first is what it is checked against.
8. Validate scene viewpoint artifacts, state artifacts, shot continuity, and target packaging.
9. Draft the submission with `scripts/submission_draft.py` and run the submission gate on the exact text and inputs. Report every refusal and everything it could not measure.
10. Work through the master checklist in [templates.md](templates.md) section 14 before returning a submission-ready package.
11. Present the complete submission or apply its fitting explicit delegation; reserve the bounded action before sending. Mark readiness separately from a result.

## 3. Stage C: Observe, finish, and continue

Use only from actual outputs or a concrete operator report.

1. Preserve exact submissions and every returned variant.
2. Verify dimensions, duration, tracks, boundary frames, and other machine-checkable facts before human review.
3. Record visible and audible symptoms without inventing hidden model causes.
4. Compare state, identity (part by part: count, colour, size, position, and change of every part in frame), camera, action, contact, prop ownership, performance, and landing against the director package.
5. Present variants and scoped observations against the intended effect. Decide repairs within granted authority, otherwise return the choice to the user. Do not use a private score to justify unlimited regeneration.
6. Finish the accepted picture and sound.
7. Extract a finished terminal frame when a physically continuous seam needs it. Omission, a new place, a flashback, or a nonvisual transition does not automatically inherit it.
8. Write accepted story events, asset lineage, run observations, and scoped tactics back to project state.
9. For physically continuous work, continue from the accepted observed endpoint, not the planned one. Preserve the declared relation for noncontinuous transitions.
