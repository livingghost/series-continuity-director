# Synthetic Target Guidance Example

This directory contains illustrative data, not a service integration. It describes
text about an isolated form; it does not generate a picture. No provider settings
or quality claims are inferred from the synthetic model name.

From the skill directory, inspect its choices:

```bash
python scripts/target_protocol.py validate-guidance examples/target-guidance/guidance.json
python scripts/target_protocol.py inspect --target synthetic-study --profiles examples/target-guidance/profiles --guidance examples/target-guidance/guidance.json --service synthetic-service --operation draw --output-kind text --purpose wording-study
```

The result shows `synthetic-outline-study`, a `detail_level` choice between
`plain` and `layered`, and the positive fragment `Keep a continuous boundary.`.
These are explicitly labeled author preferences for this example. They do not
change the target profile's capability facts.

`execution-plan.json` adopts both entries and records the exact text spans for:

```text
One geometric form. Keep a continuous boundary.
```

Use its shape for `validation.execution` in a production input choices document.
The selected model profile, service data, guidance files and schema acquisition
must be explicit project inputs before `build-inputs`. The fragment enters the
authored text by the stated choice, not through a later automatic prefix.
To reject an entry, record `decision: reject` and remove its use from the text or
setting selection. Resolve a new plan before reviewing another request.

A visual submission additionally selects anchor/register applications in its
production task. This nonvisual example uses no visual requirement. Real API
acceptance and artistic results require their own target evidence and review.
