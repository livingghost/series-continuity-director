# Target Guidance and Deliberate Execution Choices

A target profile states model facts. An offering states how one service exposes
that model. Target guidance recommends choices within those facts. It grants no
capability, authority, or guarantee of artistic quality.

## 1. Inspect the selected target

Read this procedure before choosing a model, operation, settings, or recommended
wording. Use the same sources throughout input construction and submission.

```bash
python scripts/target_protocol.py inspect --target TARGET --profiles PROJECT/profiles --guidance PROJECT/guidance.json --service SERVICE --operation OPERATION --output-kind image --purpose key-image --visual-language drawn
python scripts/target_protocol.py validate-guidance PROJECT/guidance.json
python scripts/execution_routes.py read media --root PROJECT --target TARGET --profiles PROJECT/profiles --guidance PROJECT/guidance.json --service SERVICE --operation OPERATION --output-kind image --purpose key-image --visual-language drawn
```

Replace uppercase paths and identifiers with the selected definitions. These
commands inspect files and print information; they do not send a request.
`--profiles` and `--guidance` can repeat. Profile directories are searched in
order. Equal target IDs within one directory are ambiguous and are refused.
The selected path and its content hash appear in the result. A completed
submission uses its pinned definition rather than searching the catalog again.

Without explicit guidance files, the resource role `target-guidance` is resolved
through the declared `SERIES_RESOURCES` configuration and the suite catalog.
The shipped collection is empty: no observed acceptance is advertised as a
quality recommendation. External files are read as data, never executed.

A complete card identifies the target, offering, operation, applicability
context, prompt contract, applicable advice, evidence, and limitations. A card
without complete context shows available records without claiming applicability.
`guidance_status: not-registered-for-context` means no matching advice, not an unusable model.
The profile's input modes and the service's request schema remain authoritative.

`production_workflow.py inspect-inputs` accepts the same target-selection
arguments. `submission_draft.py new` returns `target_info` for its selected
model; use `--guidance-purpose` for the purpose and `--guidance` for each file.
The completed input build and dispatch preview show the pinned card and actual
setting choices together. Reading a card alone does not authorize sending.

A complete synthetic [example](../examples/target-guidance/README.md) includes a
model definition, guidance, execution plan and executable inspection commands.

## 2. Author advice with a bounded claim

Use `schemas/authoring/target-guidance.schema.json`. A file contains one record
or a collection shaped as `{"guidance": [...]}`. Each record declares:

- `artifact_type: target-guidance`, an immutable semantic `id`, and a label;
- `applies_to`: target ID, optional service/model identifier/operation, output
  kinds, exact input-mode set when supplied, purposes, and visual selectors;
- `prompt_structure`: guidance on composition rather than text injected later;
- `entries`: parameter choices or text fragments, their reasons and evidence;
- `limits`: untested conditions and the bounds of reuse.

An empty selector list imposes no constraint on that axis. A null service or
operation is unrestricted. Input modes are different: null is unrestricted,
whereas an empty list applies to text-only input. Nonempty visual selectors
must all occur in the explicitly selected context. Purpose and visual selectors
are authored identifiers, not keywords extracted from a prompt.

A parameter entry declares the exact dotted request `field` and a `proposed`
set of JSON values or numerical range. It does not choose a midpoint. A text
entry declares `channel` (`positive` or `negative`), exact `text`, its `role`,
and whether rewording is permitted. `conflicts_with` names incompatible entries
within the same record. Distinct applicable records may coexist, but their IDs
must be unique. Resolve substantive contradictions rather than averaging them.

Each evidence item distinguishes `documented-recommendation`, `observed-result`,
`author-preference`, and `hypothesis`, with a reference and applicability scope.
An observation retains the exact target, operation, inputs, settings, wording,
post-processing and judged property at its source. An accepted API request is
not evidence for superior drawing, acting, motion, or sound.

## 3. Resolve values and text before constructing the request

The existing `build-inputs` validation selection includes `target_profile`,
`service_profiles`, `guidance` (a list), and an `execution` plan, alongside its
schema or bounded-probe evidence. Copy chosen external definitions into the
project as preserved data before preparing work. Project paths and `@skill/`
paths become byte snapshots through the ordinary input evidence reader.
No private installation is searched and no separate approval ledger is created.

