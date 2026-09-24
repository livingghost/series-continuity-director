# Command-line interface reference

Commands require Python 3.11 or later. Exit code `0` indicates success; a nonzero code indicates an input, validation or write failure. Reports go to standard output as UTF-8. A command whose report a person also reads (`init_project.py`, `init_line.py`, `validate_project.py`, `dependencies.py`, `narrative.py`, `scene_plot.py`, `narrative_entity.py`, `submission_draft.py`, `visual_continuity.py`, `observe_schema.py`, `shot_chain.py`) prints readable text in a terminal and JSON when its output goes to a pipe or a file; `--json` prints JSON anywhere. The other commands print JSON, or text where their row says so. Each command's table below specifies its side effects.

Examples use `python scripts/<name>.py` from the directory containing `SKILL.md`. For the plugin layout, that directory is `skills/series-continuity-director/`. Maintainer examples use the full script path from the directory containing `package-manifest.toml`.

Replace `PROJECT` with the series directory chosen for the task; replace other capitalized file arguments with the relevant inputs. Quote an argument containing spaces. Use the Python interpreter command available in your environment. `--help` gives each command's full arguments.

Directory arguments follow one rule:

- `--project DIR` names a project that `init_project.py` created. A command that writes refuses any other directory, and the installed suite.
- `--root DIR` names the workspace a record's relative paths resolve against. It need not be a project: a production run or an authoring example may live in any directory.
- A positional `PROJECT` is the directory a read-only report inspects.

A path a command records, such as a scene plot or an input a submission names, is relative to the project. A file a command only reads, such as `--text-file`, is an ordinary path.

## Project commands

| Command | Inputs | Output and side effects | Failure boundary |
|---|---|---|---|
| `init_project.py` | New `--out`, `--series-id`, `--title`, optional `--medium` | Creates one project directory, canonical Markdown files, manifest, event ledger, the state, narrative and media directories, a narrative with empty tables, and the persona and design forms. Prints the next commands, starting with `session_entry_points.py --project DIR --next` | Rejects an existing output path, a path inside the installed suite, or an invalid series ID |
| `init_line.py` | Existing `--project`, new `--line` | Creates the five media stages of one production line under `media/episodes/<line>/` (an episode, or a second cut of one in another register) | Rejects a directory that is not a project or is inside the installed suite, an invalid line id, or a line that already exists |
| `service_profile.py` | `<service-id>` `[--profiles <file>] [--json]` | Resolves how a service is called (endpoint, auth shape, envelope, operations, delivery, errors, limits) from an explicitly supplied `service-profiles` record and prints its transport, network deadline and observation date | Exits when no record can be found, the service is not in it, or the record names no valid transport |
| `observe_schema.py` | `schema`, `reference` or `attach-probe`, each with `--root PROJECT --profile FILE --service SERVICE --model ID --operation OPERATION --out-dir DIR`; `schema` and `reference` add `--acquisition FILE`, and `schema` takes optional `--profiles DIR` | Publishes a new evidence directory in the project and leaves the selected profile unchanged. With `--profiles DIR`, `schema` also writes the project's copy of the profile into DIR, its offering pointing at the published schema, for `submission_gate.py --profiles DIR` | Exits when the profile or offering is missing, the evidence directory exists, or DIR is outside the project or inside an installed suite |
| `vocabulary.py` | `search <query>` `[--category] [--limit]`, `read <file or ->` `[--negative <file>]`, `check <file or ->`, `categories` `[--vocabulary <file>] [--json]` | `search` finds a term while a text is being written; `read` walks a finished tag text term by term and prints what the vocabulary says each one draws, marks the terms it does not know, lists for a prose text only the listed terms found inside it, and ends with the notices (a weight on an unknown term, a term in both fields, a property named twice, terms that cannot both hold, a fragile part asked for at close scale); `check` lists only the unknown tags | Exits when the vocabulary cannot be resolved |
| `dispatch.py` | `<spec.json>` `[--send] [--poll] [--service-profiles <file>] [--profiles <dir>] [--root <dir>]` | Runs the gate on a dispatch spec, builds the exact request the named service accepts, prints it and sends nothing; with `--send` it registers the spec's files, sends, saves what came back and writes a run record | Stops on a gate refusal, on a service refusal, when no service record exists, when the record names no valid transport, when the endpoint is not https, when no network deadline is configured, or when the credential is not in the environment |
| `transport_contract.py` | (module) | The transport interface every service implements: the required functions, the outcomes accepted, refused and unknown, and the network rules (no redirect followed, https only, a deadline on every wait). `load` resolves the transport a service record names and `check` refuses a module missing a function, both before anything is claimed | |
| `transport_runware.py` | (module) | One implementation of `transport_contract.py`, for Runware: which keys a task carries, how a file is registered, how a refusal and a result are read, how a pending task is polled. Any other service is supported by its own `transport_<name>.py` against the same contract, named by the service record's `transport` | |
| `transport_synthetic.py` | (module) | A test implementation of the same contract with a different request shape. It sends only to a loopback address | |
| `resource_files.py` | (module) | Resolves an explicit resource file, environment selection, explicit `SERIES_RESOURCES` configuration, or the suite catalog | |
| `narrative.py NARRATIVE [--content-sha256]` | The series narrative | Report on stdout; no writes. `--content-sha256` prints the hash an approval has to carry and nothing else. An unknown id is reported with the declared id closest to it | Rejects a narrative that names a target or a model, an arc or a chapter naming something that does not exist, chapter numbers with a gap, a payoff before its plant, an answer before its question, a persona path outside the project, and persona phases out of chapter order. A directory gets the path of the narrative inside it |
| `narrative.py approve NARRATIVE --by NAME [--at TIME] [--note TEXT]` | The narrative, and who approved it | Records an approval the author gave: writes `approved` with `by`, `at` (RFC3339 UTC, now by default) and the content hash, then lists the scene plots written against an earlier narrative | Refuses a narrative that fails validation, a malformed `--by` or `--at`, and a file inside the installed suite, with every reason at once; writes nothing then |
| `scene_plot.py PLOT [--content-sha256]` | One scene plot | Report on stdout; no writes. `--content-sha256` prints the hash an approval has to carry | Rejects a plot that names a target or a model, a statement sourced from a beat the scene does not show, a shot the scene never planned, a scene that says nothing it leaves behind, and a `<fill: ...>` value, reported as `placeholder not filled: FIELD` |
| `scene_plot.py draft --project DIR --scene-id ID --chapter ID [--order N] [--realization KIND]` | A project and a declared chapter | Writes `narrative/scenes/ID-plot.json`: the chapter, the next free place in it, the chapter's arcs with the characters and themes they carry, the narrative hash, and the realization the medium implies. Every author decision is a `<fill: ...>` value | Refuses a chapter the narrative does not declare, a scene id or place already taken, a mixed series without `--realization`, and a directory that is not a project |
| `scene_plot.py approve PLOT --by NAME [--at TIME] [--note TEXT] [--narrative FILE]` | One plot, and who approved it | Records an approval the author gave: binds the plot to the current narrative hash, then writes `approved` with the plot's content hash | Refuses every failed check at once: the plot's contract, a placeholder, and every chapter, arc, character or theme the narrative does not declare, each with its closest declared id. Writes nothing then |
| `scene_plot.py behind --project DIR` | A project | Lists every plot written against a narrative other than the current one, with the recorded and current hashes; no writes | Approval again is the author's decision, recorded with `approve` |
| `narrative_coverage.py PROJECT [--scenes DIR] [--json] [--strict]` | A project directory, or the narrative itself | The chapter table with each chapter's story orders, places and units (shots, pages or passages, as the medium has them; all three for a mixed series), the contradictions, and what is declared and not yet covered; no writes | Exits nonzero on a contradiction, and with `--strict` on any gap. Each plot is checked whole in one pass. A gap is not a failure: a series in progress has gaps, and the report names them |
| `narrative_index.py PROJECT [--json] [--strict]` | A project directory | Every person, place, group, system, object and term the narrative directory holds, and what names each one; no writes | Rejects front matter that is missing, unreadable, disagrees with the file name or the directory, or repeats an id, and a name with no file behind it. Reports a file nothing names as a gap, and `--strict` exits nonzero on one |
| `narrative_entity.py --project DIR add KIND ID [--name] [--character] [--phase]`, `rename OLD NEW`, `remove ID [--force]` | A project directory | Writes, renames or removes one entity file with its front matter. `add persona` starts from the full installed persona form. `rename` rewrites every reference, including the scene plots that happen there, drops the approval of any document whose content it changed, and prints the approval commands that follow | Refuses a directory that is not a project or is inside the installed suite, an id that is not an id, a kind and a character that do not go together, an id already in use, and removing something still named unless `--force` |
| `validate_project.py PROJECT` | Existing project directory | Report on stdout; no writes. Each problem appears once, with a POSIX path relative to the project | Rejects a path that is not a project with one error. Otherwise rejects missing files/directories, incomplete manifest data, invalid managed artifacts, type-less JSON under `state/`, `shots/` or `narrative/`, series mismatch, a text file that is not UTF-8, and forbidden punctuation in the files this suite defines. Reports as warnings a narrative still carrying what initialization wrote and a character naming a persona document that is not there. The user's own writing is not bound by the punctuation rule, which is why the prose under `narrative/personas/`, `narrative/world/` and `narrative/glossary/` is exempt, and media is not opened as text |

