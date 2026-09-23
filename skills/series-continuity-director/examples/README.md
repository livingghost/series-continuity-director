# Examples

Every example is synthetic. None of them calls a service, and none records a real author's approval.

Run each command from the directory holding `SKILL.md`. Choose a new directory for every `--out`, outside the installed suite.

## Worked continuity example

`mixed-viewpoint-workshop/` is the canonical conforming example. It is documentation-grounded and not run.

It demonstrates a third-person-primary scene with one embodied first-person insert, temporal state, concealed information, prop transfer planning, shot-specific shot-requests, and a continuity ledger. `scripts/build_example.py` regenerates it.

`test-cases.md` defines regression cases for state, third-person camera, first-person camera, viewpoint transitions, coverage, target adaptation, evidence boundaries, and packaging. Every case is marked as executable enforcement or editorial review; [`scripts/validate_test_cases.py`](../scripts/validate_test_cases.py) runs the executable mutations and checks the complete disposition map.

## Runnable examples

These write a new directory and leave the suite untouched.

| Example | Command | What it shows |
|---|---|---|
| [production-execution](production-execution/) | `python examples/production-execution/run_example.py --out DIR` | One text production run from preparation through review, selection and completion |
| [production-execution](production-execution/) | `python examples/production-execution/repair_example.py --out DIR` | A reviewed passage repaired in a scoped child run |
| [timed-production](timed-production/) | `python examples/timed-production/run_example.py --out DIR` | A rendered audiovisual rough, measured and completed; needs FFmpeg |
| [protocol-exchange](protocol-exchange/README.md) | `python examples/protocol-exchange/run_example.py --out DIR` | A public artifact exported, received and verified |
| [reusable-authoring](reusable-authoring/README.md) | `python scripts/create_authoring_example.py --root DIR` | Scene Persona material and preserved source material |

## Checked examples

Each builder below compares its committed output with a fresh build. Run it with `--check` to verify an installation. Without `--check`, it rewrites the committed files, which is a maintainer step in a development checkout.

| Example | What it shows |
|---|---|
| [submission-gate](submission-gate/README.md) | Admitted and refused submissions, each with its expected refusal code |
| [input-assembly](input-assembly/README.md) | Inspecting, drafting and building authored production inputs |
| [model-evidence](model-evidence/README.md) | Storing an observed service schema without changing its source record |
| [resume-recording](resume-recording/README.md) | Resuming a run after its delivery source changed |
| [tactic-consultation](tactic-consultation/README.md) | Consulting directing vocabulary and applying a project tactic |

```sh
python examples/submission-gate/build_example.py --check
```