The plan follows `schemas/authoring/execution-choices.schema.json`:

```json
{
  "context": {"output_kind": "text", "input_modes": [], "purpose": "wording-study", "visual_language": []},
  "settings": [],
  "recommendations": [],
  "segments": {"positive": [], "negative": []}
}
```

This is a structure example, not a complete request. Populate the settings for
the actual service, and cover the complete authored text with contiguous spans.
The general plan deliberately invents no sampler, resolution, seed, or duration.

Each setting has `field`, `state`, `value`, `reason`, and `recommendation`.
States have distinct effects:

| State | Request effect |
|---|---|
| `explicit` | Send the author's exact JSON value. |
| `recommended` | Send a chosen permitted value and cite the adopted entry. |
| `offering` | Send an explicitly chosen `as_written` value from the offering. |
| `not-applicable` | Send no key; record why this operation does not use it. |
| `not-exposed` | Send no key; record the unavailable control and its limitation. |
| `provider-managed` | Intentionally omit the key and state what is delegated. |

Omitted states carry `value: null`, not an API null. Explicit JSON null may be
sent only if the target schema accepts it. Valid `false`, `0`, and empty arrays
remain values. Dotted paths cannot duplicate or overlap. Existing authored
values cannot be silently replaced by the plan.

An execution policy's `controls` array declares important fields, their
`availability`, whether provider management is allowed, and the evidence reason.
Each declared control needs a decision. This is operation-specific: still-image
samplers are not required of text or audio models. Where a service publishes no
seed or frame-rate control, report that limitation rather than inventing a value.
Any offering `as_written` field also requires a deliberate choice. The transport
never supplies an artistic value after these choices have been resolved.

Record adoption or rejection and a reason for every applicable advice entry.
An adopted parameter must reach a setting. An adopted text fragment must reach
the named channel. Rejected advice is not injected. Each text span contains
`start`, `end`, `text`, `recommendation` (null for authored text), and `reason`.
Offsets are character offsets, not byte offsets. Spans cover their full channel
without gaps or overlap. An empty channel has no spans. Rewording records the
selected phrase and its source; it requires the entry's permission. Negative
text is allowed only when the exact offering exposes that channel. Otherwise
write any needed exclusion in the authored positive channel and review meaning.

## 4. Keep the selected values in the existing request chain

`execution_choices.py` resolves the plan during `build-inputs`, which stores the
selected definitions, exact text hashes, settings, and recommendation decisions.
`request_renderer.py` verifies those choices and attributes the actual request
fields and text spans to their sources. The existing request seal includes their
content hash and the scoped visual selection. Unchosen parameter insertion,
model substitution, changed wording, reordered media, and omitted selected
values are refused before sending.

The final preview shows the actual request, target card, setting decisions, and
required rendition review. The reviewer checks meaning and reference influence;
the returned artifact is inspected for visual, temporal, and audio realization.
A mechanical pass proves correspondence, not artistic success.

Choose a new model or operation explicitly when a target is unavailable. Do not
replace it with another tool as an unannounced preview. Changes to definitions,
advice, settings, text, or visual application return through existing preparation,
request review, and scoped authorization. No default value is a spending grant.

`draft-variation` preserves the original selected definitions and unchanged
choices. A changed value becomes an explicit choice with the variation reason.
Changed text is authored anew, and advice no longer used is recorded as rejected.
The variation map states all changed fields. Do not describe a comparison as
one-variable when other inputs or post-processing also changed.

Generation duration, editing duration, audio generation, and presentation timing
remain different choices. Use the existing timed-production records for intervals,
adjacent shots and observed endpoints. A visual basis change invalidates dependent
preparation through source snapshots; it never rewrites accepted media or canon.

## 5. Failures and verification

Missing decisions, unmatched advice, changed source hashes, wrong operation
controls, undeclared wire fields, incomplete spans, and unresolved visual choices
stop preparation or rendering with the responsible field named. No advice is a
valid state. Missing schema evidence still follows the existing bounded-probe
procedure, never an invented assurance of compatibility.

Run `python scripts/target_guidance_smoke_test.py` for synthetic advice, external
sources, choice resolution, transport trace, and scoped visual failures. The
existing input-model, dispatch, request-contract and variation suites exercise
the connected production path. Tests use synthetic definitions and never a
personal resource collection. They do not make paid generation calls.