### Create and inspect a series

Choose a new directory for `PROJECT`. These commands create the scaffold and a production line, add a place and inspect the resulting records. Initial narrative gaps remain authoring work; scaffolding is not approval.

<!-- executable-example: project-start -->
```text
python scripts/init_project.py --out PROJECT --series-id SERIES-01 --title "Series 01"
python scripts/init_line.py --project PROJECT --line E02-M
python scripts/narrative_entity.py --project PROJECT add location station --name "Station"
python scripts/validate_project.py PROJECT
python scripts/narrative_coverage.py PROJECT
python scripts/narrative_index.py PROJECT
python scripts/session_entry_points.py --project PROJECT --next
```
<!-- end-example: project-start -->

After the author declares the narrative, start each scene plot with `draft` and fill its `<fill: ...>` values. Once the author approves a document, `approve` records that approval with its hashes. `behind` lists the plots a narrative change has left behind:

```text
python scripts/scene_plot.py draft --project PROJECT --scene-id sc01 --chapter ch1
python scripts/narrative.py approve PROJECT/narrative/narrative.json --by "Author name"
python scripts/scene_plot.py approve PROJECT/narrative/scenes/sc01-plot.json --by "Author name"
python scripts/scene_plot.py behind --project PROJECT
```

### Prepare a submission

Write the submission with `submission_draft.py new` (see Submission gate) and supply the selected service's configuration before using these commands. Inspect the printed request and gate findings. Sending is a separate decision requiring confirmation of that exact request.

A gate-admitted submission becomes a dispatch spec with four more fields:

- `model`: the `model_identifier` of the target's offering on the named service.
- `operation`: an operation the service record declares.
- `request_validation` and `input_snapshots`: `production_workflow.py build-inputs` writes both from the validation choices, as [`examples/input-assembly/README.md`](../examples/input-assembly/README.md) shows.

The dry run names each missing field and the values that fill it.

```text
python scripts/service_profile.py SERVICE --profiles PROJECT/service-profiles.json
python scripts/dispatch.py PROJECT/media/episodes/E01/prompts/SC01-SH01.submission.json --root PROJECT --service-profiles PROJECT/service-profiles.json
```

For a live send, first prepare the production run and record approval for its exact submission. Pass `--production-run RUN_ID --authorization RECEIPT_SHA --actor ACTOR --outputs COUNT --cost-bound COST_BOUND --currency CURRENCY --send` to the dispatch command. These are actual run and authorization values; confirmation or `--send` alone is insufficient. For vocabulary assistance while composing the text:

