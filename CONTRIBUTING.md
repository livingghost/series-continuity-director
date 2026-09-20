# Contributing

Contributions must preserve the suite's evidence, ownership, continuity, and packaging boundaries.

## Contribution standard

A new term, distinction, artifact, field, or workflow belongs in the runtime only when it changes at least one concrete production result:

- media that is created, inspected, submitted, edited, or adopted;
- the real target control or request key that receives it;
- exact submitted field text;
- shot structure, camera geometry, or viewpoint transition;
- another generation, audio, edit, or post-production route;
- acceptance evidence, state resolution, or continuity review.

When two labels produce the same media, controls, text, post path, and review, merge them. Keep the directing knowledge and remove the redundant label.

## Product release version

The product release uses UTC CalVer, `YYYY.MM.DD.N`, as declared in [package-manifest.toml](package-manifest.toml). `N` begins at 1 on a new UTC date and advances for an additional release on that date. Do not reuse a published identifier for different bytes.

Preserve the existing dated entries in [CHANGELOG.md](CHANGELOG.md), and prepend a current entry in `## [YYYY.MM.DD.N] - YYYY-MM-DD` form. The explicit date must match the CalVer date. Generated host plugin metadata derives its release from the package manifest. The skill trigger and runtime artifacts do not need duplicate product numbers.

Run `python skills/series-continuity-director/scripts/release_contract.py` and `python skills/series-continuity-director/scripts/release_management_smoke_test.py`. CI, source validation, and extracted release checks enforce the same identity. Publication also verifies `--tag` against `v` plus the declared CalVer.

Do not add independent version numbers to internal schemas, protocols, templates, project state files, examples, manifests, or validation reports. Internal artifacts are identified by `artifact_type`, validated structurally against the schema files shipped in the same product release, and sealed with their content hashes where required.

The `$schema` URI inside JSON Schema files is retained because it selects the external JSON Schema dialect used by validation. It is not a Series Continuity Director release or protocol version.

Do not add compatibility aliases for removed internal version fields or versioned protocol directory names. Change the current structure and its validators together in one product release.

New internal artifact IDs must be immutable semantic identifiers and must not encode revision counters such as `-v1`. Use content hashes, derivation records, effective ranges, and `supersedes` pointers to express lineage. External product or API versions, runtime dependency versions, and preserved historical run labels may remain only where they identify actual evidence or an execution requirement; they are not internal format versions.



## Protocol changes

Update an artifact's schema, reader, templates and examples together. Rebuild its content commitments and test both valid data and concrete validation failures. The interchange declaration lists supported artifact types and required and optional features. Reject an unknown required feature; preserve an unknown optional feature without claiming to interpret it.

## Record responsibilities

Maintain narrative, persona, world and visual design alongside the scene and shot plans, state history, references, target bindings, exact submissions and accepted results. These records establish different facts:

- Identity contracts preserve enduring design; events and processes establish variable state.
- Candidate manifests identify results; adoption records select them for a role and effective range.
- Snapshots and projections derive from approved history rather than replacing it.
- Observations establish only what the inspected media and operation show. Record technical properties, finished boundary frames, actual uses and usage restrictions with their evidence.

Use the ownership map in [State and Trust](skills/series-continuity-director/references/state-and-trust.md) when adding fields or changing write-back. A generated result requires explicit acceptance before becoming canon.

## Viewpoint and camera changes

Keep camera ownership, a shot's knowledge scope, the scene's narrative focalization, point of audition, shot grammar, state, and knowledge visibility separate. The shot-level scope and the scene-level focalization are two closed lists that share no value; do not write one where the other belongs.

Choose camera ownership and knowledge scope explicitly when a camera is relevant; no viewpoint family is implicit. A viewpoint change must have a concrete function and an explicit transition record. Preserve axis, screen direction, eyelines, matching action, prop ownership, state visibility, and landing geometry.

Do not turn the first-person profile into a hidden product default. Do not let an external camera reveal knowledge that the selected focalization does not permit.

## State and continuity changes

State changes are authored as events, not as silent snapshot edits.

- Record story time, production record time, and disclosure time separately when they differ.
- Require evidence for approved events.
- Use atomic events for cross-entity transfers.
- Preserve old assets and historical state for flashbacks and alternate branches.
- Keep planned state, approved state, shot-visible projection, and observed render state distinct.
- Do not infer age, culture, injury, relationship behavior, or environment response beyond approved rules.

## Knowledge preservation

Do not replace a detailed production rule, paired example, field set, risk tier, or template with a shorter overview merely because the overview contains the same topic. The missing detail changes what an agent can decide when evidence is incomplete.

When consolidating references:

