# Source-bound creative alternatives

## 1. Boundary

Read this when comparing possible portrayals, arrangements, narrative directions, continuations, or deliberate holds before producing them. Alternatives are authored plans, never forecasts of what must happen. They live in `creative-options/` inside the project, not in canon or the production receipt chain. Choosing an alternative records only a planning choice. No other installed application, fixed story tradition, subject type, genre or number of alternatives is assumed.

Separate durable intent from current focus. Preserve known facts as inputs, but allow open questions, incompatible candidate interpretations, and explicit uncertainty. An alternative may change nothing, omit an element, repeat a passage, or describe an unpeopled work. Do not force conflict, change, a protagonist, a camera, dialogue, an arc or a timed beat. Never average mutually exclusive alternatives into one plan.

## 2. Author a specification

All source and plan paths are project-relative. Plan files are inspectable UTF-8 text. A source list can be empty for an original work. IDs are local immutable labels, not release counters.

```json
{
  "purpose":"Compare authored approaches without changing accepted work.",
  "intent":{"durable":"Preserve the author's declared effect.","focus":"Resolve only the currently open presentation choice."},
  "sources":[{"id":"brief","path":"brief.txt","role":"authorial intent"}],
  "alternatives":[{
    "id":"approach-a","title":"An authored approach","plan":"plans/approach-a.md",
    "rationale":"Explain the concrete effect, not a generic quality claim.",
    "preserves":["The applicable author anchors."],"changes":[],"uncertainties":["List any unresolved evidence."],
    "trace":[{"source":"brief","locator":"The authored requirement in the source.","target":"The relevant plan passage.","treatment":"hold","reason":"A held condition serves this request."}]
  }]
}
```

The trace's `treatment` is `preserve`, `transform`, `omit`, `repeat`, or `hold`. Locators, targets and reasons explain the actual relationship; the script checks references but cannot prove meaning. No exactly-once coverage requirement is imposed. Use explicit omission or repetition where authored; add a trace only when there is an applicable source. Empty trace and change arrays are valid.

```sh
python scripts/creative_options.py prepare --project WORK --spec options.json
python scripts/creative_options.py status --project WORK --workspace OPTIONS_ID
python scripts/creative_options.py export --project WORK --workspace OPTIONS_ID --out reviews/alternatives
```

Preparation validates all input before publishing a new workspace. It saves the exact spec, every source and every plan by content hash, verifies the same bytes are still present, then publishes the staged directory. `status` compares current source bytes with that snapshot. Export presents all alternatives and staleness without making a choice.

## 3. Record an explicit planning choice

```sh
python scripts/creative_options.py select --project WORK --workspace OPTIONS_ID \
  --alternative approach-a --actor author --reason 'Exact stated reason.' --evidence choice.txt
```

The evidence file must exist and be nonempty. The command preserves those bytes and the reason, stores an immutable choice object, and atomically updates its pointer. The actor label and evidence record do not authenticate consent. Stale sources or plans block selection; prepare a new snapshot against current content instead of silently rebasing. Every declared source and plan remains bound, including unselected alternatives.

The returned plan-object path points to exact preserved plan bytes. To realize it, explicitly use those bytes as a source for a production task with the corresponding direction and execution authority. This command does not edit the narrative, modify state, grant a budget, select a generated take, or accept an event as canon. Production outcomes still require the existing review and adoption boundaries.

## 4. Scope of assurance

Isolation and hash checks establish file handling. They do not prove that an alternative is expressive, feasible, plausible, or preferred by an audience. Keep those judgments and their evidence separate. Source readers and the choice operator must respect the project lock; checks detect ordinary out-of-band edits but do not defend against a malicious concurrent filesystem administrator.

Run `python scripts/creative_options_smoke_test.py`. The cases are constructed correctness tests, not demonstrations of generation quality.