```text
python scripts/vocabulary.py search "focus lines"
python scripts/vocabulary.py read PROJECT/prompt.txt --negative PROJECT/negative.txt
python scripts/vocabulary.py check PROJECT/prompt.txt
```

Use `observe_schema.py schema --root PROJECT --profile target-profiles/TARGET.json --service SERVICE --model ID --operation OPERATION --acquisition FILE --out-dir DIR --profiles target-profiles` when recording a parameter schema for an offering. It records the project's evidence and profile; the suite's shipped profiles stay as they are.

## Submission gate

`submission_gate.py` reads one submission document and the target profile it
names. It refuses what can be proved wrong before anything is generated, and it
is the last command before a run. Each rule and the code its finding cites are in
[`references/prompt-composition.md`](../references/prompt-composition.md) section
18.

A submission is one JSON object. Its `kind` decides which fields it needs:

<!-- submission-fields -->
| Field | Required for | Carries |
|---|---|---|
| `kind` | every kind | `shot`, `page` or `passage` for a submission that depicts one unit of a scene plot; `asset` for a reference, a sheet panel, a plate or a probe. |
| `text` | every kind | The model-facing text. |
| `route_reading` | every kind | The record of reading the `media` route, with one quoted application per required document. `submission_draft.py` attaches it. |
| `visual_continuity` | every kind | The depicted subjects and their continuity, the document that decides them, and for a shot its camera and request, bound to current bytes. `visual_continuity.py build` writes it. |
| `visual_continuity_sha256` | every kind | The hash of that block, written with it. |
| `scene_plot` | shot, page, passage | The project-relative path of the approved scene plot. |
| `scene_id` | shot, page, passage | The scene that plot covers. |
| `shot_id` | shot | A shot the plot declares. |
| `page_id` | page | A page the plot declares. |
| `panel` | none | With `page_id`: one panel of that page, from 1 to the page's declared panel count. |
| `passage_id` | passage | The passage of the plot that the image illustrates. |
| `submission_id` | none | The name the report and the run record use. |
| `target` | none | The target profile id. Without it no profile rule applies, and the report says so. |
| `service` | none | The service whose offering applies: its request keys, limits and stored schema. Without it the gate checks the model alone and reports each service rule as unmeasured. |
| `inputs` | none | The files sent with the text, each `{"role", "path", "mode"}`, where `mode` is an input mode of the model. With a service named, an input may name the offering's `request_key` instead. |
| `obligations` | none | `locks` copied verbatim, `permanent_features`, and optionally `identity_reference_roles` and `identity_reference_minimum_shorter_side`. |
| `narrative` | none | The narrative the plot was approved against, which also declares character prohibitions. |
| `characters` | none | The ids of the characters the submission depicts. |
| `dialogue` | none | Lines the output speaks, checked against the prohibitions. |
| `parameters` | none | Request settings, checked against the offering's limits and stored schema. |
| `output_kind` | none | The output of a nonvisual block, such as `text`. |
| `text_form` | none | How the text is written. Dispatch reads it; the gate checks only its shape. |
| `negative_text` | none | The negative field. Dispatch reads it; the gate checks only its shape. |
<!-- end submission-fields -->

`submission_gate_smoke_test.py` compares this table with the fields the gate
requires, so the two cannot drift.

### Draft, fill and check a submission

The draft command writes the skeleton. Every field the author or agent decides
and did not supply becomes `{"placeholder": "what it asks for"}`, and the gate
refuses each one as `placeholder not filled: FIELD` until it is filled.

| Command | Inputs | Output and side effects | Failure boundary |
|---|---|---|---|
| `submission_draft.py new` | `--project`, `--out`, `--kind`, `--target`; `--scene-plot`, `--unit` and optional `--panel` for a scene-linked kind; optional `--text-file`, `--input ROLE PATH [MODE]` or `--no-inputs`, `--parameter NAME VALUE` per request setting, `--character`, `--narrative`, `--service`, `--submission-id`, `--reading-key` with `--applied`, or `--route-reading`, and the choices `visual_continuity.py build` takes | Writes one new submission, fills `scene_id` from the plot, and prints the placeholders left and the gate command | Refuses a unit the approved plot does not declare and names the ones it does, a target no profile records, a mode or service the profile does not record, a character the scene does not contain, an existing file, and a path under `state/`, `shots/` or `narrative/` |
| `submission_draft.py reading SUBMISSION --project PROJECT` | `--reading-key KEY` with optional `--applied FILE`, or `--route-reading FILE` | Replaces `route_reading` in the submission. With a key alone, `applied` becomes a placeholder naming each document that needs a quotation | Refuses a key issued for another route, and applications the reading contract refuses |
| `visual_continuity.py build SUBMISSION --root PROJECT` | `--basis PATH` and `--basis-locator TEXT`, one `--subject SUBJECT_ID CONTINUITY [CHARACTER_ID]` per depicted subject, `--shot-camera` and `--shot-request` for a shot, optional `--reference-activation` and `--purpose`; or `--choices FILE` with the block fields, for identity references | Prints the block and its hash; `--write` replaces both in the submission | Refuses a missing or changed file, a camera or request of another shot, subjects that differ from the camera's visible subjects, and an identity reference without its adoption |
| `visual_continuity.py verify SUBMISSION --root PROJECT` | A submission carrying the block | Report on stdout; no writes | Refuses a missing block, a block changed after it was built, and anything `build` refuses |
| `submission_gate.py SUBMISSION --root PROJECT [--json] [--profiles DIR]...` | A submission document, and optionally the project's own profile directories, searched before the suite's | The verdict, the refusals, what stayed unmeasured, and the review requirements; no writes | Exit `1` is a refusal, `2` a submission that could not be read, `3` a gate that did not finish |

