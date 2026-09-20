# Mixed Viewpoint Workshop

This is the canonical Series Continuity Director example.

It demonstrates:

- external character-aligned third person as the scene default;
- one external tracking shot;
- one over-the-shoulder reveal;
- one embodied first-person handoff insert;
- return to an external reaction and landing master;
- stable axis, screen direction, eyelines, prop ownership, and state;
- a concealed approved injury projected through performance rather than visibility;
- a planned pendant transfer that remains non-canon because the example is not run;
- one shot-request per shot;
- one Species Morphology Profile and one Individual Morphology Contract per recurring character;
- shot-visible morphology refs carried through shot-requests, projections, lineage, and director records.

The source directory contains:

```text
species-morphology-profile-C01.json
individual-morphology-contract-C01.json
character-identity-C01.json
species-morphology-profile-C02.json
individual-morphology-contract-C02.json
character-identity-C02.json
```

C01 is a gray wolf mechanic. C02 is a russet fox archivist with a compact fox muzzle, green eyes, tall dark-tipped ears, plantigrade stance, a full white-tipped tail, and identity-linked brass spectacles. The example does not infer either character from the broad words `wolf` or `fox`; it validates the declared morphology and individual contracts and passes their hashes into every relevant derived artifact.

Build or verify:

```bash
python examples/mixed-viewpoint-workshop/build_example.py
python examples/mixed-viewpoint-workshop/build_example.py --check
```

The example contains no generated media and claims no result quality.
