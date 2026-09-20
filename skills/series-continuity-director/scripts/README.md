# Command-line interface reference

Commands require Python 3.11 or later. Exit code `0` indicates success; a nonzero code indicates an input, validation or write failure. JSON reports go to standard output. Each command's table below specifies its side effects.

Examples use `python scripts/<name>.py` from the directory containing `SKILL.md`. For the plugin layout, that directory is `skills/series-continuity-director/`. Maintainer examples use the full script path from the directory containing `package-manifest.toml`.

Replace `PROJECT` with the series directory chosen for the task; replace other capitalized file arguments with the relevant inputs. Quote an argument containing spaces. Use the Python interpreter command available in your environment. `--help` gives each command's full arguments.

## Project commands

| Command | Inputs | Output and side effects | Failure boundary |
|---|---|---|---|
| `init_project.py` | New `--out`, `--series-id`, `--title` | Creates one project directory, canonical Markdown files, manifest, event ledger, and the state, narrative and media directories, including the blank narrative, the persona stub and its form | Rejects an existing output path or invalid series ID |
| `init_line.py` | Existing `--project`, new `--line` | Creates the five media stages of one production line under `media/episodes/<line>/` (an episode, or a second cut of one in another register) | Rejects a missing project, an invalid line id, or a line that already exists |
| `service_profile.py` | `<service-id>` `[--profiles <file>] [--json]` | Resolves how a service is called (endpoint, auth shape, envelope, operations, delivery, errors, limits) from an explicitly supplied `service-profiles` record and prints its observation date | Exits when no record can be found or the service is not in it |
| `observe_schema.py` | `<target> <service> <schema.json>` `[--source]` | Stores the service's parameter schema for one offering under `protocols/target/observed-schemas/` with the date and source, and points the offering at it; the gate then settles geometry pairs, duration bands, dependent parameters, and input exclusivity from the schema | Exits when the profile or offering is missing |
| `vocabulary.py` | `search <query>` `[--category] [--limit]`, `read <file or ->` `[--negative <file>]`, `check <file or ->`, `categories` `[--vocabulary <file>] [--json]` | `search` finds a term while a text is being written; `read` walks a finished text term by term and prints what the vocabulary says each one draws, marks the terms it does not know, and ends with the notices (a weight on an unknown term, a term in both fields, a property named twice, terms that cannot both hold, a fragile part asked for at close scale); `check` lists only the unknown tags | Exits when the vocabulary cannot be resolved |
| `dispatch.py` | `<spec.json>` `[--send] [--poll] [--service-profiles <file>] [--profiles <dir>] [--root <dir>] [--runs <dir>]` | Runs the gate on a dispatch spec, builds the exact request the named service accepts, prints it and sends nothing; with `--send` it registers the spec's files, sends, saves what came back and writes a run record | Stops on a gate refusal, on a service refusal, when no service record or transport module exists, or when the credential is not in the environment |
| `transport_runware.py` | (module) | The service-specific half of a dispatch for Runware: which keys a task carries, how a file is registered, how a refusal and a result are read, how a pending task is polled. A second service is supported by a second module against the same contract | |
| `resource_files.py` | (module) | Resolves an explicit resource file, environment selection, explicit `SERIES_RESOURCES` configuration, or the suite catalog | |
| `narrative.py NARRATIVE [--content-sha256]` | The series narrative | JSON report on stdout; no writes. `--content-sha256` prints the hash an approval has to carry and nothing else | Rejects a narrative that names a target or a model, an arc or a chapter naming something that does not exist, chapter numbers with a gap, a payoff before its plant, an answer before its question, a persona path outside the project, and persona phases out of chapter order |
| `scene_plot.py PLOT [--content-sha256]` | One scene plot | JSON report on stdout; no writes. `--content-sha256` prints the hash an approval has to carry | Rejects a plot that names a target or a model, a statement sourced from a beat the scene does not show, a shot the scene never planned, and a scene that says nothing it leaves behind |
| `narrative_coverage.py PROJECT [--scenes DIR] [--json] [--strict]` | A project directory, or the narrative itself | The chapter table with each chapter's story orders and places, the contradictions, and what is declared and not yet covered; no writes | Exits nonzero on a contradiction, and with `--strict` on any gap. A gap is not a failure: a series in progress has gaps, and the report names them |
| `narrative_index.py PROJECT [--json] [--strict]` | A project directory | Every person, place, group, system, object and term the narrative directory holds, and what names each one; no writes | Rejects front matter that is missing, unreadable, disagrees with the file name or the directory, or repeats an id, and a name with no file behind it. Reports a file nothing names as a gap, and `--strict` exits nonzero on one |
| `narrative_entity.py --series DIR add KIND ID [--name] [--character] [--phase]`, `rename OLD NEW`, `remove ID [--force]` | A series directory | Writes, renames or removes one entity file with its front matter. `add persona` starts from the full installed persona form. `rename` rewrites every reference, including the scene plots that happen there, and drops the approval of any plot whose content it changed | Refuses an id that is not an id, a kind and a character that do not go together, an id already in use, and removing something still named unless `--force` |
| `validate_project.py PROJECT` | Existing project directory | JSON report on stdout; no writes | Rejects missing files/directories, incomplete manifest data, invalid managed artifacts, type-less JSON under `state/`, `shots/` or `narrative/`, series mismatch, a text file that is not UTF-8, and forbidden punctuation in the files this suite defines. Reports as warnings a narrative still carrying what initialization wrote and a character naming a persona document that is not there. The user's own writing is not bound by the punctuation rule, which is why the prose under `narrative/personas/`, `narrative/world/` and `narrative/glossary/` is exempt, and media is not opened as text |