A submission lives under `media/`: `media/episodes/LINE/prompts/` for one that
depicts part of a scene, and `media/characters/` or `media/locations/` for an
asset. `state/`, `shots/` and `narrative/` hold typed artifacts only, and
`validate_project.py` refuses a JSON file there without an `artifact_type`. Paths
inside a submission are project-relative POSIX paths, so the gate runs with
`--root PROJECT`.

The synthetic run below drafts one panel of a comics page. `KEY` is the reading
key the first command prints last. `work/applied.json` holds the quotations the
agent writes after reading. The author fills `obligations` before the last
command.

<!-- executable-example: submission-draft -->
```text
python scripts/execution_routes.py read media --root PROJECT
python scripts/submission_draft.py new --project PROJECT --out media/episodes/E01/prompts/SC01-PG01.submission.json --kind page --scene-plot narrative/scenes/sc01-plot.json --unit PG01 --panel 2 --target xai-grok-imagine-2 --text-file PROJECT/prompt.txt --character C01 --input reference media/characters/c01-sheet.jpg reference-images --reading-key KEY
python scripts/submission_draft.py reading PROJECT/media/episodes/E01/prompts/SC01-PG01.submission.json --project PROJECT --reading-key KEY --applied PROJECT/work/applied.json
python scripts/visual_continuity.py build PROJECT/media/episodes/E01/prompts/SC01-PG01.submission.json --root PROJECT --basis narrative/scenes/sc01-plot.json --basis-locator "realization PG01" --subject C01 recurring C01 --write
python scripts/submission_gate.py PROJECT/media/episodes/E01/prompts/SC01-PG01.submission.json --root PROJECT --json
```
<!-- end-example: submission-draft -->

`submission_gate_smoke_test.py` runs these commands in a synthetic project. The
draft reports what is left to fill (synthetic output):

```json
{
  "ok": true,
  "written": "media/episodes/E01/prompts/SC01-PG01.submission.json",
  "placeholders": [
    "obligations.locks",
    "obligations.permanent_features",
    "route_reading.applied",
    "visual_continuity"
  ],
  "next": "scripts/submission_gate.py PROJECT/media/episodes/E01/prompts/SC01-PG01.submission.json --root PROJECT --json"
}
```

Run on that draft, the gate prints each placeholder and what it asks for
(synthetic output, trimmed):

```text
refused: SC01-PG01 -> xai-grok-imagine-2
  refused  PLACEHOLDER_UNFILLED: placeholder not filled: obligations.locks
           asks for: a list of the lock surfaces this frame shows, copied verbatim from the approved sheet, or []
  refused  PLACEHOLDER_UNFILLED: placeholder not filled: route_reading.applied
           asks for: a list with one entry per document named here, each {"path": the document, "quote": at least twelve words of paragraph text copied from it, "why": how it applies to this submission}: references/model-facing-artifacts.md
  unmeasured  every rule: 4 fields still hold a placeholder, so no rule was applied; fill them and run the gate again
```

A unit the plot does not declare stops the draft before anything is written
(synthetic output):

```json
{
  "ok": false,
  "error": "UNIT_NOT_IN_SCENE_PLOT: page 'PG07' is not in the approved scene plot narrative/scenes/sc01-plot.json, which declares pages PG01 (3 panels), PG02 (1 panel)"
}
```

### What the gate reads

An admitted submission is not an approved one. The report is evidence for the
user's decision to send, and the run is confirmed with them before anything is
spent. The text report prints the same refusals, unmeasured lines and review
requirements as `--json`.

Each input may name the `request_key` it occupies on the target. Where it does
not and the profile exposes more than one mode that could hold it, the ambiguity
is reported rather than charged as a conflict.

The resolution rule reads dimensions from a still image header, in PNG, JPEG,
GIF, BMP, WebP or TIFF. The floor it compares against is declared, not assumed: a
target profile may record `identity_reference.minimum_shorter_side`, and a
submission may state `obligations.identity_reference_minimum_shorter_side`. Where
neither speaks, the rule stays unmeasured. A profile floor is the surface's, so a
submission raises it rather than lowering it. Every refusal names the number and
which of the two set it.

## Resource selection and service configuration

The suite ships `assets/resources/prompt-vocabulary.json`, deterministically extracted from its own cinematic lexicon. It describes directing terms; a term's presence is not proof of a model's training or accepted syntax. `build_resources.py [--check]` regenerates or verifies it.

`resource_files.py` resolves an explicit file first, then the named resource environment variable, then an explicit `SERIES_RESOURCES` configuration, then the suite's bundled catalog. A configuration contains `{"resources": {"prompt-vocabulary": "terms.json", "service-profiles": "services.json"}}`; paths resolve inside its directory. An explicitly selected missing or invalid file is an error. Use a resource key to select the data required by the operation.

`service_profile.py SERVICE --profiles PROJECT/service-profiles.json` reads project-supplied service data. `dispatch.py SPEC --service-profiles PROJECT/service-profiles.json` uses the same source. `SERVICE_PROFILES_PATH` is the explicit environment alternative. The service template under `assets/project-templates/` holds one placeholder record: fill its `transport`, endpoint, authentication, operations and `http_timeout_seconds` from the chosen service's current documentation. No credentials or service availability are assumed. Dispatch stays dry-run by default. Live submission requires the prepared production run, recorded exact submit authorization, actor, output count, cost bound and currency, as well as `--send`. The observation date is reported, not silently refreshed.

## Shared State Protocol commands

`state_protocol.py` provides these subcommands:

