# Series Continuity Core

Series Continuity Director treats a series as a chain of approved state, adopted media, shot plans, exact operations, and observed results.

## 1. Continuity domains

Continuity is not one score. Track at least:

- story chronology and knowledge;
- character identity and current state;
- wardrobe, accessories, inventory, and prop ownership;
- relationship state and performance behavior;
- location geometry, light, weather, and culture rules;
- viewpoint, axis, screen direction, eyeline, and coverage;
- action order, contact, material response, and landing;
- dialogue, sound, music, and subtitle routing;
- asset lineage, target bindings, and accepted endpoints.

A scene can be continuous in one domain and discontinuous in another. Diagnose the exact domain rather than calling the whole result inconsistent.

## 2. Scene and shot hierarchy

```text
Series
  -> chapter or episode
    -> scene
      -> shot
        -> clip or generation operation
```

A scene is a continuous dramatic and state context. A shot is one camera construction. A clip is a delivery unit and may contain one shot or an intentional internal cut. A generation operation is the actual target action used to produce or edit media.

Do not treat these names as interchangeable.

## 3. Scene default and shot overrides

Each scene owns:

- story time and current state snapshot;
- visible cast and active relationships;
- environment and prop state;
- default viewpoint profile;
- focalization and point of audition;
- axis of action;
- sparse coverage strategy;
- planned state transitions;
- landing required for the next scene.

Each shot stores only meaningful overrides and a complete camera specification.

## 4. Sparse coverage

Third-person capability does not justify automatic coverage inflation. Include a shot only when it performs a distinct visible function:

- geography;
- cause;
- primary action;
- reaction;
- contact detail;
- information reveal;
- landing;
- transition bridge.

Merge shots that repeat the same function without changing interpretation.

## 5. State continuity and viewpoint continuity

A viewpoint switch does not create a state change. Every shot before a state event projects the same canonical state from a different camera. A planned state event separates pre-event and post-event snapshots.

```text
scene start state
  -> shot projections before event
  -> planned or approved event
  -> post-event projection
  -> scene end state proposal
```

## 6. Asset continuity

Use adopted assets only inside their effective story ranges and visible support. A front portrait does not support a rear marking. A pre-injury asset may remain correct for a flashback and incorrect for the current scene.

Each actual run records:

- exact file;
- exact control;
- intended influence;
- what the prompt still supplies;
- review dimensions;
- fallback.

## 7. Continuation rule

Finish the accepted result before extracting the endpoint. The next shot or clip begins from the finished frame, actual prop ownership, actual body pose, actual light, and actual sound tail.

A planned endpoint remains useful for acceptance criteria, but it never overrides observed geometry.

## 8. Canon boundary

A generated output may suggest a useful change. It becomes canon only after acceptance. Artifacts such as extra jewelry, altered scars, changed clothing, accidental gestures, or inferred motives remain non-canon until approved.
