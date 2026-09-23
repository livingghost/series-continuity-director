# Production execution and bounded authority

The production task owns purpose, applied evidence, selected realization,
verification criteria and delivery. Preparation snapshots those inputs and
everything the run depends on: the suite files it executes and the documents its
reading covers. Handoff transfers the exact consumer input, the complete input
the writer or generator receives. Capture registers actual bytes, review
observes a specific candidate, selection names that candidate and review, and
completion binds the selected state. All steps
use the **same production receipt chain**, not a separate evaluation ledger.
See `production-direction.md` for decisions and evidence; the executable forms
are in `schemas/authoring/production-*.schema.json`.

## 1. Working path

### Input assembly

Use [Tactic consultation](tactic-consultation.md) while deciding what to write or revise. The lookup, application source, and authored review questions stay connected to the current task. Input inspection provides the concrete entry action.


`inspect-inputs` shows declared sources, recorded candidates, and required choices.
`draft-inputs` creates an unanswered choices document in a new directory.
The author supplies continuity and acceptance decisions; the operator supplies quotations, applications, and explicit source selections.
`build-inputs` resolves those selections through the existing contract builders.
It derives document hashes, image hashes, adoption selectors, and reference positions from recorded evidence.

Each output directory is published after all required judgments and current evidence validate.
An incomplete selection returns named unresolved fields and preserves existing files.
The original task and source artifacts remain unchanged.
Construction returns formal inputs, their provenance, and arguments for the next operation.
Preparation, final request rendering, review, and authorization follow through their own commands.

Use `--from-run` to name a saved run from the same work task.
Copied reading applications retain their origin and require assessment for the current work.
Choose current visual references and validation evidence explicitly.
The [synthetic input assembly example](../examples/input-assembly/README.md) contains complete commands, choice fields, and actual output.

Begin an ordinary work task. Author `task.json` with its open task ID, an actual
route, sources (ID/path/role/disposition/locator/reason), delivery path and
transport, criteria (ID/strength/text/evidence), and a `direction`. Follow the
route's read dependencies. Prepare, hand off, execute or acquire the actual
artifact, capture, draft and complete its review, then explicitly select it.
An actual current selection and completion are required before a production-
linked work task can finish. Setting all checklist flags alone is insufficient.

```
python scripts/production_workflow.py prepare --root PROJECT --task task.json
python scripts/production_workflow.py handoff --root PROJECT --run RUN --recipient ACTOR --method manual
python scripts/production_workflow.py capture --root PROJECT --run RUN --artifact result.png --note 'How this artifact was acquired'
python scripts/production_workflow.py draft-review --root PROJECT --run RUN --candidate RECEIPT_SHA256 --out review.json
python scripts/production_workflow.py review --root PROJECT --run RUN --file review.json
python scripts/production_workflow.py draft-selection --root PROJECT --run RUN --candidate RECEIPT_SHA256 --out selection.json
python scripts/production_workflow.py select --root PROJECT --run RUN --file selection.json
python scripts/production_workflow.py complete --root PROJECT --run RUN
```

`PROJECT` must be an existing project; a mistyped root returns one JSON error and creates nothing.
An expected failure prints one JSON object with `ok: false` and `error`, and exits 1.
Runs live in `production/` under their UUIDv7 names, beside the task, review and selection templates there.
Every other entry in that folder is ignored, including `desktop.ini`, `Thumbs.db` and `.DS_Store`.

Recorded paths are project-relative POSIX paths, and each names one file on every platform.
The commands refuse a path component that Windows reads as another name:

- a trailing dot or space, as in `hero.png.`;
- a colon, as in `hero.png:ads`, or another character Windows reserves;
- a device name such as `NUL` or `com1.png`.

A project may sit below a symbolic link, such as the macOS `/tmp`.
A symbolic link at the project root or inside the project is refused.
Some volumes refuse hard links, such as FAT32, exFAT and some network shares.
There a new record is created only under a free name and then written, rather than linked in complete.
An interruption can leave that record incomplete, and its hash check then reports it.

