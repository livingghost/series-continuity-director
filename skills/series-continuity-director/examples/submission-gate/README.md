# Submission contract examples

These synthetic scenarios test declared input contracts before model submission.
Each JSON file includes its expected status and, when applicable, a refusal code.
The `sources/` directory stores the authored scenarios. The builder adds full
reading records, explicit one-off subjects, and public camera/request artifacts.

The scenarios cover every kind of submission:

- shots of `fixtures/scene-plot.json`;
- pages and panels of `fixtures/scene-plot-pages.json`, in `clean-page`,
  `clean-panel`, `page-outside-plot` and `panel-outside-page`;
- a passage illustration of `fixtures/scene-plot-passages.json`, in `clean-passage`;
- assets, which belong to no scene.

`shot-against-page-plot` names a shot of a plot realized as pages, and
`placeholder-unfilled` is a draft with fields nobody filled.

Run from the skill directory:

```sh
python examples/submission-gate/build_example.py
python examples/submission-gate/build_example.py --check
python scripts/submission_gate_smoke_test.py
```

The builder validates every expected result before publishing the generated
files. The smoke test also checks missing evidence, camera correspondence,
literal locks, input channels, image dimensions, and malformed inputs.

Creative requirements remain attached to their source for rendition review.
The author evaluates whether the final content realizes those requirements.
Read the `unmeasured` and `review_requirements` fields alongside the verdict.

For one generated input:

```sh
python scripts/submission_gate.py examples/submission-gate/clean-s03.json --root examples/submission-gate --json
```

The clean scenario is admitted. A changed camera reference receives
`VISUAL_CONTINUITY_INVALID`; a removed reading record receives
`ROUTE_READING_INVALID`. Neither result certifies generated image quality.
