# Regression Test Cases

Every case declares one enforcement disposition. `executed` means the case is exercised by [`scripts/validate_test_cases.py`](../scripts/validate_test_cases.py) or delegated to an existing validator named by that runner. `editorial review` means the case requires visual, narrative, or production judgment and must not be reduced to a brittle automatic heuristic.

## 1. Third-person default
A new scene with no requested viewpoint uses external character-aligned third person.

Enforcement: editorial review

## 2. External camera position
Reject an external shot with no concrete camera position.

Enforcement: executed

## 3. Character-restricted knowledge scope
Reject a character-restricted shot with no focal character.

Enforcement: executed

## 4. Objective external shot
Allow an external objective master that reveals only shared visible geography.

Enforcement: editorial review

## 5. Omniscient reveal
Require an explicit story purpose for an omniscient reveal.

Enforcement: editorial review

## 6. Over-the-shoulder foreground ownership
Keep the foreground shoulder, head edge, or hand attached to the aligned character.

Enforcement: editorial review

## 7. First-person camera owner
Reject embodied first person with no camera-owner character.

Enforcement: executed

## 8. First-person detached rig
Reject crane or orbit movement inside an embodied first-person shot.

Enforcement: executed

## 9. Device camera optics
Require declared device ownership and permitted device movement.

Enforcement: executed

## 10. Fixed in-world camera
Require fixed mount behavior or declared mechanical pan and tilt.

Enforcement: executed

## 11. Scene shot order
Reject duplicate or nonconsecutive shot order indices.

Enforcement: executed

## 12. Viewpoint transition trigger
Reject a profile change without a concrete trigger.

Enforcement: executed

## 13. External to over-the-shoulder
Preserve axis, prop ownership, and eyeline through the cut.

Enforcement: editorial review

## 14. External to first-person
Require a camera-ownership change and a visual or sonic bridge.

Enforcement: editorial review

## 15. First-person to external reaction
Begin the reaction shot from the accepted end state of the first-person shot.

Enforcement: editorial review

## 16. Point of audition switch
Allow character-subjective audio without a camera change when declared.

Enforcement: editorial review

## 17. Axis continuity
Preserve axis side across ordinary external coverage.

Enforcement: editorial review

## 18. Axis crossing
Require a visible crossing, neutral-axis shot, or re-establishing shot.

Enforcement: editorial review

## 19. Screen direction
Reject unexplained movement reversal across cuts.

Enforcement: editorial review

## 20. Eyeline match
Preserve eyeline height and target across shot and reverse shot.

Enforcement: editorial review

## 21. Sparse coverage
Reject redundant shots that perform the same visible function without a new interpretation.

Enforcement: editorial review

## 22. Prop ownership
Reject a prop ownership change with no state event or transition requirement.

Enforcement: executed

## 23. Atomic transfer
Require multi-entity inventory transfer to be atomic.

Enforcement: executed

## 24. Concealed injury
Project guarded performance while keeping the injury hidden when camera and wardrobe occlude it.

Enforcement: editorial review

## 25. Approved reveal
Allow a later objective insert to reveal the injury only when story disclosure changes.

Enforcement: editorial review

## 26. Viewpoint does not alter state
Use the same canonical state snapshot across camera changes until an event occurs.

Enforcement: editorial review

## 27. Flashback assets
Reject future-state identity or wardrobe assets in an earlier snapshot.

Enforcement: executed

## 28. Environment adaptation proposal
Keep hot-weather wardrobe changes proposed until approved.

Enforcement: editorial review

## 29. Shot-request angle coverage
Select references that cover the visible identity obligations for the chosen shot angle.

Enforcement: editorial review

## 30. First-person shot-requests
Request camera-owner limb references and other-character references rather than the camera owner's face.

Enforcement: editorial review

## 31. Exact target control
Reject a package that names a capability but not the actual control or request key.

Enforcement: editorial review

## 32. Unsupported input combination
Do not infer that character references and first-last frames work together.

