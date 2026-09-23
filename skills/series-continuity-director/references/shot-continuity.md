# Shot Continuity and Seam Design

## 1. Continuity ledger

A scene ledger carries, per shot:

- camera specification hash;
- start and end anchors;
- axis side and screen direction;
- visible subjects;
- prop ownership;
- state snapshot hashes;
- transition requirements;
- unresolved continuity.

## 2. Matching action

When an action crosses a cut, preserve motion phase, direction, active limb, contact, object orientation, and physical response. Cut on a readable phase boundary rather than asking two independent generations to invent matching positions.

## 3. Prop continuity

Record owner, carrier, hand, orientation, open or closed state, damage, and destination. A transfer uses an atomic state event and a visible hand-off or accepted offscreen event.

## 4. State continuity

Every shot points to the correct character state snapshot. A viewpoint switch reprojects the same state unless an explicit event occurs.

## 5. Clip boundaries

Plan a bridge before generation:

```text
action
audio
occlusion
eyeline
light
continuation input
generated transition supported by a real operation
```

## 6. Finishing order

1. accept picture;
2. repair and conform;
3. grade and mix;
4. finish the seam;
5. extract the actual terminal frame;
6. begin continuation from that frame.

## 7. Machine-first checks

Before human review, check dimensions, duration, tracks, boundary frame scale and shift, state hashes, file integrity, and loudness when relevant. Human review then judges motion, acting, sound content, taste, and final acceptance.

## 8. Continuity categories

Track continuity by category instead of one vague score:

```text
identity
state
wardrobe and adornment
prop ownership and orientation
blocking and support
axis and screen direction
eyeline
camera scale, height, and lens relation
action phase
light and atmosphere
audio perspective and bed
knowledge and reveal status
```

A shot can pass identity continuity and fail prop continuity. Record symptoms precisely.

Part inventory pass. Identity is compared part by part, not as an impression. For every part of a character that is in frame, the individual morphology contract gives count, colour, size against its neighbours, position (side and landmark), and what may change; the returned frame is read against those columns beside the accepted views and the accepted endpoint. A miss on any one column is recorded as a symptom that names the part and the column: an ear on the wrong side for the pose, an eyebrow marking absent, an eye of another colour, a second tail. It is a defect whatever else the frame does well, because it reads as another character. Hair-like fur (a crest, mane, ruff, or tuft) is read as hair is: length, volume, and direction against the accepted views, since a close-up grows it as readily as it grows hair. The pass is heaviest on close-ups, where one part fills the frame with nothing to anchor it, and after any step that redraws the frame, where a marking absent from the source stays absent.


## 9. State-aware continuity

Every shot uses the state snapshot effective at its story time. When no event occurs, viewpoint changes reproject the same state. When an event occurs:

1. identify the trigger;
2. declare pre-event state;
3. show or route the transition;
4. declare post-event state;
5. update the event ledger only after approval;
6. bind later shots to the accepted post-event snapshot.

Do not use a future-state reference in a flashback or a pre-event shot.

## 10. Match points

Choose a match point before generating adjacent shots:

- face scale and screen position;
- hand or prop position;
- body silhouette;
- doorway or furniture edge;
- motion direction;
- light boundary;
- sound transient;
- occluding object.

A match point gives post-production and review a concrete registration target.

## 11. Action phase

For action across cuts, record the phase:

```text
preparation
initiation
contact or peak
release
recovery
landing
```

Adjacent beats must connect. The end pose, gaze, support, prop ownership, and action phase of one beat are the start conditions of the next unless a declared cut, time jump, offscreen event, or corrective derivative changes them.

Two clips should not both start the contact or both end before the landing unless the edit intentionally repeats action. Matching action works best when the cut separates clear phases.

## 12. Wardrobe and material continuity

Track:

- layer order and closure;
- rolled or loosened parts;
- wet, dirty, torn, or repaired regions;
- fabric tension and compression;
- accessory attachment and orientation;
- carried versus worn items;
- state-dependent material response.

A change may be physically caused during action. Otherwise it requires an approved event or correction.

## 13. Light continuity

Across continuous story time, preserve:

- source positions;
- direction and color;
- practical intensity;
- shadow side;
- environmental fill;
- reflective anchors;
- weather or atmosphere state.

Camera angle can change apparent brightness. Distinguish expected angle response from an unexplained source change.

## 14. Audio continuity

Record:

- ambient bed;
- dialogue tail;
- music phrase;
- action effect;
- point of audition;
- spatial direction;
- intended J-cut or L-cut;
- silence used as a deliberate event.

A continuous bed often hides picture seams better than a simultaneous picture and audio restart.

## 15. Generated boundaries versus edit boundaries

A generated boundary asks a model to produce motion or transition. An edit boundary joins existing accepted material. Choose based on evidence and risk.

Generated transition requires:

- actual supported operation;
- inspected outgoing and incoming evidence;
- compatible state and geometry;
- exact source-to-control mapping;
- direct review of the result.

Record a generated transition with the complete operation-backed structure:

```text
bridge type: generated transition
outgoing operand
outgoing endpoint anchor
incoming operand
incoming endpoint anchor
generated bridge output
operation
story duration
generated duration
operation-card or run ID
exact controls and files
acceptance criteria
```

A missing operand, endpoint, operation card, or duration is not repaired by calling an ordinary cut a generated transition.

An edit boundary may use hard cut, registered cut, action match, eyeline cut, occlusion, light, sound bridge, dissolve, or another approved transition.

## 16. Continuity repair order

When a boundary fails:

1. confirm correct files and state snapshots were used;
2. identify the failing category;
3. try registration, crop, timing, grade, or audio repair;
4. replace only the failing shot or boundary when possible;
5. use a stronger boundary frame or composite;
6. change operation or target if the evidence cannot be carried;
7. redesign the shot only when the original transition is structurally impossible.

Preserve accepted material and lineage through every repair.

## 17. Continuity completion check

- the ledger contains every shot and transition;
- hashes point to current artifacts;
- no unresolved continuity remains for required categories;
- state and prop changes have approved events or explicit proposals;
- action phases match;
- axis, screen direction, and eyelines are coherent;
- light and audio carry through continuous time;
- the final accepted endpoint is extracted after finishing.
