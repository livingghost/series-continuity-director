# Viewpoint Profiles

Viewpoint is not one field. Separate camera ownership, knowledge scope, point of audition, and shot grammar.

Knowledge scope is not the scene plot's `focalization`. That one is the narrative contract's, it
is `zero`, `internal` or `external`, and it says whose knowledge the telling of the whole scene is
limited to. This one is a shot's, under a camera already placed, and it says how far that shot's
knowledge reaches. A scene carries both.

## 1. Camera ownership

```text
external_camera
character_body
held_device
worn_device
fixed_diegetic_camera
vehicle_or_machine_sensor
```

## 2. Knowledge scope

`knowledge_scope` on a `shot-camera-spec`, `default_knowledge_scope` on a `scene-viewpoint-plan`.

```text
objective
character_restricted
shared_restricted
omniscient
```

An external camera may still be restricted to one character's knowledge and attention.

## 3. Point of audition

```text
objective_mix
character_subjective
remote_or_device_audio
```

Audio perspective may change without a camera cut.

## 4. Built-in profiles

### External character-aligned third person

`external-character-aligned-third-person`. Default. The camera stays outside all characters while one focal character guides attention, knowledge, and performance emphasis.

### External objective third person

`external-objective-third-person`. Useful for action geography, group blocking, and procedural clarity. It grants no privileged internal knowledge.

### External omniscient third person

`external-omniscient-third-person`. Opt-in. It may reveal information unknown to present characters only when the scene records a deliberate story function.

### Over-the-shoulder

`over-the-shoulder`. The camera is external and aligned with one character through a readable foreground shoulder, head edge, hand, or body mass. It is useful for conversation, observation, threat, intimacy, and hand-offs.

### Embodied first person

`embodied-first-person`. The camera belongs to a character body. Visible limbs, breathing, balance, and contact belong to that camera owner. Detached rig motion is invalid.

### Held or worn device

`held-device-first-person`. The camera follows a declared device, operator, grip, optics, and audio path. Device faults do not describe human vision.

### Fixed diegetic observer

`fixed-diegetic-observer`. The camera is an object inside the story world. Mount, field of view, obstruction, recording properties, and knowledge access are explicit.

## 5. Selection rule

Choose the profile that best carries the shot's hardest evidence or emotional relation. Do not switch only for decorative variety.

A viewpoint change must affect at least one of:

- camera geometry;
- visible information;
- emotional alignment;
- contact or prop readability;
- point of audition;
- transition design;
- review criteria.
