# Consult and apply directing knowledge

Use the `tactic-consultation` route feature to include these rules in the selected route reading.

## 1. Ask during production

Use `production_workflow.py consult-tactics --help` while planning, revising, or reviewing a scene or asset.
The agent selects the craft question, relevant source passage, and application.
Existing knowledge may be reused within its approved scope; production and canonical adoption retain their separate authority.

`inspect-inputs`, `draft-variation`, and `repair-analysis` provide concrete consultation actions for the current task.
`consult-tactics` uses the selected directing vocabulary and the project's explicit production sources.
It reads `production-state.md` when present, and task sources with the production-state or production-tactics role.
Prior application records appear in a separate source list. Use `--source` to open one or another explicit project-relative source.
These records describe intended uses; actual results remain in the production review and scoped production-state entries.
This keeps successive consultations from recursively copying every earlier report.

Vocabulary search returns lexical candidates, then opens their complete entries.
Project sources are returned in full with their file hashes and line counts.
Source order does not rank a tactic or establish its approval.
An empty vocabulary result describes that query, not all knowledge in the project.

The command saves `consultation.json` and an unanswered `decisions.json` in a new project directory.
The public [consultation example](../examples/tactic-consultation/README.md) runs the CLI and records the observed output.

## 2. Select a source and its application

A passage selector contains `kind: passage`, a consulted `path`, and inclusive `start_line` and `end_line`.
The tool extracts the chosen text and retains the complete source for context.
A vocabulary selector contains `kind: vocabulary`, the exact `category`, and the exact `term`.
The tool rechecks the consulted vocabulary bytes and full entry.

Supply `source_id`, `reason`, `uses`, and `not_used` in the decision file.
Each use records:

- the selected `source`, relationship `borrowed`, conditions `preserved`, and intended scope `changed`;
- an existing task source ID as `target_source`, or `@delivery`, with a `target_locator`;
- existing `review_criteria` IDs and the authored `review_question`.

A nonuse decision records its source selector and reason.
Select none when no consulted tactic fits.
Describe an unchanged application honestly, without manufacturing a change or a new approval.

`apply-tactics` snapshots the selected source and the authored target file.
It adds a `tactic-application` source to a copied task and links it through the existing translation notes.
It leaves the original task, target text, project state, and authority unchanged.
Author the actual direction or rendition in its normal source; the tool records that relationship rather than rewriting it.

The copied task continues through the existing input builders and preparation.
Publication is atomic into a new directory.
A stale source or task, unknown criterion or target, invalid line range, or existing output path is reported before publication.
Reconsult changed sources or correct the explicit choice and rebuild.

## 3. Judge the resulting work

Preparation captures the application through the existing source dependencies.
`draft-review` carries authored questions into their criterion reasons, leaving verdicts and observations unassessed.
The reviewer replaces those prompts with observations and judgments about the actual result.

Compare the source relationship with the authored direction and actual camera, contact, continuity, or sound behavior.
Check whether required constraints survived and unrelated material was kept out.
Separate planned improvements from observed effects and audience evidence.

Use `repair-analysis` to organize recorded failures, then ask a focused question before choosing another tactic.
After a successful result, retain the exact operation, observation, and usable scope in the existing production-state record.
Reuse that scoped knowledge without treating one result as proof of every future outcome.

## 4. Verification

`scripts/tactic_consultation_smoke_test.py` covers complete sources, explicit selectors, stale input, atomic publication, and review transfer.
The public CLI example uses synthetic local source material.
These operational checks remain distinct from model quality and author acceptance.