Drafts leave substantive review, authority and selection fields for the responsible actor.
`status` and `resume` first verify frozen inputs and the receipt chain.
They then report current dependencies separately from acquired artifacts, reservations and execution evidence.
`impact` locates changed inputs and affected declared decisions.
A changed source retains uncertain submissions and acquired results in the resume report.
The author or delegated selector decides which actual candidate to select and adopt.
See the [synthetic resume example](../examples/resume-recording/README.md) for actual before-and-after reports.

## 2. Delegation is scoped, not an all-automatic flag

```
python scripts/production_workflow.py draft-authorization --root PROJECT --run RUN --out grant.json
python scripts/production_workflow.py authorize --root PROJECT --run RUN --file grant.json
```

The grant is tied to `input_sha256`, an explicit principal, actor, purpose,
permissions, protected sources, stop conditions, optional expiry and an existing
file containing the actual authority evidence. The principal's name and that
file are recorded evidence, **not identity authentication or proof of consent**.
Never manufacture a grant on the user's behalf. An existing explicit delegation
may cover intermediate choices; returning every delegated edit to the user is
not required. When authority or a relevant boundary is unclear, stop that action.

`decide`, `edit`, `submit`, `select` and `adopt` are different operations. Each
permission has exact scopes, maximum calls/outputs, decimal-string maximum cost
and currency. `task` scopes this prepared task only; it is not permission for
other tasks. A decision scope is `decision:ID`, a selection scope is
`candidate:RECEIPT_SHA256`. There are no wildcards. Protected input files stay
immutable in this run. Human-readable stop conditions are for the acting agent;
`halt_on` can additionally enforce `failed-hard-review` or `unresolved-review`.
The grant's expiry and revocation are checked when acting and completing.

Physical executors reserve budget/count/outputs **before** producing or sending.
Failure and uncertainty consume the reservation. The same request identity does
not permit a second side effect. Inspect retained outputs and execution evidence;
do not automatically resend an uncertain service request. Cost bounds must be
supplied from verified capability/pricing information, never invented as zero
for a paid operation. Zero with currency `none` is for genuinely uncharged
processing or a documented service operation, not free spending authority.

`record-choice` records a delegated confirmation of the prepared choice. Changing that
choice requires updated authoring and preparation. The Python APIs `reserve_action()` and
`action_result()` are the execution integration boundary; they do not perform a
provider call themselves. Built-in executors call them directly. An external
executor must honor the returned replay status and limits, persist its result
and observation provenance, and may not label another operation as a manual
capture to bypass authority. Manual capture only records an already obtained
artifact; it does not authorize its creation or any spending.

Selection JSON includes the authorization receipt hash and actor in `selector`.
A grant permitting selection alone cannot adopt design. New grants/revocations
append to the same run. Already completed history is immutable; corrections
create a new work task/run with explicit provenance. Local file ownership and
process access control remain the deployment's responsibility.

## 3. Evidence and uncertainty

Reviews identify file/time regions, observations, verification relationship,
repair choices and unresolved issues. The software rejects impossible ranges,
missing modalities, changed inputs and insufficient declared authority. It does
not make an aesthetic verdict, verify an audience response, or prove that the
acting agent actually inspected the media. Keep these boundaries visible.

`examples/production-execution/run_example.py` is a runnable synthetic integrity
exercise. Its explicit test authority is **not a human approval**. An actual
production request needs its own source evidence, substantive authoring and
observation. Tests of shape, color or duration are not acting-quality tests.

## 4. Sequences and project assets

The task declares `sequence_plan: null` when no timed realization is required,
or the path of the exact declared sequence plan. Its assets are snapshotted.
Use `timed_sequence.py` for an actual time-bearing rough, and the extraction
commands to identify actual review regions. See `timed-production.md`. Screen,
comics, prose and mixed work remain supported; a text/comics request needs no
fictional timeline.