Enforcement: editorial review

## 33. Planned versus observed result
A not-run example must not contain render observations.

Enforcement: executed

## 34. Accepted endpoint
A continuation uses the finished accepted endpoint, not the planned endpoint.

Enforcement: editorial review

## 35. Prompt self-containment
Exact target text resolves through submitted media, documented syntax, or introduced nouns.

Enforcement: editorial review

## 36. Primary and negative consistency
Reject a negative field that excludes an action requested by the final primary prompt.

Enforcement: editorial review

## 37. State hash integrity
Reject a modified state artifact whose canonical hash no longer matches.

Enforcement: executed

## 38. Camera hash integrity
Reject a modified camera artifact whose canonical hash no longer matches.

Enforcement: executed

## 39. Canonical package identity
Require the package manifest, skill metadata, adapters, protocols, and archive root to use the single canonical Series Continuity Director identity.

Enforcement: executed

## 40. Dated product release history
Require the packaged `CHANGELOG.md` to retain its history and start with a substantive current release entry whose UTC date matches the package CalVer. Product history is not an independent runtime artifact counter.

Enforcement: executed

## 41. ASCII punctuation
Reject Unicode em dash and en dash characters in runtime text.

Enforcement: executed

## 42. Deterministic example
Rebuild the canonical example and require byte-identical generated artifacts.

Enforcement: executed

## 43. Canonical reference structure
Require each consolidated runtime reference to have one continuous numbered section sequence and reject duplicated level-two topics introduced by concatenating concise and detailed drafts.

Enforcement: executed

## 44. Canonical project state layout
Require project initialization, project validation, temporal-state documentation, the shared-state protocol README, and the project-template README to use the same state subdirectory set.

Enforcement: executed

## 45. Project-template documentation conformance
Require `references/state-and-trust.md` to link to the canonical files under `assets/project-templates/`, and require those templates to retain the ownership sections used by project initialization and validation.

Enforcement: executed

## 46. Installed-suite immutability and sensitive-text redaction
Require project execution to write only to the project workspace and require sensitive imported text to be redacted before any safe remainder is retained.

Enforcement: executed

## 47. Video and audio asset records
Require reusable video records to retain inspected timing, camera, endpoints, accepted events, and non-canonized artifacts, and require audio or performance records to retain speaker, line, timing, consent, and licensing notes.

Enforcement: executed

## 48. First-person and device technique library
Require the first-person profile to retain gaze, optical, device-fault, time-control, direct-interaction, and camera-motion risk knowledge instead of only the profile name.

Enforcement: executed

## 49. Scoped lexicon and exclusion syntax
Require function-scoped vocabulary, clean-realism wording guidance, sound-versus-grade separation, zero-simile blocking, constructive direction, and unambiguous integrated negation syntax.

Enforcement: executed

## 50. Dialogue quality and beat-template fatigue
Require concrete synthetic-dialogue diagnostics, revision heuristics, silent reaction, indirect answer options, and review of recent episodes for repeated surface forms.

Enforcement: executed

## 51. Segment roles, narration, and spare generated time
Require segment delivery roles, narration and motif techniques, generated transition fields, and explicit treatment of unused generated duration.

Enforcement: executed

## 52. Operational distinction examples
Require paired examples that distinguish start frames, subject references, planning media, operands, performance drivers, endpoint evidence, dialogue routes, duration controls, viewpoint labels, and evidence stages.

Enforcement: executed

## 53. Generated-transition and adjacent-beat records
Require generated transitions to name operands, anchors, operation, durations, and run or operation-card identity, and require adjacent beats to connect through actual end and start conditions.

Enforcement: executed

## 54. Canonical production templates and full checklist
Require reusable preparation, identity-media, boundary inspection, director-package, submission, exact-field, post-production, run-review, disclosure, and archive templates plus the complete production checklist.

Enforcement: executed

