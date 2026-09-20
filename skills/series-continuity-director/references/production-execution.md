# Production execution and bounded authority

The production task owns purpose, applied evidence, selected realization,
verification criteria and delivery. Preparation snapshots those inputs and the
actual runtime/reading closure. Handoff transfers an exact consumer, capture
registers actual bytes, review observes a specific candidate, selection names
that candidate and review, and completion binds the selected state. All steps
use the **same production receipt chain**, not a separate evaluation ledger.
See `production-direction.md` for decisions and evidence; the executable forms
are in `schemas/authoring/production-*.schema.json`.

## 1. Working path

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

Drafts deliberately leave substantive review/authority/selection fields empty.
They are not approvals. `status` and `resume` verify inputs and recorded files;
`impact` additionally locates changed inputs, recorded artifacts and affected
declared decisions. Source changes require re-reading and preparing, not an
in-place rewrite of receipt history. Captured artifacts are not automatically
selected, and delivery selection never implicitly adopts canonical design.

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

## 5. Bounded model submission and interruption

Include the submission JSON, primary text, service-profile file and all input media as task sources (the primary text also occupies `delivery.path`). Choose a `dispatcher` handoff. The exact primary text in the built request must equal that prepared rendition; request options cannot silently replace it. A service record is data, not permission. The installed target profiles are pinned with the Skill; selected external profiles must be pinned project sources as well.

```
python scripts/dispatch.py project/submission.json --root project --service-profiles project/services.json --send --production-run RUN --authorization RECEIPT --actor ACTOR --outputs 1 --cost-bound 0 --currency none
python scripts/production_dispatch.py --root project --run RUN
python scripts/production_dispatch.py --root project --run RUN --poll
```

Set a real agreed cost bound and currency for paid operations; zero/none is not a claim that an external service is free. The permission checker enforces the declared reservation, not a provider's eventual invoice. The selected transport must describe the built request's text and output count. The bundled transport requires explicit `parameters.numberResults`, matching `--outputs`; another transport implements its own request semantics.

The grant is reserved and a claim committed before any upload. Each upload identifier, exact request, response, poll response, and downloaded file is durably recorded. Files are uploaded from immutable prepared copies. A claim cannot be sent again. Recovery only polls existing task IDs or retrieves and records known outputs. An exception before a response leaves an uncertain claim that must be reconciled with the provider, not automatically resubmitted. No credential is stored in the journal.

Acquired files become candidates in the same run. Gate admission and successful delivery do not certify direction, acting, or audience response. A changed input prevents later review or completion of that stale preparation; it does not erase the acquired evidence.

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