### Create and inspect a series

Choose a new directory for `PROJECT`. These commands create the scaffold and a production line, add a place and inspect the resulting records. Initial narrative gaps remain authoring work; scaffolding is not approval.

<!-- executable-example: project-start -->
```text
python scripts/init_project.py --out PROJECT --series-id SERIES-01 --title "Series 01"
python scripts/init_line.py --project PROJECT --line E02-M
python scripts/narrative_entity.py --series PROJECT add location station --name "Station"
python scripts/validate_project.py PROJECT
python scripts/narrative_coverage.py PROJECT
python scripts/narrative_index.py PROJECT
python scripts/session_entry_points.py --project PROJECT --next
```
<!-- end-example: project-start -->

After writing the narrative and scene plot, inspect their content and approval hashes:

```text
python scripts/narrative.py PROJECT/narrative/narrative.json --content-sha256
python scripts/scene_plot.py PROJECT/narrative/scenes/sc01-plot.json --content-sha256
```

### Prepare a submission

Create the submission document and supply the selected service's configuration before using these commands. Inspect the printed request and gate findings. Sending is a separate decision requiring confirmation of that exact request.

```text
python scripts/service_profile.py SERVICE --profiles PROJECT/service-profiles.json
python scripts/dispatch.py PROJECT/submission.json --service-profiles PROJECT/service-profiles.json
```

For a live send, first prepare the production run and record approval for its exact submission. Pass `--production-run RUN_ID --authorization RECEIPT_SHA --actor ACTOR --outputs COUNT --cost-bound COST_BOUND --currency CURRENCY --send` to the dispatch command. These are actual run and authorization values; confirmation or `--send` alone is insufficient. For vocabulary assistance while composing the text:

```text
python scripts/vocabulary.py search "focus lines"
python scripts/vocabulary.py read PROJECT/prompt.txt --negative PROJECT/negative.txt
python scripts/vocabulary.py check PROJECT/prompt.txt
```

Use `observe_schema.py TARGET SERVICE SCHEMA_FILE --source SOURCE` when recording a parameter schema for an offering. It updates target evidence; it is not part of project initialization.

## Submission gate