## 55. Consolidated post-production structure
Require post-production knowledge to exist as one detailed canonical section sequence rather than a concise layer followed by a duplicate detailed layer.

Enforcement: executed


## 56. Capability-based verification and human authority
Require the user to retain spending, canon approval, and final acceptance while any capable host performs measurable checks before subjective viewing.

Enforcement: executed

## 57. Persistent and nonpersistent state handling
Require persistent workspaces to update canonical project files, require nonpersistent chats to return complete updated state when continuity matters, and mark missing prior canon as continuity-unverified rather than inventing it.

Enforcement: executed

## 58. Temporary expiry ownership
Require a temporary event to roll back only its own active write, never a later persistent writer that happens to use the same value.

Enforcement: executed

## 59. Character state schema enforcement
Reject undeclared character paths, values of the wrong declared type, and persistence modes not allowed for the path.

Enforcement: executed

## 60. Scene-consistent continuity ledger
Reject shot artifacts from another scene and transitions that reference shots outside the ledger.

Enforcement: executed

## 61. Structured type errors
Return validation errors rather than tracebacks for ordinary JSON container type mistakes.

Enforcement: executed

## 62. Per-character hash values
Require every value in a per-character SHA-256 map to be a canonical lowercase digest.

Enforcement: executed

## 63. Interchange path collision
Reject an envelope output that collides with its payload and preserve the original payload bytes.

Enforcement: executed

## 64. Declared payload artifact type
Reject an interchange payload type not declared by the selected capability profile.

Enforcement: executed

## 65. Project artifact boundary
Reject incomplete project manifests and type-less JSON under managed artifact directories.

Enforcement: executed

## 66. Tracked release membership
Exclude and report untracked working-tree files under release include directories.

Enforcement: executed

## 67. Release version alignment
Require package, Skill, agent adapter, and integration capability release versions to agree.

Enforcement: executed

## 68. Real integration branches
Exercise a real generated payload, compatible peer capability manifest, and invalid payload type through integration validation.

Enforcement: executed

## 69. CLI artifact type validation
Reject a wrong artifact type before a public state CLI hashes or uses it.

Enforcement: executed

## 70. Cross-OS release publication gate
Require release publication to depend on Linux and Windows archive consistency.

Enforcement: executed

## 71. Narrative contract
Reject a narrative whose chapters skip a number, whose payoff precedes its plant, whose answer precedes its question, or which names a target or a model.

Enforcement: executed

## 72. Story time anchoring
Require the narrative to name the timeline its chapters are ordered on and each chapter to name the story orders it covers, and report a chapter whose span ends before the previous chapter's begins.

Enforcement: executed

## 73. Persona phases and character span
Reject persona phases out of chapter order, a character persona that disagrees with the phase the narrative points at, and a character written out before they appear.

Enforcement: executed

## 74. Scene plot contract
Reject a scene plot with no turn, no focalization, no place in its chapter, no themes, or a statement sourced from a beat the scene does not show.

Enforcement: executed

## 75. Declared structure profile
Require a declared structure profile to name every part it has and no part it does not, each pointing at a beat the scene contains, and allow a scene to declare none.

Enforcement: executed

## 76. Realization per medium
Require a scene to break into the units its medium has, and reject a scene realized in another kind than the narrative declares.

Enforcement: executed

## 77. Narrative coverage
Report a chapter no scene covers, an arc no scene advances, a theme no scene carries, and a fact the narrative says was learned in a chapter where no beat teaches it.

Enforcement: executed

## 78. Approval chain across a change
Reject a scene plot approved against a narrative that has since changed, at the gate and in project validation both.

Enforcement: executed

## 79. Narrative entity references
Reject front matter that disagrees with its file name or its directory, a name with no file behind it, and removing an entity something still names; report a file nothing names.

Enforcement: executed

## 80. Character prohibitions in model-facing text
Reject text carrying a phrase a character is declared never to say, and report a behaviour prohibition as unmeasured rather than passing it.

Enforcement: executed