| Subcommand | Required artifact inputs | Output and side effects | Failure boundary |
|---|---|---|---|
| `validate` | One or more registered JSON artifacts | Validation report; no writes | Schema, cross-invariant, or canonical hash failure |
| `finalize` | One registered JSON artifact and `--out` | Writes a sealed copy | Final artifact does not validate |
| `hash` | One JSON artifact | Prints canonical content hash; no writes | Missing or unknown artifact type |
| `resolve-world` | Base state JSON, event JSONL, timeline/order/time/snapshot ID, `--scene-context-id`, and repeatable `--character-state-schema` | Writes a sealed world snapshot | Invalid event/process, missing character schema, undeclared path, wrong value type, disallowed persistence, failed precondition, or ambiguous ordering |
| `extract-character` | World snapshot, species profile, individual morphology, identity contract, character/snapshot IDs | Writes a sealed character state snapshot | Any input has the wrong artifact type, invalid hash, missing character, or inconsistent identity binding |
| `build-context` | Scene request, world snapshot, character snapshots | Writes a sealed scene context snapshot | Missing entity, stale snapshot, or request mismatch |
| `build-projection` | Identity, species, individual morphology, state snapshot, scene context, request | Writes a sealed visual state projection | Invalid input contract, hash mismatch, or unresolved projection obligation |
| `plan-reference-bundle` | Identity, morphology, style family, target model, output directory | Writes the plan and related files under the output directory | Invalid contracts or unresolved coverage requirements |
| `make-lineage` | Explicit stateless/state-aware inputs and `--out` | Writes sealed state lineage | Missing state-aware evidence or wrong artifact type |
| `propose-environment-adaptations` | Character state schema and environment snapshot | Writes a sealed proposal | Invalid input contract or unresolved adaptation condition |
| `select-references` | Binding collection, identity and optional state contracts, story order | Writes sealed reference selection | Wrong artifact type, invalid binding, story-range mismatch, or unresolved required feature |

The world-state base, the scene-context request and the projection requests are inputs without an `artifact_type`, kept under `work/state-inputs/`. A scene context takes its scene's id: `--scene-context-id` and the request's `scene_context_id` equal the `scene_id` of the shots, which `shot_request.py` checks.

Character State Schema currently enforces declared path, value type, and allowed persistence. Nonempty `state_machines` are rejected until the protocol defines explicit path and event-trigger bindings.

Example world resolution:

```text
python scripts/state_protocol.py resolve-world --base-state PROJECT/work/state-inputs/world-base.json --events PROJECT/state/events.jsonl --character-state-schema PROJECT/state/character-C01.schema.json --timeline main --scene-context-id SC01 --story-order 20 --story-time story:20 --snapshot-id WORLD-main-20 --out PROJECT/state/snapshots/world-20.json
```

### Build a shot's state chain

`shot_chain.py CHAIN --project PROJECT` runs the chain above for the shots of one approved scene plot and binds each shot's records to it. The chain file names what the author wrote:

- `scene_plot`, `timeline_id`, `story_order`, `story_time`, `world_base`, `scene_context_request`, and optionally `events` (default `state/events.jsonl`) and `processes`;
- `characters`: per character, its `species_profile`, `individual_morphology`, `identity_contract` and `state_schema`;
- `shots`: per shot the plot declares, its `camera`, `projection` and `request`, and `character_projections` naming one projection request per character the shot shows.

It resolves the world with the scene's id as the scene context, extracts each character, builds the scene context and each projection, writes them under `state/`, fills every hash the camera, shot projection and request bind, seals the three, and runs the complete binding check. The report lists each file written and whether each shot is complete. It refuses a plot that is not approved or not realized as shots, a shot or character the plot does not declare, a scene-context request named for another scene, and a camera placed at another scene or shot.

`shot_chain_smoke_test.py` builds a two-character shot's chain from the worked example's sources, runs it twice to the same bytes, and refuses a chain that disagrees with its plot, its scene or its camera.

```text
python scripts/shot_chain.py work/state-inputs/SC01.chain.json --project PROJECT
```

A synthetic chain file, trimmed to one character:

```json
{
  "scene_plot": "narrative/scenes/SC01-plot.json",
  "timeline_id": "main", "story_order": 110, "story_time": "story:110",
  "world_base": "work/state-inputs/world-base.json",
  "scene_context_request": "work/state-inputs/SC01.context-request.json",
  "characters": {"C01": {"species_profile": "state/contracts/species-fox.json",
                         "individual_morphology": "state/contracts/individual-C01.json",
                         "identity_contract": "state/contracts/identity-C01.json",
                         "state_schema": "state/contracts/state-schema-C01.json"}},
  "shots": {"SH01": {"camera": "shots/SC01/SH01.camera.json", "projection": "shots/SC01/SH01.projection.json",
                     "request": "shots/SC01/SH01.request.json",
                     "character_projections": {"C01": "work/state-inputs/SH01-C01.projection-request.json"}}}
}
```

`select_state_references.py` is a convenience entry point for the same reference selection operation. It validates identity, era, appearance, and state artifacts before hashing them. `issue_adoption_receipt.py` validates a Candidate Manifest plus an explicit decision JSON and writes a separate sealed Adoption Receipt; it never edits the Candidate Manifest.

## Viewpoint commands

`viewpoint_protocol.py` provides:

| Subcommand | Inputs | Output and side effects | Failure boundary |
|---|---|---|---|
| `validate` | One viewpoint artifact | JSON report; no writes | Schema, profile, continuity, digest, or canonical hash failure |
| `seal` | One artifact and optional `--out` | Writes the sealed artifact, or replaces the input when `--out` is omitted | Sealed result is invalid |
| `validate-tree` | Directory of JSON artifacts | Aggregate report; no writes | Any recognized artifact is invalid |
| `build-ledger` | Scene plan, shot directory, transition directory, `--out` | Writes a sealed continuity ledger | Wrong artifact type, duplicate ID, foreign scene, scene-plan mismatch, unknown transition endpoint, or unresolved continuity |
| `seal-profiles` | Built-in profile directory | Rewrites built-in profiles with canonical hashes | Any profile is invalid after sealing |

Example:

```text
python scripts/viewpoint_protocol.py build-ledger --scene-plan PROJECT/shots/scene-plan.json --shots-dir PROJECT/shots/specs --transitions-dir PROJECT/shots/transitions --out PROJECT/shots/continuity-ledger.json
```

`seal` and `seal-profiles` are intentional write operations. Use `validate` for read-only checks.

## Target commands

