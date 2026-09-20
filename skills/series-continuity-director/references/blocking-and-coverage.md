# Blocking and Coverage

## 1. Blocking table

For every multi-character scene, record:

```text
character
start position and facing
path or held pose
contact and occlusion
end position and facing
screen direction
```

Use visible landmarks rather than private labels in model-facing text.

## 2. One active objective per shot

A shot may include preparation, response, and settling motions when they serve one dominant change. Split independent objectives, large relocations, competing camera moves, or dialogue without a stable performance window.

## 3. Coverage roles

Useful roles include:

- establishing geography;
- master action;
- aligned medium;
- over-the-shoulder dialogue;
- reaction;
- contact detail;
- prop insert;
- approved information reveal;
- landing master;
- transition bridge.

A role is useful only when it changes the visible function or review.

## 4. Shot and reverse shot

Preserve:

- axis side;
- eyeline height and target;
- subject scale;
- prop ownership;
- wardrobe and state;
- hand positions when continuity matters;
- audio and performance timing.

## 5. Group scenes

Use a stable spatial fan or ring around the active area. Name every actor when limb ownership, motion order, or prop transfer matters. Let inactive characters hold readable poses or minimal reactions.

Three visible recurring characters is a conservative starting point for a short scene. More characters require simpler motion, fewer simultaneous lines, stronger landmark anchoring, and clearer active-versus-held roles. This is a planning heuristic, not a target capability limit.

## 6. Inserts and reveals

An insert may show a prop, wound, clue, hand contact, or state change. It must follow an eyeline, action, sound, interruption, contact, or story reason. Ask why the camera looks there at that moment; the answer cannot be only that the audience needs information. A camera can reveal information only when the selected focalization permits it.

## 7. Spatial coordinate record

Before writing camera prose, establish a simple scene coordinate system from inspected media or an approved layout:

```text
landmark
world position
screen position in the master
allowed movement path
contact surface
occlusion risk
```

Update the record after a major relocation or deliberate axis change. Model-facing text uses visible relations, not private zone names.

## 8. Axis selection

The axis can be defined by:

- two characters facing each other;
- a character and a target object;
- a movement path;
- a vehicle direction;
- a workbench, table, doorway, bed, or other dominant contact line;
- a group oriented toward a shared event.

Complex scenes may contain several local axes. State which axis governs each shot and how the transition re-establishes orientation.

## 9. Entrances, exits, and travel

Record where a subject enters and exits the frame, their world-space path, and screen direction. Across a cut:

- continue the same screen direction when travel continues;
- show a turn or reorientation before reversing;
- use a neutral or re-establishing shot when geography changes;
- keep carrying state, prop ownership, and wardrobe response consistent.

A character leaving frame-right and entering the next shot from frame-right may read as reversal unless the new camera relation is clearly established.

## 10. Conversation coverage

A conversation plan may use:

- shared master;
- character-aligned medium;
- over-the-shoulder views;
- clean single close-ups;
- two-shot profile;
- reaction shot;
- object or hand insert;
- environment or listener cutaway with story function.

Do not create every option automatically. Choose coverage according to power, intimacy, knowledge, contact, and editing needs.

Record:

```text
speaker and listener positions
eyeline target and height
foreground shoulder or object
screen side
prop ownership
hand state
performance window
dialogue route
```

## 11. Power and scale blocking

Power can appear through distance, height, occupied frame area, ability to move, interruption, access to exits, prop control, and who makes the other adjust. Use these physical relations rather than relying only on low or high angles.

For characters of different scale, preserve:

- floor and support contact;
- eye level relation;
- reach distance;
- furniture and doorway scale;
- safe contact geometry;
- camera distance that keeps both identities readable.

## 12. Group blocking

For three or more characters:

1. define the active subject and current objective;
2. place others in readable holds or subordinate reactions;
3. preserve a clear movement lane;
4. name every moving limb or shared prop owner;
5. keep foreground and background groups separated by value, depth, or framing;
6. simplify dialogue and camera movement when physical interaction grows complex.

A group scene may use clusters, lines, rings, or opposing sides. Record who can see and hear each event.

## 13. Contact coverage

