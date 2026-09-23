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

Start a plot with `draft` rather than by hand. It fills in what the narrative declares: the
chapter, the next free place in it, the arcs the chapter carries with their characters and themes,
the narrative hash and the realization the medium implies. Every other field is a `<fill: ...>`
value, and the reader refuses each one by name until the author's decision replaces it.

```
python <skill>/scripts/scene_plot.py draft --project <project> --scene-id <scene-id> --chapter <chapter-id>
python <skill>/scripts/scene_plot.py narrative/scenes/<scene-id>-plot.json
python <skill>/scripts/scene_plot.py approve narrative/scenes/<scene-id>-plot.json --by "<name>"
python <skill>/scripts/scene_plot.py behind --project <project>
```

The second lists what is still open. The third records an approval the author gave: it binds the
plot to the current narrative, writes the approval block, and refuses a plot that fails its checks
or names an id the narrative does not declare. The fourth lists every plot written against an
earlier narrative, with the recorded and current hashes; each one needs the author's approval again.

A shot submission names its scene plot, and the gate refuses a submission whose plot is:

- missing;
- unapproved;
- edited after approval;
- lacking the shot being submitted.
