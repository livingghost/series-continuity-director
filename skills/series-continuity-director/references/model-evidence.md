# Model request evidence

The operator chooses the target, source documents, candidate settings, and permitted trial scope.
The importer preserves acquired bytes and verifies their declared target before publishing evidence.

## 1. Import source documents

`observe_schema.py schema` records a target's own schema and its acquisition evidence.
Supply `--root`, the exact service, model, operation, and the acquisition document.
`--pointer` selects the schema inside the response using a JSON Pointer.
A local envelope overlay has its own source and remains separate from the acquired schema.
`--profiles DIR` writes the project's copy of the profile, its offering pointing at the published schema, and leaves the suite's profiles untouched.

`observe_schema.py reference` preserves the source model's identity.
The selected relationship document explains why the operator considered that source.
Its schema remains reference material rather than an observation of the execution target.

Select the unchanged public target profile with `--profile`.
`--out-dir` publishes a new project-local evidence catalog and its complete witnesses.
The catalog records schema, reference, and trial evidence in separate fields.
The public target profile keeps its original content and protocol hash.
Select the catalog's contract and evidence paths when building local request-validation inputs.

## 2. Attach an existing trial

`observe_schema.py attach-probe` reads the selected `--run` and its saved request, authorization, transport trace, and output bytes.
The importer performs no network call or reservation.
A completed trial can produce an observed profile for that exact parameter tuple and input form.
Acceptance by a service alone records acceptance, not completed output acquisition.

A profile retains fixed sampling, seed, geometry, output count, and media roles and dimensions.
New content receives a new request hash and review even when the fixed profile applies.
A changed fixed parameter needs an explicit new bounded trial or a valid target schema.
The operator's scope and stop assessments govern permission independently of parameter evidence.

## 3. Compare recorded candidates

Use `production_workflow.py draft-variation` with the run, exact candidate receipt, and an explicit field change map.
The compiler's declared fields identify parameters, content, and media; the map supplies their new values.
The new draft retains unchanged witnesses, production identity, and the source of any copied reading application.
It lists changed dependencies and the new reviews, validation, or authority required.
Follow its `build-inputs` action before preparing the next execution.
Drafting changes no candidate status and consumes no authority.

See the [synthetic model evidence example](../examples/model-evidence/README.md) for commands and recorded output.