`target_protocol.py` reads the durable per-model surface facts under `protocols/target/profiles`. The top level of a profile records what one model accepts on any service; each offering records one service's identifier, request keys, request shape and limits. [`protocols/target/README.md`](../protocols/target/README.md) gives the shape.

| Subcommand | Inputs | Output and side effects | Failure boundary |
|---|---|---|---|
| `validate` | One target profile | JSON report; no writes | Schema, cross-invariant, or canonical hash failure |
| `seal` | One profile and optional `--out` | Writes the resealed profile, or replaces the input when `--out` is omitted | Sealed result is invalid |
| `validate-catalog` | The profile directory and manifest | Aggregate report; no writes | A listed profile is missing, an unlisted profile is present, a profile is invalid, a `target_id` repeats, or one service names the same `model_identifier` in two profiles |

`validate_target_protocol.py` runs `validate-catalog` and is the entry point `validate_skill.py` calls.

Example:

```text
python scripts/target_protocol.py seal protocols/target/profiles/minimax-h3.json
python scripts/validate_target_protocol.py
```

`seal` is an intentional write operation and is the supported way to reseal a profile after editing its evidence. Every content change requires it, because `profile_sha256` covers the canonical profile content.

A profile carries evidence about the model with a check date and sources, and each offering carries the sources and observation date of its service. Record a fact only where it was confirmed, at the level it was confirmed for.

## Interchange commands

`build_interchange_envelope.py` takes `--profile`, an explicit payload file/type/ID, optional feature names and `--out NEW_DIRECTORY`. It validates the payload and selected operation profile before publishing three files: `artifact.json`, `declaration.json`, `envelope.json`. Existing output is never replaced; no application directory is read. The payload ID must match the actual public artifact identifier.

```bash
python scripts/build_interchange_envelope.py --profile shot-request --payload project/request.json --payload-type shot-request --payload-id REQ-SH01 --out project/handoff/SH01
python scripts/validate_integration.py --direction consumes --envelope project/incoming/envelope.json --declaration project/incoming/declaration.json --payload-root project/incoming
```

`validate_integration.py` reports the declaration check as `declaration_validation`, separately from payload results. It validates the bundled capability declaration and synthetic public data, and optionally the exact received bundle. `--direction produces` checks an outgoing envelope. Incoming data requires its explicit declaration; equal capability hashes never determine direction. Validation does not adopt media or authorize a run.

`protocol_contract.py` validates public schema structure, cross-invariants and content hashes. `temporal_state.py` applies approved state events and processes at an explicit timeline and scene point. They read only installed public contracts. `state_protocol.py` additionally enforces the project's Character State Schemas before mutation.

`protocol_exchange.py check-installed` verifies the complete installed public schema closure. `inspect --root PROJECT --artifact FILE` checks one artifact. `export --root PROJECT --artifact FILE --out NEW_DIRECTORY` writes exact artifact/contract/manifest files. `verify --root PROJECT --bundle DIRECTORY` checks that supplied bundle. An optional `--contract FILE` on inspect/export is a supplied public descriptor, never an installation. No command performs network access, media adoption or canon write-back.

`shot_request.py REQUEST --require-complete` checks all named character, scene, camera and projection bindings supplied through its artifact arguments. Without the complete flag, missing bindings are reported as unverified rather than passed.

`reference_activation_gate.py` reads an activation naming a prepared reference set, the story point the shot sits at, and the dimensions each reference is asked to settle. It refuses an activation that assembles its own reference set, asks a reference to settle a dimension outside its declared authority, reopens a dimension the package locked, or activates a reference outside the story range its binding holds over. `--root` sets where relative paths resolve from and defaults to the activation's own directory. `--json` prints the verdict. What the package does not carry is reported as unmeasured rather than passed.

```text
python scripts/reference_activation_gate.py PROJECT/handoff/SH04.activation.json --json
```

`reference_activation_gate_smoke_test.py` builds an admitted activation and damages one thing per case, declaring the refusal code each case must produce.

## Maintainer validation and build commands