Beside its refusals the gate reports advisories it cannot settle: a submission that declares `"text_form": "tags"` has its tags looked up in the prompt vocabulary and the unknown ones listed; a video submission has its bracketed camera commands compared with the profile's command list. Both are reported as unmeasured, never refused.

`submission_gate.py` reads one submission document and the target profile it
names, and refuses what can be proved wrong before anything is generated. It is
the last command before a run, and it is described in full in
[`references/prompt-composition.md`](../references/prompt-composition.md) section
18, where each rule carries the ID the finding cites.

| Argument | Meaning |
|---|---|
| `<submission.json>` | The submission document: `submission_id`, `target`, `text`, `inputs`, `obligations`. |
| `--profiles DIR` | Where the target profiles live. Defaults to `protocols/target/profiles` inside the suite. |
| `--root DIR` | Root for relative input paths. Defaults to the directory holding the submission, so a submission and its media travel together. |
| `--json` | Print the report and nothing else. |

Exit code `1` means refused, `0` means admitted, and `2` means the submission
could not be read. An admitted submission is not an approved one: the report is
evidence for the user's decision to send, and the run is confirmed with them
before anything is spent.

Each input may name the `request_key` it occupies on the target. Where it does
not and the profile exposes more than one mode that could hold it, the ambiguity
is reported rather than charged as a conflict.

The resolution rule reads dimensions from a still image header, in PNG, JPEG,
GIF, BMP, WebP or TIFF. The floor it compares against is declared, not assumed: a
target profile may record `identity_reference.minimum_shorter_side`, a submission
may state `obligations.identity_reference_minimum_shorter_side`, and where
neither speaks the suite's default applies. A profile floor is the surface's, so
a submission raises it rather than lowering it. Every refusal names the number and
which of the three set it.

```text
python scripts/submission_gate.py PROJECT/shots/SC01-SH01.submission.json --json
```

## Resource selection and service configuration

The suite ships `assets/resources/prompt-vocabulary.json`, deterministically extracted from its own cinematic lexicon. It describes directing terms; a term's presence is not proof of a model's training or accepted syntax. `build_resources.py [--check]` regenerates or verifies it.

`resource_files.py` resolves an explicit file first, then the named resource environment variable, then an explicit `SERIES_RESOURCES` configuration, then the suite's bundled catalog. A configuration contains `{"resources": {"prompt-vocabulary": "terms.json", "service-profiles": "services.json"}}`; paths resolve inside its directory. An explicitly selected missing or invalid file is an error. Use a resource key to select the data required by the operation.

`service_profile.py SERVICE --profiles PROJECT/service-profiles.json` reads project-supplied service data. `dispatch.py SPEC --service-profiles PROJECT/service-profiles.json` uses the same source. `SERVICE_PROFILES_PATH` is the explicit environment alternative. The service template under `assets/project-templates/` is empty: fill the chosen service's documented endpoint, authentication and operation fields from current evidence. No credentials or service availability are assumed. Dispatch stays dry-run by default. Live submission requires the prepared production run, recorded exact submit authorization, actor, output count, cost bound and currency, as well as `--send`. The observation date is reported, not silently refreshed.

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

Character State Schema currently enforces declared path, value type, and allowed persistence. Nonempty `state_machines` are rejected until the protocol defines explicit path and event-trigger bindings.

Example world resolution:

