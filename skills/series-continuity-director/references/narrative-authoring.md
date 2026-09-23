# Narrative authoring and full source records

**Preparation and reuse:** Full applicable sources govern initial characterization and a changed scope. While preparing a scene, save actual definitions and applications using [Scene Persona](scene-persona.md). During writing or resumption in the reviewed scope, verify complete-source commitments and use that document; the instruction to read the full Persona applies to preparation, not to repeated execution within the reviewed scope. Reopen for new participants, topics, knowledge or portrayal intent, even when source hashes are unchanged.


## 1. Current full forms

Use `scripts/narrative_entity.py --project PROJECT add KIND ID` to create the selected persona, design, location, faction, system, artifact or glossary entry. The command writes only into a project directory outside the installed suite. Persona creation takes `--character ID`; it uses the complete installed form, not an emotion summary. `rename OLD NEW` updates declared references, drops approvals whose actual content changes, and prints the `narrative.py approve`, `scene_plot.py behind` and `scene_plot.py approve` commands that record the author's approvals again. `remove ID` refuses live references unless explicitly forced. Do not treat command success as authorial approval. A person the agent proposes is a candidate in the design record until the author admits them; create the persona entity and the narrative entry after that decision, once. [Story Structure](story-structure.md) section 6 owns the candidate, the scope of a confirmation and the depth a use needs.

The `design/` records retain portrayal aims, source applicability, permitted variation, intentional departures and disclosure boundaries. Persona describes an individual's enduring and conditional patterns; world records describe non-agent conditions without invented psychology. Empty cast and theme collections are valid. Select the current applicable information without copying a full private dossier into a model-facing request.

## 2. Read-only drafting checks

`scripts/authorial_intent_audit.py --root PROJECT RECORD.md` follows explicit intent links and reports source hashes, missing targets, scope fields and unresolved decisions. `scripts/persona_expression_audit.py PERSONA.md` reports placeholders and literal reuse in known fields. These operations neither rate individuality nor determine whether a performance succeeds; quoted examples are not active instructions. Inspect the full records and use `production-direction.md` for a portrayal choice.

## 3. Index and coverage

`scripts/narrative_index.py PROJECT` checks names, front matter, links and unfinished fields. `scripts/narrative_coverage.py PROJECT` compares declared narrative subjects and scenes; a coverage gap is not always an error for a design-only task. `scripts/narrative_smoke_test.py`, `scripts/scene_plot_smoke_test.py` and `scripts/narrative_index_smoke_test.py` exercise these current forms and retain evidence of failures rather than changing expected outputs silently.