For `registry-adoption`, selection includes `adoption` with `owner_path`,
`asset_id` and `role`. A separate adopt grant is required, and the owned asset
registry must actually accept the selected file and SHA-256 for that role.
Delivery-only selection never changes registry ownership.
The record names the candidate's exact path under `file` or `files and views`.
It gives that file's SHA-256 under `SHA-256`, or on the file's own line under `SHA-256 per file`.
A synthetic record in the template's shape, with its 64-character hash shortened here:

```text
### C01-IDENTITY - approved identity set
- role: C01/identity
- status: accepted
- files and views:
  - `media/c01-identity.png` (front view)
- SHA-256 per file:
  - `media/c01-identity.png`: 5f2c...e81a
```

## 5. Bounded model submission and interruption

Include the submission JSON, primary text, service-profile file and all input media as task sources (the primary text also occupies `delivery.path`). Choose a `dispatcher` handoff. The exact primary text in the built request must equal that prepared rendition; request options cannot silently replace it. A service record is data, not permission. The installed target profiles are pinned with the Skill; selected external profiles must be pinned project sources as well.

```
python scripts/dispatch.py project/media/episodes/E01/prompts/SC01-SH01.submission.json --root project --service-profiles project/service-profiles.json --send --production-run RUN --authorization RECEIPT --actor ACTOR --outputs 1 --cost-bound 0 --currency none
python scripts/production_dispatch.py --root project --run RUN
python scripts/production_dispatch.py --root project --run RUN --poll
```

Set a real agreed cost bound and currency for paid operations; zero/none is not a claim that an external service is free. The permission checker enforces the declared reservation, not a provider's eventual invoice. The service record names its transport with `"transport": "<name>"`, which selects `scripts/transport_<name>.py`. Every transport implements `scripts/transport_contract.py`. Its `compile_request` declares the fields that carry the built request's text and output count, and the declared count must match `--outputs`.

Before the claim, the dispatcher refuses a send that would fail after it:

- a service record that names no valid transport, or a transport that lacks a function the contract requires;
- an `endpoint.base_url` that is not https (plain http is accepted only for `127.0.0.1`, `::1` or `localhost`);
- a missing network deadline. Set `http_timeout_seconds` in the service record or `PRODUCTION_HTTP_TIMEOUT_SECONDS`; the environment variable takes precedence.

The deadline bounds each network wait of a send, poll or download.

The grant is reserved and a claim committed before any upload. Each upload identifier, exact request, response, poll response, and downloaded file is durably recorded. Files are uploaded from immutable prepared copies. A claim cannot be sent again. Recovery only polls existing task IDs or retrieves and records known outputs. An exception before a response leaves an uncertain claim that must be reconciled with the provider, not automatically resubmitted. No credential is stored in the journal.

The credential travels only to the configured endpoint, and a redirect is recorded instead of followed. A transport records these answers with the status and complete body that arrived, as an unknown outcome (`indeterminate`):

- a redirect or a server error;
- a transport failure or an expired deadline;
- a success whose body is not a JSON object.

Recovery reconciles an unknown outcome with the provider and never resends it. A 4xx answer is a refusal. Recovery rebuilds the outputs from the answer and every recorded poll response in order, so an interruption after any recorded response keeps the outputs completed before it. A result URL uses https, or plain http on a loopback host, and each redirect it follows keeps to that rule. Each output streams to disk, and its SHA-256 and size are recorded.

Acquired files become candidates in the same run.
A changed input requires fresh preparation for later review or completion while preserving acquired evidence.
`recover-recording` registers already acquired outputs from immutable dispatch records, including after an input change.
It restores a missing output file from its saved bytes and rejects conflicting bytes at the destination.
Repeated recovery returns the existing candidate. It uses no network call or new execution reservation.

```text
python scripts/production_workflow.py recover-recording --root PROJECT --run RUN
python scripts/production_resume_smoke_test.py
```

