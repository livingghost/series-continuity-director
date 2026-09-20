#!/usr/bin/env python3
"""Validate restored directing knowledge and canonical production templates."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str, errors: list[str]) -> str:
    path = ROOT / rel
    if not path.is_file():
        errors.append(f"{rel}: required file is missing")
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append(f"{rel}: must be UTF-8 text")
        return ""


def require_markers(rel: str, markers: list[str], errors: list[str]) -> None:
    text = read(rel, errors).casefold()
    for marker in markers:
        if marker.casefold() not in text:
            errors.append(f"{rel}: missing restored knowledge marker {marker!r}")


def h2_titles(text: str) -> list[str]:
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


def validate_numbered_sections(rel: str, expected: list[str], errors: list[str]) -> None:
    titles = h2_titles(read(rel, errors))
    actual: list[str] = []
    for index, title in enumerate(titles, 1):
        match = re.fullmatch(r"(\d+)\.\s+(.+)", title)
        if not match:
            errors.append(f"{rel}: section heading is not continuously numbered: {title!r}")
            continue
        if int(match.group(1)) != index:
            errors.append(f"{rel}: expected section {index}, found {title!r}")
        actual.append(match.group(2))
    if actual != expected:
        errors.append(f"{rel}: canonical section list drifted; expected {expected}, found {actual}")


def main() -> int:
    errors: list[str] = []

    require_markers(
        "references/state-and-trust.md",
        [
            "Do not write project observations",
            "installed Series Continuity Director bundle",
            "redact or remove the sensitive portion",
        ],
        errors,
    )


    require_markers(
        "SKILL.md",
        [
            "The user always controls spending, canon approval, and final acceptance",
            "Human viewing is reserved for what measurement cannot decide",
            "machine check could have found before viewing is a process failure",
        ],
        errors,
    )

    require_markers(
        "references/state-and-trust.md",
        [
            "In a persistent workspace, read and update the canonical project files",
            "return complete updated copies when continuity matters",
            "Mark continuity as unverified",
        ],
        errors,
    )

    require_markers(
        "assets/project-templates/asset-registry.md",
        [
            "### P01-PROP",
            "### V01-VIDEO",
            "duration, frame rate, dimensions, and aspect as inspected",
            "accepted opening frame",
            "accepted terminal frame",
            "visible or audible artifacts not canonized",
            "### A01-AUDIO-PERFORMANCE",
            "speaker or performer",
            "language, exact line, timing, and duration",
            "consent and licensing notes",
        ],
        errors,
    )

    validate_numbered_sections(
        "references/first-person-camera.md",
        [
            "Embodied first-person ownership",
            "Functional owner presence",
            "Gaze and attention techniques",
            "The body drives the camera",
            "Stillness without a dead frame",
            "Optics and physiology",
            "Held or worn device profile",
            "Fixed diegetic observer",
            "Time control",
            "Sound-driven camera and point of audition",
            "Direct interaction with the camera owner",
            "External visibility and viewpoint transitions",
            "Starting camera-motion risk heuristics",
            "First-person completion check",
        ],
        errors,
    )
    require_markers(
        "references/first-person-camera.md",
        [
            "Gaze ellipsis",
            "Blink cut",
            "Focus handoff",
            "Peripheral entrance",
            "Held gaze",
            "waking blur",
            "dark adaptation",
            "backlit silhouette",
            "tunnel vision",
            "autofocus searching",
            "device arriving late",
            "zoom overshooting",
            "walking shake",
            "finger, strap",
            "focus breathing",
            "Use at most one deliberate capture fault per beat",
            "An eye does not hunt for autofocus",
            "one or two meaningful hand",
            "sleeve grips",
            "approved body-visibility rule",
            "Object-anchored time skip",
            "Same-composition repeat",
            "heartbeat emphasis",
            "Lower risk",
            "Moderate risk",
            "Higher risk",
        ],
        errors,
    )

    validate_numbered_sections(
        "references/scoped-lexicon.md",
        [
            "Observable visual prose",
            "Function-scoped vocabulary",
            "Clean-realism quality profile",
            "Sound words are not visual-grade words",
            "Zero-simile blocking",
            "Constructive direction before exclusions",
            "Negative and exclusion syntax",
            "Dialogue and character voice",
            "Scoped lexicon completion check",
        ],
        errors,
    )
    require_markers(
        "references/scoped-lexicon.md",
        [
            "nostalgic grade",
            "retro photo",
            "old-photo look",
            "film grain",
            "vintage grade",
            "sepia grade",
            "hazy frame",
            "dreamy focus",
            "soft-focus image",
            "global warm-tone filter",
            "misty overall image",
            "muffled",
            "indistinct",
            "prose similes",
            "no noise; no grain",
            "no noise, grain",
        ],
        errors,
    )

    validate_numbered_sections(
        "references/operational-distinctions.md",
        [
            "A start frame is not a character reference",
            "A planning image is not a submitted image",
            "A video reference is not a video operand",
            "A performance driver is not a generic motion reference",
            "Start-only and start-plus-end submissions require different writing",
            "A text continuity fact is not visual evidence",
            "A planned endpoint is not the next shot's opening evidence",
            "Same-pass dialogue and post-produced dialogue are different productions",
            "A selectable duration is not timestamp obedience",
            "A model-facing prompt is not the whole production",
            "A viewpoint label is not concrete camera direction",
            "Workflow stages are evidence changes, not mental modes",
            "Distinction completion check",
        ],
        errors,
    )

    validate_numbered_sections(
        "references/dialogue-and-audio.md",
        [
            "Dialogue ownership and character grammar",
            "Common synthetic-dialogue tells",
            "Conversation and revision rules",
            "Dialogue function",
            "Dialogue density and stable visual window",
            "Compose in the spoken language",
            "Point of audition",
            "Functional sound design",
            "Music",
            "Subtitles and captions",
            "Localization",
            "Beat-template fatigue",
            "Audio continuity and finishing",
            "Dialogue and audio completion check",
        ],
        errors,
    )
    require_markers(
        "references/dialogue-and-audio.md",
        [
            "dialogue any character could say",
            "customer-service politeness",
            "symmetrical question-and-answer",
            "stock exclamations",
            "translation shaped by another language's syntax",
            "every visible speaker receiving a line",
            "cut at least one third",
            "silent reaction",
            "counter-questions",
            "previous two episodes",
            "In-world metronome",
            "Play the heaviest line dry",
            "Cross-episode motif arc",
        ],
        errors,
    )

    validate_numbered_sections(
        "references/story-structure.md",
        [
            "Production hierarchy",
            "Scene function",
            "Five story functions",
            "Segment delivery roles",
            "Scene proposition",
            "Narrative",
            "Scene plot",
            "One dominant change per unit",
            "Hooks and early value",
            "Turn and emotional peak",
            "Relationship progression",
            "Reveal control",
            "Long-form continuity",
            "Narration and retrospective structure",
            "Sound and music as structure",
            "Multi-clip stitching and generated transitions",
            "Duration, slack, and spare generated time",
            "Retellability check",
            "Publishing tie-ins",
            "Scene completion gate",
        ],
        errors,
    )
    require_markers(
        "references/story-structure.md",
        [
            "standalone_short",
            "chapter_opening",
            "interior_segment",
            "chapter_closing",
            "in-world metronome",
            "Play the heaviest line dry",
            "Cross-episode motif arc",
            "outgoing operand",
            "incoming endpoint anchor",
            "story duration",
            "generated duration",
            "Spare generated time is an intentional hold or ambience tail",
            "cover image",
            "one-line retell may seed a title or description",
            "Publishing copy remains separate from generation text",
        ],
        errors,
    )

    require_markers(
        "references/blocking-and-coverage.md",
        [
            "Zero-simile blocking",
            "why attention is placed here",
            "No shot count, scale distribution",
            "Three visible recurring characters is a conservative starting point",
        ],
        errors,
    )
    require_markers(
        "references/performance-details.md",
        [
            "Species and form vocabulary idea bank",
            "Large form-specific action in short segments",
            "actual operation's supported controls",
            "Material and light as performance",
            "Coordinated details and simultaneous actions",
        ],
        errors,
    )
    require_markers(
        "references/shot-continuity.md",
        [
            "Adjacent beats must connect",
            "generated bridge output",
            "operation-card or run ID",
            "story duration",
            "generated duration",
        ],
        errors,
    )
    require_markers(
        "references/runtime-capabilities.md",
        [
            "Spare generated time is an intentional hold",
            "story duration",
            "selected generated duration",
        ],
        errors,
    )
    require_markers(
        "references/model-facing-artifacts.md",
        [
            "Preserve specificity by moving it, not deleting it",
            "A destructive rewrite",
            "The production must never become less specific",
        ],
        errors,
    )
    require_markers(
        "references/prompt-composition.md",
        [
            "Adjacent beats must connect",
            "Weak: Do not reveal the concealed injury",
            "Weak: No duplicated hands",
        ],
        errors,
    )

    validate_numbered_sections(
        "references/post-production.md",
        [
            "Boundary types and planning record",
            "What separately generated clips do not promise",
            "Continuity joins",
            "Scene transitions",
            "Generated transition record",
            "Registration and conform",
            "Masked-event calibration",
            "Picture repair and alternate paths",
            "Audio finishing",
            "Viewpoint-switch finishing",
            "Terminal-frame and audio-tail extraction",
            "Machine-first verification",
            "Finishing record and completion check",
        ],
        errors,
    )

    require_markers(
        "references/post-production.md",
        [
            "small near-constant shifts in framing",
            "repainted fur, skin, cloth",
            "restarted ambience",
            "Pixel continuity across independent generations is an editing deliverable",
            "-14 LUFS",
            "-16 LUFS",
            "-23 LUFS",
            "-1 dBTP",
        ],
        errors,
    )

    require_markers(
        "references/atmosphere-quality.md",
        [
            "Dual reference temperature",
            "Specular anchors",
            "foreground",
            "midground",
            "background",
            "traces of life",
        ],
        errors,
    )

    require_markers(
        "references/visual-language.md",
        [
            "Humor comes from character instinct",
            "nonvisual sense",
            "repeated functionless micro-gestures",
            "repeated eye-level",
            "ornament, camera motion, or environmental detail",
        ],
        errors,
    )

    template_requirements = {
        "assets/production-templates/scene-and-asset-preparation.md": [
            "## Stop conditions",
            "## Provisional requirement transfer",
        ],
        "assets/production-templates/character-identity-media-request.md": [
            "## Required coverage",
        ],
        "assets/production-templates/scene-layout-boundary-media-brief.md": [
            "## Camera and viewpoint",
            "## Frame role",
        ],
        "assets/production-templates/boundary-frame-inspection.md": [
            "## Direct visual observations",
            "## Audio tail",
            "## Continuation consequence",
        ],
        "assets/production-templates/shot-director-package.md": [
            "## Beat and causal spine",
            "## Creative requirement transfer",
            "## Operation card",
        ],
        "assets/production-templates/submission-sheet.md": [
            "## Target surface",
            "## Operation",
            "## File-to-control mapping",
            "## Text fields",
            "## Settings",
            "## Requirements routed outside this pass",
            "## Preflight",
        ],
        "assets/production-templates/exact-primary-prompt.txt": [
            "Opening context not supplied by submitted media",
            "Dominant visible action and ordered linked micro-actions",
            "Readable landing and continuity state",
        ],
        "assets/production-templates/separate-negative-field.txt": [
            "exact target exposes and documents a separate negative or exclusion field",
            "Concise unwanted artifact category 1",
        ],
        "assets/production-templates/post-production-and-alternate-path.md": [
            "## Requirements not completed in picture generation",
            "## Rejoin",
        ],
        "assets/production-templates/run-review.md": [
            "## Exact run identity",
            "## Variant observations",
            "## Accepted result",
        ],
        "assets/production-templates/documentation-grounded-disclosure.md": [
            "Evidence state: documentation-grounded, not run.",
            "Run status: not run.",
        ],
        "assets/production-templates/episode-archive-entry.md": [
            "accepted run IDs and variants",
            "artifacts explicitly not canonized",
        ],
    }
    for rel, markers in template_requirements.items():
        require_markers(rel, markers, errors)

    require_markers(
        "references/templates.md",
        [
            "Creative completeness",
            "Shot feasibility",
            "Blocking, contact, props, and state",
            "Performance and dialogue",
            "Camera and viewpoint",
            "Visual language and wording",
            "Target adaptation and requirement transfer",
            "Clip packing, delivery, and transitions",
            "Finishing and joins",
            "Run review, archive, and state",
        ],
        errors,
    )

    report = {
        "ok": not errors,
        "errors": errors,
        "stats": {
            "restored_reference_files": 15,
            "production_templates": len(template_requirements),
            "asset_record_types": 5,
        },
        "generated_media_quality": "not evaluated",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
