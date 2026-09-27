# Generation Planning

Use generation planning before paid or remote generation when duration, input mode, reference count, or chaining can make the requested edit structurally impossible.

`generation_schedule.py` distinguishes generation duration from edit duration. A four-second provider minimum does not make a two-second edit impossible if a usable two-second source span can be trimmed from that generation. It also does not prove the required performance occurs in that span.

Choose one lane explicitly: `single-generated-sequence`, `independent-shots`, `endpoint-conditioned-chain`, or `edit-existing-media`. The lane is a production choice, not a quality ranking.

Run:

```sh
python scripts/generation_schedule.py check --root PROJECT --plan path/to/generation-plan.json
```

A `structurally-feasible` result means the declared timing and interface constraints are internally compatible. It is not permission to submit, proof of performance, or evidence that planned media exists.
