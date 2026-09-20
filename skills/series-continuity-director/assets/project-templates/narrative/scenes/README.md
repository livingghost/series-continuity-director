# Scenes

One scene plot per file, as `<scene-id>-plot.json`. A scene plot is where the story meets the
coverage, so it sits with the narrative rather than with the shot artifacts: it is written from
the narrative, and they are written from it.

A scene plot records its:

- purpose;
- setting;
- viewpoint;
- presented beats;
- preserved conditions;
- creative freedoms;
- realization.

It names its chapter, order and source narrative hash. Cast, explicit themes and arc lists can be
empty; an exchange or relationship change is optional. `turn` is optional and can describe
persistence; `state_changes: []` means nothing lasting changes. An observation or held condition
counts as a scene by itself; an invented person or reversal is optional. Declared references,
visible-beat support and source approvals remain enforceable.

A unit is a shot, a page, or a passage, depending on what the series is made of. The narrative's
`medium` decides which, and a scene realized in another kind is refused.

Target and model stay out of the plot; the interface is chosen after the plot is approved. A plot
written once the interface is known takes that interface's limits in as though they were story
decisions, and nothing afterwards can tell the two apart.

```
python <skill>/scripts/scene_plot.py narrative/scenes/<scene-id>-plot.json
python <skill>/scripts/scene_plot.py narrative/scenes/<scene-id>-plot.json --content-sha256
```

The second prints the hash the approval block has to carry. A shot submission names its scene plot,
and the gate refuses a submission whose plot is:

- missing;
- unapproved;
- edited after approval;
- lacking the shot being submitted.
