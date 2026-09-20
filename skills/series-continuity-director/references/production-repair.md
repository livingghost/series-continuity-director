# Reviewed production changes and retained-output recovery

A failed candidate is evidence rather than a replacement plan. Keep its actual
file, latest review, observations and unconfirmed limits. A failed check
requires a concrete repair proposal or a nonempty unresolved issue; where a real
repair is unknown, record the unresolved issue rather than a repair invented to
fill the form.

## 1. Describe and bound the change

Each proposed repair has a human-readable `scope` and machine-checkable
`targets`. A target names one of:

- `delivery`, `purpose` or `execution`;
- `source:ID`, `criterion:ID` or `decision:ID`;
- a sequence element: `asset:ID`, `cue:ID`, `placement:ID`, `clock:ID`, `sequence:output`, `sequence:boundaries`, `sequence:constraints`, `sequence:story_links` or `sequence:cue_links`;
- `sequence`, for adding or removing the whole sequence.

These are change coordinates rather than artistic categories; author only the
scopes the repair genuinely needs.

Prepare revised authoring files, leaving every recorded candidate, review and
authorization evidence untouched. The read-only comparison reports the actual
changed scopes rather than the labels the caller supplied:

```
python scripts/production_workflow.py revision-intent --root PROJECT --run PARENT --task revised-task.json --candidate CANDIDATE_SHA256 --repair-index 0
python scripts/production_workflow.py revise --root PROJECT --run PARENT --task revised-task.json --candidate CANDIDATE_SHA256 --repair-index 0 --authorization GRANT_SHA256 --actor ACTOR
```

The index is zero-based in the **latest** review of that candidate. The intent
binds:

- parent;
- candidate;
- review;
- proposal;
- actual scopes;
- full revised preparation.

`revise` requires an edit grant covering those scopes and respecting protected
sources, and creates a new run with that parent link. A changed review or an
unrelated criterion/source change is refused. A repeated reservation reuses the
same child, branch and budget.

The child inherits nothing: handoff, candidate, pass, selection and approval
start over. For it:

- re-read the current route;
- hand off;
- realize the changed inputs;
- inspect the actual output;
- select it under current authority.

Retiming, sound, order or asset edits use this path as naturally as direction
changes. The old run's observations and used permissions survive a source
change. Edit-only authority may be recorded against a parent whose project
authoring inputs are being revised; a changed implementation or altered recorded
evidence is still refused.

## 2. Permission across preparations

A permission's accounting identity derives from the supplied principal, actor
and exact approval evidence. Rebinding the same approval to another run of this
task keeps its call, output and cost limits, its revocation and its machine stop
conditions as they were; under the same evidence, scope and limits stay fixed.
A genuinely changed authorization requires actual new approval evidence rather
than an agent-generated document purporting to be consent. This is
consistency/accounting rather than identity authentication.

## 3. Interrupted timed execution

An edit reserves before execution. The built-in timed renderer computes in an
isolated temporary location, verifies its output, then retains the exact MP4
and provenance receipt before publishing them. Recovery publishes only those
retained bytes and records their candidate:

```
python scripts/production_workflow.py recover-action --root PROJECT --run RUN --reservation RESERVATION_SHA256
```

Repeating the same timed render request enters this recovery path and renders
nothing new. When retained bytes are missing, the operation refuses recovery:
retain the claim, inspect the outcome and obtain specific authority for a new
attempt. A changed input, a revoked/expired permission or a conflicting existing
destination blocks stale publication. A successful technical recovery leaves the
review verdict open.

The regression suite is `scripts/production_integrity_smoke_test.py`. The
runnable `examples/production-execution/repair_example.py` retains a synthetic
review, scoped child run and completion; it tests the mechanism rather than
artistic quality.

For repeated failures across recorded candidates, use [Repair Analysis](repair-analysis.md). A hypothesis or a failed review grants nothing by itself: another submission or a canonical change needs its own authority.
