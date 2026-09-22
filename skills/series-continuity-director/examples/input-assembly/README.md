# Assemble authored input choices

This synthetic example runs the public inspection, drafting, and input-building commands.
It preserves the original task and checks every generated file hash.
The local text task requires neither an image identity nor a model-service contract.
A complete input directory is still distinct from a prepared or authorized production.

Run from the skill directory:

```bash
python examples/input-assembly/build_example.py
python examples/input-assembly/build_example.py --check
```

[The recorded summary](report.json) contains fields from actual command output.
The example uses fixed synthetic reading applications through the fixture helper.
Real operators read the selected sources and write their own quotations and reasons.

## Run the input helpers

Start with an authored production task in a project directory.
The following commands leave preparation, authorization, and sending as separate operations.

```bash
python scripts/production_workflow.py inspect-inputs --root PROJECT --task task.json
python scripts/production_workflow.py draft-inputs --root PROJECT --task task.json --out-dir work/input-draft
python scripts/production_workflow.py build-inputs --root PROJECT --task task.json --choices work/input-draft/choices.json --out-dir work/inputs
```

Edit the `choices` member of the draft before calling `build-inputs`.
Retain the draft envelope; the builder recalculates its `unresolved` entries.
Use a new output directory for each construction.
A failed build preserves existing output directories and the authored task.

## Reading choices

Use the supplied key from the full route read.
`snapshot_id` can be null when the issued record remains valid without the delivery snapshot.
Choose each required document quotation and write its `why` for this task.
The builder resolves the document hashes from the issued record.
Reading choices contain `snapshot_id`, `reading_key`, and `applied`.

## Input choices

Visual choices contain `purpose`, `basis`, `subjects`, `shot_camera`, `shot_request`, `reference_activation`, and `submission`.
`basis` selects a source `path` and an authored `locator`.
Camera, request, and activation selectors contain a `path` or an explicit null where the purpose permits it.
Each subject declares `continuity`, `character_id`, and `identity_refs`.
Identity choices select a registry entry, image path, activation reference, and adoption record.
For local adoption, choose `kind: production-selection`, `run`, and the recorded `selection` ID.
The inspection output pairs selection IDs with their candidates, including multiple selections for the same candidate.
For a public receipt, choose the manifest path, receipt path, and candidate ID.
The builder derives file hashes and the local selection receipt hash.

Validation choices contain `mode`, `submission`, `target_profile`, `service_profiles`, `contract`, `evidence`, and `execution_policy`.
The first five file selectors identify the local submission, public target profile, service data, contract, and acquisition evidence.
An unused execution policy can be null.
Select the same submission file for visual and validation choices.
Target IDs and offering identities must match exactly.

The author supplies continuity and acceptance decisions.
`undecided` denotes a deliberately undecided, single-subject exploration.
An unanswered null field remains an unanswered question.
For a non-model text task, explicitly select the following applicability choices:

```json
{
  "visual": {
    "applicability": "not-applicable",
    "reason": "This synthetic task produces only local text."
  },
  "validation": {
    "applicability": "not-applicable",
    "reason": "This synthetic task sends no model request."
  }
}
```

## Inspect the result

`inputs` lists the formal files and their computed hashes.
`derived_from` identifies the source records and selected run.
`assessment_required` names judgments still needed for the current work.
`next_actions` supplies operation arguments and their effects.
`execution_ready` remains false: model requests still need rendering, review, and authorization.

The generated submission embeds the reading, visual, and validation records.
Matching task source paths point to the generated submission; the original submission remains unchanged.
Use the generated task for the normal preparation workflow.