```text
python scripts/state_protocol.py resolve-world --base-state PROJECT/world-base.json --events PROJECT/state/events.jsonl --character-state-schema PROJECT/state/character-C01.schema.json --timeline main --scene-context-id SCENE-20 --story-order 20 --story-time story:20 --snapshot-id WORLD-main-20 --out PROJECT/state/snapshots/world-20.json
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

`target_protocol.py` reads the durable per-model surface facts under `protocols/target/profiles`. A profile records what one exact model on one exact host accepts and how it wants to be addressed, separately from what any project decided to send it.

| Subcommand | Inputs | Output and side effects | Failure boundary |
|---|---|---|---|
| `validate` | One target profile | JSON report; no writes | Schema, cross-invariant, or canonical hash failure |
| `seal` | One profile and optional `--out` | Writes the resealed profile, or replaces the input when `--out` is omitted | Sealed result is invalid |
| `validate-catalog` | The profile directory and manifest | Aggregate report; no writes | A listed profile is missing, an unlisted profile is present, a profile is invalid, or a `target_id` or `model_identifier` repeats |

`validate_target_protocol.py` runs `validate-catalog` and is the entry point `validate_skill.py` calls.

Example:

```text
python scripts/target_protocol.py seal protocols/target/profiles/minimax-h3.json
python scripts/validate_target_protocol.py
```

`seal` is an intentional write operation and is the supported way to reseal a profile after editing its evidence. Every content change requires it, because `profile_sha256` covers the canonical profile content.

A profile carries evidence with a check date and sources, documented controls, `run_observations` bound to preserved output, and `unknowns`. Record a fact you have not confirmed for this exact host as an unknown with a matching `evidence.recheck_when` trigger rather than as a declared value.

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
| `build_example.py [--check]` | Without `--check`, regenerates the canonical example. With it, performs a read-only byte comparison. |
| `build_flat.py [--check] [--stdout]` | Regenerates the flat adapter unless `--check` or `--stdout` is selected. |
| `build_host_packages.py [--check]` | Regenerates the host specific files from `[hosts]` in the manifest. The repository is laid out as a plugin, so these sit at the repository root beside this suite: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, `hooks/hooks.json`, `AGENTS.md` and `CLAUDE.md`, plus `agents/openai.yaml` inside the suite. With `--check`, regenerates into a temporary directory and compares. A tree that does not carry the templates under `hosts/` reports that the question does not apply rather than passing in silence. |
| `build_host_packages_smoke_test.py` | Builds a repository in a temporary directory by generating into it, damages one thing, and requires the matching refusal: a missing template or hook source, a generated file edited or deleted, an undeclared `kind`, hook events at the top level, and a template that renders to invalid JSON. One case damages nothing and must be admitted. |
| `host_manifest_smoke_test.py` | Builds a repository in a temporary directory for each host rule, damages one thing, and requires the matching refusal. One case damages nothing and must be admitted. |
| `validate_host_manifests.py [--json]` | Read-only. Checks the generated host manifests against shapes that cost a hook or a plugin: a plugin manifest that names the standard hooks file the host already loads, a hooks file whose events sit at the top level, a hook command pointing at a file the package does not carry, a marketplace source that is not a directory here, a marketplace naming a different plugin, and a version that differs between the manifests, the guides and the package. |
| `run_gallery.py PROJECT [--out FILE]` | Writes `runs/gallery.html` and `runs/gallery.json`: every run record under `runs/` in the order it happened, each beside the text as sent, the model, every setting, the media by role, the seed and file of each result, or the refusal. `init_project.py` writes them at the start and `dispatch.py` rewrites them after every run, so they are current without anyone asking; run this by hand only for a record edited by hand. Built from the records and nothing else, so a result that is not in it was not sent through `dispatch.py`, and `validate_project.py` refuses a gallery that does not match the records. `--self-test` exercises it on a temporary project. |
| `work_ledger.py --project DIR begin|step|note|block|finish|abandon|show` | Writes the open task to `work/current.json` (goal, steps, which are done, what is next, what it waits on) and appends every change to `work/ledger.jsonl`. Open a task before work that takes more than one step, mark each step as it is done, finish or abandon at the end. `session_entry_points.py` prints the open task first and `validate_project.py` checks the trail. |
| `session_entry_points.py [--project DIR] [--compare DIR] [--next]` | Read-only. Prints the version of the copy it runs from, the entry points, the unsettled roles of a project, and the next actions in the order the layers depend on each other. `--next` prints only those actions, one per line. `--compare` reports whether another copy of the suite is behind this one. |
| `protocol_contract_smoke_test.py` | Exercises public artifacts using bundled fixtures and explicit data bundles. |
| `project_workflow_smoke_test.py` | Exercises resource selection, explicit protocol exchange and fresh-workspace operation. |
| `build_resources.py [--check]` | Rebuilds or verifies the bundled cinematic vocabulary from its source document. |
| `validate_state_protocol.py` | Read-only protocol and fixture validation. |
| `validate_viewpoint_protocol.py` | Read-only protocol and fixture validation. |
| `validate_integration.py` | Read-only bundled declarations and explicitly supplied public payload validation. |
| `refusal_coverage.py <reader> <suite>...` | Read-only. Lists every refusal a reader can make that no case in the named suites asserts a fragment of. A refusal nothing names can be deleted with every suite still green, which is the one failure a suite cannot report about itself. `validate_skill.py` runs it over `narrative.py` and `scene_plot.py`. |
| `seal_contract.py [--check]` | Seals `protocols/narrative/README.md` against the files it publishes: writes the digest of the prose into `narrative.py`, then republishes the hash of every file the contract's block lists. Run it after editing the contract, a published reader, or the corpus; `--check` says whether sealing would move anything and writes nothing. |
| `narrative_corpus.py [--check]` | Writes `narrative_corpus.json`: the documents in the case tables of the narrative and scene plot suites, each with the verdict the contract requires of it, so that an implementation elsewhere is checked against the verdicts and not against a resemblance to the readers. `--check` refuses a corpus that is not what those tables write, or a verdict in it the readers here do not reach. `validate_skill.py` runs the check. |
| `validate_test_cases.py` | Executes and classifies the numbered regression catalog. |
| `validate_knowledge_integrity.py` | Read-only knowledge and template integrity validation. |
| `submission_gate_smoke_test.py` | Runs every shipped submission fixture, the exclusivity and resolution-floor cases against profiles written by the test, and the image header readers against generated files. No writes outside a temporary directory. |
| `scene_plot_smoke_test.py` | Changes one thing in a scene plot that answers the contract and requires the message that rule is for. The gate fixtures settle that a bad plot stops a submission; this settles which rule stopped it. |
| `narrative_index_smoke_test.py` | Builds a project per case, changes one thing, and requires the message that rule is for. Exercises the entity commands through their argument parsers, because an option that stops parsing is a command nobody can run. |
| `narrative_smoke_test.py` | Changes one thing in a narrative that answers the contract and requires the matching refusal, and builds projects in a temporary directory to compare a narrative against the scene plots meant to cover it. |
| `asset_registry_smoke_test.py` | Runs the registry reader over minimal registries that each declare whether an error, a warning, or neither is required. Read-only. |
| `validate_skill.py` | Aggregate repository validation plus temporary project creation outside the package. |
| `build_release.py` | Requires a Git worktree, checks generated files, copies only tracked manifest-included members into a temporary stage, validates stage and extraction, then writes ZIP, SHA-256, and reports. |

The generated members are rebuilt before they are checked, and some of them are
themselves release members, so the order matters. Run from the repository root:

```text
python skills/series-continuity-director/scripts/build_example.py
python skills/series-continuity-director/scripts/build_flat.py
python skills/series-continuity-director/scripts/build_host_packages.py
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
| `dependencies.py --scope core` or `--scope media` | Report declared runtime and optional media requirements without installation | Missing dependency is not a quality pass |
| `production_direction_smoke_test.py` | Exercise direction, authority and actual media locators | Synthetic fixtures, not artistic proof |
| `production_examples_smoke_test.py` | Run the documented production and timed examples in separate temporary projects | Actual CLI outputs, observation and completion |
| `authorial_intent_audit.py`, `persona_expression_audit.py` | Read-only drafting and link evidence | See `references/narrative-authoring.md`; no artistic scoring |

## Reusable authoring and observed execution

- `scene_persona.py`: prepare exact scene definitions and applications; verify whole originals; output JSON and Markdown.
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