| Command | Side effects |
|---|---|
| `build_derived.py [--check]` | Regenerates every derived file, each after the files it comes from: the directing vocabulary, the narrative corpus and its seal, the flat adapter, the worked example, the host files and the checked examples. `--check` compares each with a fresh build and writes nothing. It stops at the first step that fails and names it. |
| `build_example.py [--check]` | Without `--check`, regenerates the canonical example. With it, performs a read-only byte comparison. |
| `build_flat.py [--check] [--stdout]` | Regenerates the flat adapter unless `--check` or `--stdout` is selected. |
| `build_host_packages.py [--check]` | Regenerates the host specific files from `[hosts]` in the manifest. The repository is laid out as a plugin, so these sit at the repository root beside this suite: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, `hooks/hooks.json`, `AGENTS.md` and `CLAUDE.md`, plus `agents/openai.yaml` inside the suite. With `--check`, regenerates into a temporary directory and compares. A tree that does not carry the templates under `hosts/` reports that the question does not apply rather than passing in silence. |
| `build_host_packages_smoke_test.py` | Builds a repository in a temporary directory by generating into it, damages one thing, and requires the matching refusal: a missing template or hook source, a generated file edited or deleted, an undeclared `kind`, hook events at the top level, and a template that renders to invalid JSON. One case damages nothing and must be admitted. |
| `host_manifest_smoke_test.py` | Builds a repository in a temporary directory for each host rule, damages one thing, and requires the matching refusal. One case damages nothing and must be admitted. |
| `validate_host_manifests.py [--json]` | Read-only. Checks the generated host manifests against shapes that cost a hook or a plugin: a plugin manifest that names the standard hooks file the host already loads, a hooks file whose events sit at the top level, a hook command pointing at a file the package does not carry, a marketplace source that is not a directory here, a marketplace naming a different plugin, and a version that differs between the manifests, the guides and the package. |
| `run_gallery.py PROJECT [--out FILE]` | Writes `runs/gallery.html` and `runs/gallery.json`: every production run under `production/` that holds a dispatch claim, in the order it happened, each beside the text as sent, the model, every setting, the media by role, the seed and file of each result, or the refusal. `init_project.py` writes them at the start and `production_dispatch.py` rewrites them after every send and recovery, so they are current without anyone asking; run this by hand only for a record edited by hand. Built from the records and nothing else, so a result that is not in it was not sent through `dispatch.py`, and `validate_project.py` refuses a gallery that does not match the records. `--self-test` exercises it on a temporary project. |
| `work_ledger.py --project DIR begin|step|note|block|finish|abandon|show` | Writes the open task to `work/current.json` (goal, steps, which are done, what is next, what it waits on) and appends every change to `work/ledger.jsonl`. Every write holds the project lock that production runs hold and replaces the open task in one step. Refuses a directory that is not a project or is inside the installed suite, and explains an open task file that is cut off. Open a task before work that takes more than one step, mark each step as it is done, finish or abandon at the end. `session_entry_points.py` prints the open task first and `validate_project.py` checks the trail. |
| `session_entry_points.py [--project DIR] [--compare DIR] [--next] [--hook]` | Read-only. Prints the version of the copy it runs from, the entry points, the unsettled roles of a project, and the next actions in the order the layers depend on each other. `--next` prints only those actions, one per line. `--compare` reports whether another copy of the suite is behind this one. |
| `protocol_contract_smoke_test.py` | Exercises public artifacts using bundled fixtures and explicit data bundles. |
| `project_workflow_smoke_test.py` | Exercises resource selection, explicit protocol exchange and fresh-workspace operation. |
| `build_resources.py [--check]` | Rebuilds or verifies the bundled cinematic vocabulary from its source document. |
| `validate_state_protocol.py` | Read-only protocol and fixture validation. |
| `validate_viewpoint_protocol.py` | Read-only protocol and fixture validation. |
| `validate_integration.py` | Read-only bundled declarations and explicitly supplied public payload validation. |
| `refusal_coverage.py <reader> <suite>...` | Read-only. Lists every refusal a reader can make that no case in the named suites asserts a fragment of. A refusal nothing names can be deleted with every suite still green, which is the one failure a suite cannot report about itself. `validate_skill.py` runs it over `narrative.py` and `scene_plot.py`. |
| `seal_contract.py [--check]` | Seals `protocols/narrative/README.md` against the files it publishes: writes the digest of the prose into `narrative.py`, then republishes the hash of every file the contract's block lists. Also rewrites `protocols/contract-manifest.json` with the byte hash of each registered schema and of the semantics document, and the digest of the set. Run it after editing the contract, a published reader, the corpus or a public schema; `--check` says whether sealing would move anything and writes nothing. |
| `narrative_corpus.py [--check]` | Writes `narrative_corpus.json`: the documents in the case tables of the narrative and scene plot suites, each with the verdict the contract requires of it, so that an implementation elsewhere is checked against the verdicts and not against a resemblance to the readers. `--check` refuses a corpus that is not what those tables write, or a verdict in it the readers here do not reach. `validate_skill.py` runs the check. |
| `validate_test_cases.py` | Executes and classifies the numbered regression catalog. |
| `validate_knowledge_integrity.py` | Read-only knowledge and template integrity validation. |
| `submission_gate_smoke_test.py` | Runs every shipped submission fixture, the exclusivity and resolution-floor cases against profiles written by the test, and the image header readers against generated files. Compares the submission field table above with the fields the gate requires, removes each required field from an admitted submission of every kind, and runs the documented draft commands in a synthetic project. No writes outside a temporary directory. |
| `scene_plot_smoke_test.py` | Changes one thing in a scene plot that answers the contract and requires the message that rule is for. The gate fixtures settle that a bad plot stops a submission; this settles which rule stopped it. |
| `narrative_index_smoke_test.py` | Builds a project per case, changes one thing, and requires the message that rule is for. Exercises the entity commands through their argument parsers, because an option that stops parsing is a command nobody can run. |
| `narrative_smoke_test.py` | Changes one thing in a narrative that answers the contract and requires the matching refusal, and builds projects in a temporary directory to compare a narrative against the scene plots meant to cover it. |
| `asset_registry_smoke_test.py` | Runs the registry reader over minimal registries that each declare whether an error, a warning, or neither is required. Read-only. |
| `report_output_smoke_test.py` | Requires JSON for a pipe, text for a terminal and JSON with `--json`, and that every command listed at the top of this file takes `--json`. |
| `cli_encoding_smoke_test.py` | Runs commands with their streams set to a Western code page and requires UTF-8 output of a character outside it, then checks that every command calls `stdio_utf8.configure()`. CI also runs it on Windows without UTF-8 mode. |
| `validate_skill.py [--list] [--only NAME] [--jobs N]` | Aggregate repository validation plus temporary project creation outside the package. `--list` names every check, `--only` runs the named checks (`static` names the in-process ones), and `--jobs` sets how many run at once, one per CPU by default. |
| `build_release.py` | Requires a Git worktree, checks generated files, copies only tracked manifest-included members into a temporary stage, validates the stage once, then compares the extracted archive with it byte for byte and writes ZIP, SHA-256, and reports. |

The generated members are rebuilt before they are checked, and some of them are
themselves release members, so the order matters. Run from the repository root:

```text
python skills/series-continuity-director/scripts/build_derived.py
python skills/series-continuity-director/scripts/validate_skill.py
```

`build_host_packages.py` writes `agents/openai.yaml`, which is a release member, so
it runs before the release is built.

Release example, from the repository root:

```text
python skills/series-continuity-director/scripts/build_release.py --out dist/series-continuity-director.zip --reports-dir dist/reports
```

`integration_contract.py`, `project_layout.py`, `asset_registry.py` and `tree_layout.py` are internal library modules. `tree_layout.py` declares the two roots and what each owns; every other script resolves its paths through it rather than from its own location. Invoke the public commands above instead.

