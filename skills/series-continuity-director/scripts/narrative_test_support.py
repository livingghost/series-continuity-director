"""Neutral fixtures for the published narrative contract; not runtime defaults."""
import narrative

def minimal_narrative(cast_size: int = 0, *, chapter: bool = True) -> dict:
    """A fixture with no implicitly declared concern, arc or interpersonal plot."""
    return {
        "artifact_type": "narrative", "series_id": "coherence-fixture", "timeline_id": "main",
        "medium": "prose", "themes": [], "arcs": [], "acts": [],
        "characters": [{"id": f"C{i:02d}", "name": f"Agent {i}",
                        "persona": f"narrative/personas/c{i:02d}.md"}
                       for i in range(1, cast_size + 1)],
        "chapters": ([{"id": "ch01", "number": 1, "title": "Observation", "status": "complete",
                       "arcs": [], "depicts": ["A held condition at one interval."],
                       "story_order_start": 0, "story_order_end": 0}] if chapter else []),
        "relationships": [], "promises": [], "questions": [], "knowledge": [],
    }

def observational_scene(document: dict | None = None) -> dict:
    """One unpeopled, non-dramatic prose scene with actual visible support."""
    document = minimal_narrative() if document is None else document
    return {
        "artifact_type": "scene-plot", "scene_id": "sc01",
        "narrative_sha256": narrative.content_sha256(document), "chapter": "ch01", "order": 1,
        "arcs": [], "themes": [], "characters": [], "focalization": {"kind": "external"},
        "setting": {"interior_exterior": "exterior", "location": "basin",
                    "where": "along the rim", "time_of_day": "dawn"},
        "scene_function": "settle", "delivery_role": "standalone_short",
        "proposition": "Sustain attention to the unchanged pattern of light on still water.",
        "beats": [{"id": "b1", "beat": "The light holds a narrow line along the still water.",
                   "visibility": "visible"}],
        "exchanges": [], "relationship_delta": [], "state_changes": [],
        "placement": [{"statement": "The light lies along the rim.", "from": ["b1"]}],
        "must_preserve": [{"statement": "The water remains still.", "from": ["b1"]}],
        "free": [{"statement": "The length of the description within the intended rhythm."}],
        "realization": {"kind": "passages", "units": [{"id": "p1", "focal_beat": "b1",
            "mode": "scene", "covers": [{"statement": "Light sustained on still water.", "from": ["b1"]}]}]},
    }