A contact scene often needs fewer, stronger shots:

- pre-contact relation;
- contact action with ownership;
- reaction or physical feedback;
- stable landing.

An insert is useful when the exact grip, wound, device, or ownership transfer matters. A reaction shot is useful when the emotional consequence is not readable in the action view.

## 14. Reveal coverage

For a reveal, separate:

```text
cause or attention trigger
what the focal character sees
what the audience sees
reaction
new state or knowledge
landing
```

The insert or reveal shot must be allowed by focalization. If the audience sees more than a focal character, record the deliberate knowledge change.

## 15. Coverage efficiency test

For each planned shot, ask:

- What new visible information does it add?
- What action or reaction does it carry better than the previous shot?
- What continuity evidence does it preserve?
- Does it create a necessary edit point?
- Could its function be combined with another shot without loss?

Consider removal only against the intended effect: duration, recurrence, silence, anticipation, or an unpeopled pattern may be the shot's purpose even when it adds no new event.

## 16. Blocking completion check

- all characters have start and end positions;
- active and inactive roles are readable;
- axis and screen direction are recorded;
- entrances and exits connect across cuts;
- eyelines have targets;
- prop and limb ownership are unambiguous;
- contact surfaces and physical responses are defined;
- group movement has a clear lane;
- every shot has a distinct function;
- the landing supplies usable continuation geometry.

## 17. Zero-simile blocking

Write actual pose, weight, path, amplitude, timing, and landing rather than comparing a character to an animal, profession, ritual, or cinematic archetype.

```text
Weak: C01 stands like a guard dog.
Constructive: C01 plants both feet outside shoulder width, squares the chest to the doorway, lowers the chin, and keeps the right hand beside the latch.
```

```text
Weak: C02 receives the pendant like a sacred relic.
Constructive: C02 raises both hands level at the sternum, closes the fingertips around the pendant, lowers the breath, and holds the object still before looking up.
```

Character-specific dialogue may use simile. Blocking prose should describe camera-readable construction.

## 18. Purpose of a view

Ask why attention is placed here, at this time, for this duration. The purpose may concern action, a relationship, space, a held pattern, withholding, repetition, sound, an omission, or an unresolved ending. An explanatory view is not intrinsically wrong, and no character or incident is required.

Select from feasible framings and presentation orders when they materially change the reading. Record the selected realization, reason, and place in the actual result where its effect can be inspected. Do not remove deliberate stillness or repetition solely because it supplies no new fact.

## 19. Framing, duration, motion, and sound as rhythm

Read the proposed interval as a sequence, not only as individually defensible shots. Compare how frame size, movement, holds, cuts, repeated views, silence, and sound overlap organize attention. Maintaining one scale can be a deliberate rhythm; changing scale is not proof of one. No shot count, scale distribution, axis step, or emotional curve is mandatory.

Choose cut length and transition according to the intended effect rather than leaving every clip at a provider's default duration. The same event may be omitted, repeated from another position, or placed earlier or later in the telling. Keep story order, performance time, source ranges, edit time, and production order separate.

When timing is uncertain, make a playable rough through `timed_sequence.py` or a declared capable editor, and inspect the interval at actual speed with the relevant audio. Proxy frames can test timing but cannot establish a facial performance or a missing sound. Review the segment and the larger whole; repairs may change cut points, ordering, duration, sound, or material choice without regenerating every shot.

A target's demonstrated strengths and failures constrain that operation, not all production. Keep evidence scoped to the controls, subject, scale, and result actually tested. A required detail that fails in one method may need another method, not removal from the intended work.

## 20. Detail, scale, and actual evidence

Before committing a composition, identify which declared structures, surfaces, markings, text, contacts, or relations the frame makes important. Choose their treatment from the purpose and known operation capabilities. Do not assume a universal list of difficult body parts or that a small feature is incapable of visible error.

Inspect the actual result at the intended viewing size and, where needed, at a recorded region or time span. Compare against the relevant design and geometry. A mismatch is an observation; its hidden generation cause is not known merely from its appearance. Preserve meaningful detail when changing framing, references, local edits, compositing, or generation method to repair it.