- identify which document owns the topic;
- preserve concrete examples, fields, conditions, exceptions, and fallback paths;
- remove actual duplication without deleting the more specific treatment;
- adapt first-person-only or old-product assumptions to the current third-person-primary suite rather than discarding the underlying production knowledge;
- update `skills/series-continuity-director/scripts/validate_knowledge_integrity.py` when restored knowledge becomes a release invariant;
- keep human editorial judgment separate from brittle automated heuristics.

A reduction in file size or word count is not evidence of improvement. The criterion is whether the resulting artifact still supports the same concrete production decisions.

A shorter paragraph that leaves an agent to reconstruct removed context from general knowledge is a regression. Preserve concrete operator actions, model-facing consequences, review evidence, exceptions, and failure modes.

## Documentation

Run `python skills/series-continuity-director/scripts/readme_smoke_test.py` after changing user-facing examples. It executes the marked offline commands in temporary directories and verifies outputs and source-change behavior; live-send examples are checked without contacting a service. It is not a prose-quality or artistic assessment.

README content is for users and operators. Put contributor-only release, authoring, packaging, and governance rules in this file.

Use Markdown links for repository files and directories. Keep links relative and inside the package. Run the link validator before release.

Write in direct production language. Preserve uncertainty and evidence boundaries. Do not claim generated results that are not included and inspectable.

Use ASCII punctuation everywhere; the validator refuses em dashes and en dashes.

The writing rules in the repository guide apply here and to every reference, template and changelog entry:

- Say what a thing does, as an action: "the tool records every returned
  variant". State a boundary at most once per section, and as who decides:
  "the author decides when a candidate becomes canon", not "the tool does not
  decide".
- One idea per sentence, about twenty words. Three or more items become a list.
- Prefer the general word. Where a product term must appear because the tools
  use it, put the general phrase beside it at its first use and use the general
  word afterward. Do not add a glossary, a preamble about the document itself,
  or a section that explains why other sections repeat.
- Show a real example next to any claim about output: an actual command's output
  or an actual record, trimmed, and labeled synthetic when it is a fixture.
- Delete a repeated principle and refer to the place it is stated. Longer is
  not safer.
- ASCII punctuation, no em or en dashes, English throughout.
- After changing README.md, run `python skills/series-continuity-director/scripts/readme_smoke_test.py`
  and keep the executable example blocks byte-identical unless the commands changed.


## Repository layout

Two roots exist and they are not the same. The repository owns `README.md`,
`CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE` and [package-manifest.toml](package-manifest.toml).
The suite owns `SKILL.md` and the directories beside it, under
[skills/series-continuity-director/](skills/series-continuity-director/). Both lists are declared in
[scripts/tree_layout.py](skills/series-continuity-director/scripts/tree_layout.py), and
`validate_skill.py` compares the tree against that declaration rather than against whatever it
finds, so a declared file that moved is an error instead of a new definition of where things go.

Everything at the repository root except the source directories is generated from `[hosts]` in the
package manifest. Edit the table and the templates under `hosts/`; never edit a generated file,
because the next build overwrites it.
[scripts/build_host_packages.py](skills/series-continuity-director/scripts/build_host_packages.py)
rewrites them, and `--check` proves what is on disk still matches.

## Build and validation

Use your Python interpreter command in the examples. Replace `PROJECT` with a new directory for the validation project.

Before proposing a release, regenerate the generated members and run the
aggregate check. The first three write files that the fourth compares, so the
order matters, and `validate_skill.py` runs every protocol validator, the host
manifest checks, and the smoke tests:

```text
python skills/series-continuity-director/scripts/build_flat.py
python skills/series-continuity-director/scripts/build_example.py
python skills/series-continuity-director/scripts/build_host_packages.py
python skills/series-continuity-director/scripts/validate_skill.py
```

Initialize and validate a temporary project when changing public project interfaces:

```text
python skills/series-continuity-director/scripts/init_project.py  --out PROJECT  --series-id VALIDATION-SERIES  --title "Validation Series"
python skills/series-continuity-director/scripts/validate_project.py PROJECT
```

Build the release with [scripts/build_release.py](skills/series-continuity-director/scripts/build_release.py). The release process must:

1. reject stale generated adapters before staging;
2. create a clean stage from Git-tracked files selected by the release manifest;
3. run all checks on the stage;
4. build a deterministic ZIP;
5. extract it into a fresh directory;
6. rerun all checks on the extracted copy;
7. verify archive structure, forbidden files, and SHA-256.

Untracked and ignored files under an included directory are reported but never packaged. Release builds require a Git worktree; an extracted source directory is validated as an archive boundary, not used as a new release source.

## Pull request description

Describe:

1. the concrete production problem;
2. the observable before and after difference;
3. the affected media, field, operation, shot, state, or review path;
4. the evidence level of target-specific claims;
5. the tests and examples added or updated;
6. the complete validation performed.
