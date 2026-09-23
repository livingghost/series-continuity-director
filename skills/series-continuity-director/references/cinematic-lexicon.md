# Cinematic Lexicon

Shot and camera vocabulary for writing shot texts, with the behaviour each word buys on an image or video surface. These are the words a director uses to plan; the ones marked as prompt words go into the text as written, and the rest are translated into observable prose before they reach a surface. Every surface has its own closed vocabulary for camera moves; the target profile names it, and a move outside that list is ordinary prose the surface may ignore.

## 1. Shot scale

| Term | What the frame holds | Prompt word |
|---|---|---|
| extreme close-up | one detail fills the frame (an eye, a hand on a handle) | yes |
| close-up | the head, shoulders up | yes |
| medium close-up | chest up | yes |
| medium shot | waist up | yes |
| medium wide (cowboy) | mid-thigh up | yes |
| full shot | head to toe, the figure fills the height | yes |
| wide shot | the figure small within the environment | yes |
| establishing shot | the whole location with the players placed; the first shot of a scene | yes |
| extreme wide | a vast area, the figure barely visible | yes |
| insert | a part of the action in a tighter frame than the master (hands, a prop) | as a scale word |

A scale word alone is read loosely by most surfaces; pair it with what fills the frame (waist up, the hands and the pan, the figure filling the height) and, for a still, with the fraction of the frame the figure occupies.

## 2. Angle and height

| Term | Behaviour | Prompt word |
|---|---|---|
| eye level | the camera at the subject's eye line; neutral | yes |
| low angle | the camera below the eye line looking up; stature, threat | yes |
| high angle | the camera above the eye line looking down; smallness, overview | yes |
| top-down, bird's eye | straight down from above | yes |
| worm's eye | straight up from the ground | yes, but it draws the animal on tag surfaces |
| dutch angle | the horizon tilted | yes |
| over the shoulder | framed past one subject's shoulder toward another | yes |
| point of view | the frame is what a character sees | yes |
| profile, three-quarter, front, rear | the subject's facing to the camera; follows from where the camera stands | yes, only where the geometry allows it |

A height word that describes a person (the eye level of a tall person working there) is read as a viewpoint and can remove the person; write the camera's height as the camera's.

## 3. Camera movement

| Term | Behaviour | Note |
|---|---|---|
| static, locked-off | the camera does not move | the hardest request; say it in prose and give the frame other motion |
| pan left, pan right | the camera swivels horizontally in place; no parallax | follows action, reveals what is beside the frame |
| whip pan | a very fast pan with motion blur | a transition |
| tilt up, tilt down | the camera pivots vertically in place | reveals height |
| dolly in, push in | the camera body moves toward the subject; perspective changes | tension, attention |
| dolly out, pull out | the camera body moves away; the environment expands | reveals, endings |
| truck left, truck right | the body slides sideways, parallel to the subject | walk-and-talks |
| pedestal up, pedestal down | the whole camera rises or drops | |
| crane up | the camera lifts high over the scene | scale |
| tracking shot | the camera follows a moving subject; name the direction it follows from | |
| orbit, arc | the camera circles the subject, fully or partly | some surfaces only |
| zoom in, zoom out | the lens changes, the body stays; the image flattens | not the same as a dolly |
| crash zoom | an extremely fast zoom | shock, comedy |
| dolly zoom | dolly one way while zooming the other; the background stretches | vertigo |
| rack focus | the frame holds and the focus shifts between planes | redirects attention without motion |
| handheld, steadicam, gimbal | the texture of the camera's own motion, from raw to smooth | documentary to glide |
| slow motion | time slowed for a named action | say which action and for how long |

Rules that hold across surfaces:

- one move per shot;
- every move carries a speed word (slow, deliberate, rapid) or a duration in seconds, because a surface has no default speed;
- a pan and a dolly draw different pictures, so the word must be the right one;
- describe what each stage of a move reveals rather than stacking verbs;
- a move is motivated by an action or a look that is visible in the frame.

## 4. Shot grammar

| Term | Meaning |
|---|---|
| master shot | one shot holding the whole scene with every player in view; the geography the closer shots inherit |
| coverage | the set of shots that lets a scene be cut: master, singles, over-the-shoulders, inserts, reactions |
| single | one person alone in the frame within a scene of several |
| two-shot | two people in one frame; their distance is the content |
| over-the-shoulder | conversation coverage past one shoulder |
| insert | a detail of the action in a tighter frame |
| cutaway | a view of something else, then back |
| reaction shot | a cutaway to a face reacting to what just happened |
| eyeline match | a cut from a look to what is looked at |
| match cut | a cut joined on a shared shape, motion, or position |
| axis of action | the line between two interacting characters, or along a movement |
| 180-degree rule | keep the camera on one side of the axis so left and right hold across cuts |
| reverse angle | the opposite side of the previous shot along the same axis; fixtures swap sides |
| frame within frame | a doorway, window, or arch framing the subject |
| leading lines | lines in the scene that pull the eye to the subject |
| negative space | the subject small against emptiness |
| cinematic hold | a beat with no camera or subject movement before or after an action |
| one beat per clip | one narrative moment per short clip |

## 5. Focus and lens

| Term | Behaviour |
|---|---|
| deep focus | foreground, middle, and background all sharp |
| shallow focus | one plane sharp, the rest soft; isolates the subject |
| soft focus | diffusion across the whole frame |
| wide lens (24 to 28 mm feel) | more of the room, stretched perspective near the edges |
| normal lens (35 to 50 mm feel) | natural perspective |
| long lens (85 mm and up feel) | compressed space, flattened background, easy isolation |
| anamorphic | wide frame, oval highlights, horizontal flares |

Lens words are read as a feel on generated surfaces, not as optics; they set how much room is in the frame and how flat the space looks.

## 6. Visual registers

A register is a set of the behaviours above chosen together for a whole series or a scene. Record the chosen register in `series-state.md` as behaviour (scale, camera, light and colour, pacing, finish); a label alone leaves each choice to the surface.

| Register | Scale | Camera | Light and colour | Pacing | Avoid |
|---|---|---|---|---|---|
| cinematic | medium to close; one establishing master per scene | motivated moves, slow push-ins, shallow focus | directional light, a colour grade | holds and one beat per clip | the bare word cinematic |
| documentary | shoulder-height medium and close | handheld feel, slightly imperfect framing | available light, no grade | ordinary tactile motion | dramatic spotlights, product gloss |
| music video, performance | alternating wide and close on the performer | whip pans, crash zooms, cuts on the beat | strobe, colour wash, neon or plain daylight | the song sets the speed | |
| music video, narrative | cinematic coverage of one beat per scene | as cinematic | colour keyed to mood | cutaways for texture | scenes without a reason |
| anime opening | close on faces, poses held at peak | fast cuts, speed lines, flashes | strong backlight, lens flare | one beat per clip | |
| anime slice-of-life | medium, soft normal lens | mostly static, small secondary motion | warm rim light against cool shadow | slow | action poses, glossy 3D |
| manga cinematic | panel sizes as scales, spreads as wides | dramatic close-ups | high contrast, screentone, speed and focus lines | panel rhythm | |
| observational realism | eye-level medium and wide | static or slow | available light, slight warmth | motion from the subjects only | grades and moves |

A resolved `prompt-vocabulary` resource carries the same terms with descriptions for tag-driven surfaces; the target profile carries the exact command list for a video surface.