Remote result retrieval uses `production_dispatch.py` and remains distinct from local record recovery.
A start boundary alone means the external outcome is unconfirmed; the report separates response, output and charge evidence.
The acting reviewer evaluates direction, acting and the intended audience response from the actual output.

## 6. Scope-aware repairs and durable output recovery

Read [Production Repair](production-repair.md) when a reviewed candidate needs
new production inputs, timing or source selection. `revision-intent` compares
the full preparations; `revise` creates a parent-linked child under an edit grant.
The child inherits no review, selection or permission. Call/output/cost usage,
revocation and machine stop conditions from the same approval persist across
preparations of this work task. Rebinding the input hash is not a budget reset.

Temporal review locators use the actual integer stream index reported by probe,
seconds, and a nonempty interval within that stream's own measured duration.
For example, `{kind: time, stream: 0, unit: seconds, start: 0, end: 0.5}` in JSON
notation names stream 0, not a generic video track. Use quoted JSON keys in a
file. Byte ranges and descriptions of a video do not establish motion; audio
claims require an audio interval. A stream with unknown duration cannot borrow
the container duration as evidence. The cited observations themselves must
support each passed criterion, not merely another uncited observation.

## 7. Inspectable production evidence

After capture or review, a requested inspection export uses the same prepared sources, consumer, receipts and actual bytes through [Evidence Review](evidence-review.md). Exporting a report or study is read-only with respect to production and canon. Continue decisions through the authority-bearing workflow; exported observations never authorize a new action.

### Prepared scene material

During the existing prepare stage, build and verify [Scene Persona](scene-persona.md), then include `scene_materials` and the `scene-persona` feature in the task. The snapshot pins the plan, complete originals and derived documents. The `authoring_materials` in `consumer.json` are for the authoring agent only. They do not automatically enter model-facing text or become performer knowledge. Public artifact selectors require explicit acceptance of their exact content and the lack of current-original verification.

## 8. Contract regression checks

The local synthetic suites exercise recorded evidence and structural contracts.
Run these checks from the skill directory:

- `python scripts/production_inputs_smoke_test.py`
- `python scripts/production_input_model_smoke_test.py`
- `python scripts/route_reading_smoke_test.py`
- `python scripts/visual_continuity_smoke_test.py`
- `python scripts/request_contract_smoke_test.py`
- `python scripts/request_validation_smoke_test.py`
- `python scripts/reservation_lifecycle_smoke_test.py`

Each result measures the exercised contract, separately from creative quality or production approval.

`python scripts/route_reading.py RECORD --root PROJECT` validates an authored reading record against its recorded issuance.
`ROUTE_READING_INVALID` names a missing or inconsistent reading contract.
`VISUAL_CONTINUITY_INVALID` names a missing or inconsistent subject, adoption, or delivered-reference contract.

## 9. Model request workflow checks

The dispatcher preview, attributed evidence import, and candidate variation each have a dedicated regression entry point.
Run `scripts/production_variation_smoke_test.py`, `scripts/schema_observation_smoke_test.py`, `scripts/dispatch_preview_smoke_test.py`.
Their synthetic providers exercise request recording and recovery separately from image quality or author acceptance.

## 10. Exact request preview and variations

A dispatcher preview uses the same renderer as its sending path and reports each transform's source.
Use `--preview-out` to retain the sealed request, declared bindings, and validation report in a new file.
Use `--decision-out` with the prepared run and selected authorization to draft the exact request assessment.
The draft derives request hashes, reference binding IDs, and the authorization's stop conditions.
The actor supplies the scope case, approval source, rendition judgment, and stop assessments.
Pass the completed file as `--request-decision` when sending.
A new request within an explicit existing delegation receives a new exact authorization under the same cumulative budget.
A scope change requires the missing principal decision; request equality alone does not authorize work.

`draft-variation` prepares a new input draft from an exact recorded candidate and a structural field change map.
It preserves the source candidate and prompts reassessment of copied reading applications for the changed work.
The [model evidence workflow](model-evidence.md) describes schema imports and bounded comparison trials.