## Responsibility and input-boundary regression

`python scripts/layer_boundaries_smoke_test.py` checks that schema validation, content identity, state applicability, protocol direction and adoption remain distinct when artifacts are copied or exchanged. It checks the current data flow using synthetic records, not word counts or artistic merit.

`python scripts/public_boundary_smoke_test.py` exercises public declarations,
exact payload bytes, explicit send/receive direction, payload identifiers, and
publication. `python scripts/protocol_contract_smoke_test.py` validates the
schema closure and typed fixtures.

`python scripts/project_workflow_smoke_test.py` exercises fresh screen, comics,
prose and mixed workspaces, complete persona creation, visual
contract finalization, explicit resources and dry dispatch. Its service data is
synthetic and the network boundary is intercepted; it does not generate media.
These checks are run by `validate_skill.py`.

## Current production and media commands

| Command | Inputs and result | Failure boundary and regression |
|---|---|---|
| `production_workflow.py` | `prepare`, `handoff`, `capture`, `review`, `select`, `complete`; `status`, `resume`, `impact`; scoped authority commands | Refuses stale sources, fabricated modality support and unauthorized selection; `production_workflow_smoke_test.py` |
| `production_dispatch.py --root PROJECT --run RUN [--poll]` | Recover a known response and its actual outputs, never submit again | Uncertain calls and edited journals stop; `production_dispatch_smoke_test.py` |
| `timed_sequence.py --help` | Validate a plan, render an authorized sequence, extract actual frames or audio | Explicit clocks, ranges, control limits and output hashes; `timed_sequence_smoke_test.py` |
| `dependencies.py --scope core` or `--scope media [--venv DIR] [--install [--yes]]` | Reports what the scope requires and what it does not, each with its version, status and the work it enables, then names what is missing and what that affects. A Python distribution counts as present only when its smallest operation runs: Pillow encodes and decodes a PNG, resvg draws one pixel, and the SVG parsers read a document. For the media scope it prints the command that installs each missing part: the running Python's installer with `requirements-media.txt` (pip, or uv where the environment has no pip), and the platform's package manager for `ffmpeg` and `ffprobe`. A Python the system manages (PEP 668) receives nothing; `--venv DIR` installs into a virtual environment at `DIR`, created when absent, and the check then runs with that environment's Python. `--install` runs those commands after the user confirms at a terminal; `--yes` records a confirmation the user gave elsewhere, and an agent passes it only after asking | Missing dependency is not a quality pass. Without a confirmation, `--install` installs nothing |
| `production_direction_smoke_test.py` | Exercise direction, authority and actual media locators | Synthetic fixtures, not artistic proof |
| `production_examples_smoke_test.py` | Run the documented production and timed examples in separate temporary projects | Actual CLI outputs, observation and completion |
| `authorial_intent_audit.py`, `persona_expression_audit.py` | Read-only drafting and link evidence | See `references/narrative-authoring.md`; no artistic scoring |

## Reusable authoring and observed execution

- `scene_persona.py`: draft a plan from a scene plot, prepare exact scene definitions by heading and field, verify whole originals, and list the scenes a Persona change reaches; output JSON and Markdown.
- `persona_units.py FILE [--anchor A]`: list every heading and field of a Markdown definition with whether it carries an answer, or print the text an anchor names.
- `source_material.py`: retain original bytes and authored segmentation; attach actual source spans to extraction candidates.
- `agent_evaluation.py`: inspect an explicit host command plan, execute only the approved plan, retain logs/outputs and unknown metrics.
- `repair_analysis.py`: derive repeated failure groups and attributed hypotheses from actual run reviews, without execution.
- `scene_material_smoke_test.py`, `agent_evaluation_smoke_test.py`: constructed deterministic tests, not real-agent outcomes.

## Product release verification

`python scripts/release_contract.py` validates the installed product CalVer, dated release notes and generated distribution identity. `python scripts/release_management_smoke_test.py` exercises the same contract; neither command defines scene or protocol versions.

## Executable product README

From the repository root, run
`python skills/series-continuity-director/scripts/readme_smoke_test.py`.
From the installed skill directory, run `python scripts/readme_smoke_test.py`.
The command executes the product README's marked offline examples in fresh
temporary directories, verifies resulting files and source-change behavior, and
checks local links and live command signatures without sending to a provider.
It prints a JSON report, returns nonzero on failure, and does not modify project
canon or the installed skill. It checks executable instructions, not completeness
of prose, real-model behavior or artistic quality.


## Target guidance and selected execution values

Use `target_protocol.py inspect --target ID --profiles DIRECTORY` to view the
selected model record. Add `--guidance FILE`, `--service ID`, `--operation NAME`,
`--output-kind KIND`, `--purpose PURPOSE`, `--input-mode MODE` and
`--visual-language SELECTOR` to filter advice for a concrete task. Directories,
guidance files, input modes and visual selectors accept repeated arguments.
`target_protocol.py validate-guidance FILE` checks an advice record or collection.

The `execution_routes.py read` and `production_workflow.py inspect-inputs` entries
accept the same selection arguments and show the model card. Submission drafts
show the card as `target_info`; their purpose flag is `--guidance-purpose`.
Use `draft-inputs` to obtain unresolved input selections, then complete
`validation.guidance` and `validation.execution` before `build-inputs`.

`target_guidance.py` validates and filters advice, `execution_choices.py` resolves
settings and text provenance, and `visual_language.py` binds scoped anchor and
register applications. They are libraries called by the existing build and
request pipeline, not independent dispatchers. Read
[Target Guidance](../references/target-guidance.md) for schemas, full conditions,
outputs, and examples. `target_guidance_smoke_test.py` exercises their success
and refusal paths using synthetic definitions. Run it with `python`.


The submission-draft example above exercises the preliminary scene and reference
gate, not an executable service request. Before rendering or sending, resolve
its service, operation, schema evidence and execution choices with `build-inputs`.
A draft-gate verdict is neither execution readiness nor authorization.
