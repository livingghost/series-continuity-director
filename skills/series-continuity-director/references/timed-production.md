# Time-bearing realization and review

Scene state, presentation order and production order are separate timelines.
`timed-sequence.schema.json` declares clocks with an explicit kind:

- `story`: ordinal only;
- `performance`: elapsed action;
- `source`: each timed asset's own coordinates;
- `edit`: the assembled output.

Elapsed clocks use seconds or integral frames with an explicit rational frame
rate. Intervals are half-open [start, end). A `story_order` is read only as an
ordinal. A non-narrative work may omit story clocks and mappings entirely.

## 1. Plan only the relationships needed

An asset names its actual file, SHA-256, media kind, source clock and proxy
limitations. Stills have no fictitious source duration. A performance cue has
its own span and free-form subjects/action/relations. Record needed overlaps or
dependencies rather than a universal list of looking/reaching/touching phases.
A passive response, held support, collective action, nonhuman change or empty
environment can be a cue. Constraints compare cues only in the same performance
clock.

A placement maps an actual source span, at an explicit playback rate, to an
edit interval. A story link is an optional descriptive correspondence rather
than a conversion from ordinal position to seconds. A cue link declares
realization as depicted, reference or omitted; an omitted cue may lack a
placement but must explain the limit, and the renderer leaves an omitted action
uncertified. Boundaries explain the intended relation between placements and
where it will be checked. Physical continuity, ellipsis and recollection differ:
only physical continuation may require the adopted observed terminal state. A
planned last pose is a plan; the final frame is the measured/accepted one.

## 2. Produce an actual rough

```
python scripts/timed_sequence.py inspect --root PROJECT --plan sequence.json
python scripts/timed_sequence.py render --root PROJECT --run RUN --out rough.mp4 --authorization GRANT_RECEIPT_SHA256 --actor ACTOR
python scripts/timed_sequence.py extract --root PROJECT --source rough.mp4 --sha256 ACTUAL_SHA256 --start 0.5 --out frame.png
python scripts/timed_sequence.py extract --root PROJECT --source rough.mp4 --sha256 ACTUAL_SHA256 --start 0.5 --end 1.0 --out interval.wav
```

The renderer realizes:

- explicit holds;
- clip trims;
- speed changes;
- layer ordering;
- contain/cover/stretch sizing;
- linear start/end movement and opacity;
- audio trim/speed/gain/placement/mixing.

It writes a new MP4 plus a source/command/probe receipt, then adds the real
output as a candidate to the same production run. The task must already be
prepared and handed off, with an edit grant reserved before physical execution.
A reserved request is retried only on explicit request.

The built-in implementation needs FFmpeg/ffprobe, H.264 encoding and, for audio,
AAC. These constraints are the renderer's own rather than the genre's or the
whole Skill's:

- its yuv420p MP4 canvas is even-sized;
- dimensions and frame rate are free of any invented product ceiling;
- visual cuts and duration align to its output frame grid;
- audio is mixed at 48 kHz with sample-count timestamp normalization and silence padding to the declared interval;
- source coordinates begin at the first decoded frame/sample rather than a container-specific absolute timestamp.

For control beyond this renderer, choose a capable tool and record its exact
request, actual outputs and limits through the production boundary. Prose
instructions add only the control a provider accepts; claim nothing beyond that.

Frame extraction records the requested timestamp and selection rule (first
decoded frame at/after it); audio extraction records the interval and sample
rounding. Both support observation and assert nothing about recognized action,
dialogue, music, performance or meaning. A short rough can answer one uncertain
timing question; it is optional when the request is independent of time, and
adds only the phases it needs.

## 3. Review the assembled interval

Inspect, at shot and sequence scales and as relevant to the purpose:

- actual duration;
- framing;
- motion;
- waits and responses;
- omissions and cuts;
- sound and silence.

Record locators and what was actually observed. A proxy may establish timing;
facial detail, acted intention, meaning of sound and audience effect lie beyond
it. A black frame, silence, repeated framing or stillness can be deliberate
rather than an error. A failure can call for a different
cut/order/duration/source/mix, local repair or partial re-production rather than
complete regeneration.

`examples/timed-production/run_example.py` creates and measures an unpeopled
synthetic sequence as a processing test; it says nothing about acting quality.

## 4. Review-driven edits and recovery

Use [Production Repair](production-repair.md) to revise source selections,
placements, cue relationships, duration, mix or direction against a specific
review. The built-in renderer stages and retains measured output before final
publication; `recover-action` publishes only retained bytes and renders nothing.
Reservations survive uncertain execution and new preparations.

Each selected source interval is checked against the selected stream's measured
duration, beyond container duration alone. The built-in executor selects the
first video/audio stream of the requested kind; for review, identify its actual
numeric stream index and interval explicitly. A missing duration remains
unmeasured rather than silently widening to a broader range.
