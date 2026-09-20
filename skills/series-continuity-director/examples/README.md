# Examples

`mixed-viewpoint-workshop/` is the canonical conforming example. It is documentation-grounded and not run.

It demonstrates a third-person-primary scene with one embodied first-person insert, temporal state, concealed information, prop transfer planning, shot-specific shot-requests, and a continuity ledger.

`test-cases.md` defines regression cases for state, third-person camera, first-person camera, viewpoint transitions, coverage, target adaptation, evidence boundaries, and packaging. Every case is marked as executable enforcement or editorial review; [`scripts/validate_test_cases.py`](../scripts/validate_test_cases.py) runs the executable mutations and checks the complete disposition map.
