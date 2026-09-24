#!/usr/bin/env python3
"""Write a submission skeleton from a project and explicit arguments, and fill its reading.

`new` writes one submission document for `submission_gate.py`. It checks the
kind and unit against the approved scene plot and the target against the
profiles. It reads the text from a file, and attaches a reading record and a
visual continuity block when their inputs are given. Every field the author or
agent still decides is written as a placeholder, and the gate refuses the
document until each one is filled.

`reading` fills the `route_reading` of an existing submission from a reading key
or from a complete reading record.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any

import execution_contract as c
import execution_routes
import report_output
import route_reading
import submission_gate as gate
import visual_continuity
from project_layout import ARTIFACT_JSON_ROOTS, CANONICAL_FILES

READING_ROUTE = "media"


def application_paths(documents: list[dict]) -> list[str]:
    """The documents of a reading that each need a quoted application.

    The documents every route reads first are exempt, which is the rule
    `route_reading.require_route_reading` applies.
    """

    manifest = c.load(c.local(route_reading.ROOT, execution_routes.MANIFEST))
    always = set(manifest["always_read"])
    return [item["path"] for item in documents if item["path"] not in always]


def reading_value(root: Path, *, key: str | None = None, applied: Path | None = None,
                  record: Path | None = None) -> dict[str, Any]:
    """The route_reading a submission carries, from a record or from an issued key.

    A key without applications gives the issued edition with `applied` left as a
    placeholder naming each document that needs a quotation.
    """

    if record is not None:
        value = c.load(record)
        route_reading.require_route_reading(value, project=root, routes={READING_ROUTE})
        return value
    issued = route_reading.resolve_issuance(key, project=root)
    row = issued["row"]
    if row["route"] != READING_ROUTE:
        raise ValueError(
            f"the reading key belongs to route {row['route']!r}, and the gate requires a reading of the "
            f"{READING_ROUTE} route: scripts/execution_routes.py read {READING_ROUTE} --root PROJECT"
        )
    if applied is not None:
        applications = c.load(applied)
        if not isinstance(applications, list):
            raise ValueError("the applications file must hold a list of {path, quote, why} entries")
        return route_reading.build_record(issued, {"applied": applications}, project=root)
    value = {name: row[name] for name in ("documents", "features", "route")}
    value["reading_key"] = key
    value["applied"] = gate.placeholder(
        'a list with one entry per document named here, each {"path": the document, "quote": at least '
        'twelve words of paragraph text copied from it, "why": how it applies to this submission}: '
        + ", ".join(application_paths(row["documents"]))
    )
    return value


def refusals(errors: list[dict]) -> str:
    """The gate's refusals as one line, each with its code."""

    return "; ".join(f"{item['code']}: {item['message']}" for item in errors)


def project_file(root: Path, value: str, label: str) -> str:
    """A project-relative POSIX path to a file that exists."""

    try:
        c.local(root, value)
    except ValueError as exc:
        raise ValueError(f"{label} {value!r}: {exc}") from None
    return value


def output_path(root: Path, out: Path) -> tuple[Path, str]:
    """Where the submission is written, and that place relative to the project."""

    target = out if out.is_absolute() else root / out
    try:
        relative = PurePosixPath(target.resolve().relative_to(root.resolve()).as_posix())
    except ValueError:
        raise ValueError(f"write the submission inside the project: {out}") from None
    if relative.parts and relative.parts[0] in ARTIFACT_JSON_ROOTS:
        raise ValueError(
            f"{relative} is under {relative.parts[0]}/, where every JSON file is a typed artifact; "
            "write a submission under media/, such as media/episodes/LINE/prompts/ for one that "
            "depicts part of a scene"
        )
    if target.exists():
        raise ValueError(f"the submission already exists and is not replaced: {out}")
    return target, relative.as_posix()


def input_modes(profile: dict[str, Any]) -> list[str]:
    """The names of the input modes the model declares."""

    return [mode["mode"] for mode in profile.get("input_modes") or []
            if isinstance(mode, dict) and isinstance(mode.get("mode"), str)]


def parameters(entries: list[list[str]]) -> dict[str, Any]:
    """The request settings the arguments state, each value read as JSON when it parses."""

    settings: dict[str, Any] = {}
    for name, raw in entries:
        if name in settings:
            raise ValueError(f"--parameter {name} is given twice")
        try:
            settings[name] = json.loads(raw)
        except ValueError:
            settings[name] = raw
    return settings


def draft(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.project)
    if not root.is_dir():
        raise ValueError(f"the project directory does not exist: {args.project}")
    target_path, relative = output_path(root, Path(args.out))
    profiles = [*args.profiles, gate.DEFAULT_PROFILES]
    profile = gate.load_profile(args.target, profiles)
    if profile is None:
        raise ValueError(f"no target profile records {args.target!r}; the profiles record "
                         + (", ".join(gate.profile_targets(profiles)) or "none"))
    kind = args.kind
    name = PurePosixPath(relative).name
    submission: dict[str, Any] = {
        "submission_id": args.submission_id or name.removesuffix(".json").removesuffix(".submission"),
        "kind": kind,
    }

    scene_characters: list[str] | None = None
    if kind in gate.SCENE_KINDS:
        if not args.scene_plot or not args.unit:
            raise ValueError(f"kind {kind!r} depicts part of a scene: give --scene-plot PATH and --unit ID")
        if args.panel is not None and kind != "page":
            raise ValueError(f"--panel narrows a page, and kind {kind!r} has no panels")
        errors: list[dict] = []
        plot = gate.read_scene_plot(args.scene_plot, root, errors)
        if plot is None:
            raise ValueError(refusals(errors))
        report = plot[1]
        scene_characters = report["characters"]
        submission.update(scene_plot=args.scene_plot, scene_id=report["scene_id"])
        submission[gate.SCENE_KINDS[kind]["unit"]] = args.unit
        if args.panel is not None:
            submission["panel"] = args.panel
    elif args.scene_plot or args.unit or args.panel is not None:
        raise ValueError("an asset belongs to no scene: drop --scene-plot, --unit and --panel")

    submission["target"] = profile["target_id"]
    # A service is named only when the author names one; without it the gate
    # applies the model's rules and reports the service's as unmeasured.
    offerings = {item.get("service"): item for item in profile.get("offerings") or [] if isinstance(item, dict)}
    offering = None
    if args.service:
        if args.service not in offerings:
            raise ValueError(f"the profile {profile['target_id']} records no offering on service "
                             f"{args.service!r}; it records {', '.join(map(str, offerings)) or 'none'}")
        submission["service"] = args.service
        offering = offerings[args.service]

    if args.narrative:
        submission["narrative"] = project_file(root, args.narrative, "--narrative")
    elif (root / CANONICAL_FILES["narrative"]).is_file():
        submission["narrative"] = CANONICAL_FILES["narrative"]
    if args.character:
        submission["characters"] = list(args.character)
    else:
        where = (f"the scene plot carries {', '.join(scene_characters) or 'nobody'}"
                 if scene_characters is not None else "from the narrative")
        submission["characters"] = gate.placeholder(
            f"a list of the ids of the characters this {kind} depicts, or [] for nobody; {where}")

    if args.text_file:
        text = Path(args.text_file).read_bytes().decode("utf-8").rstrip("\r\n")
        if not text.strip():
            raise ValueError(f"the text file is empty: {args.text_file}")
        submission["text"] = text
    else:
        submission["text"] = gate.placeholder("the model-facing text, written from the approved plot")

    modes = input_modes(profile)
    if args.no_inputs:
        submission["inputs"] = []
    elif args.input:
        inputs = []
        for entry in args.input:
            if len(entry) not in (2, 3):
                raise ValueError("--input takes ROLE PATH [MODE]; got " + " ".join(entry))
            item = {"role": entry[0], "path": project_file(root, entry[1], "--input")}
            if len(entry) == 3:
                if entry[2] not in modes:
                    raise ValueError(f"mode {entry[2]!r} is not one the profile {profile['target_id']} "
                                     f"records; it records {', '.join(modes) or 'none'}")
                item["mode"] = entry[2]
            inputs.append(item)
        submission["inputs"] = inputs
    else:
        keys = (" or, with the service named, a request_key it records: "
                + ", ".join(key for values in (offering.get("request_keys") or {}).values() for key in values)
                if offering else "")
        submission["inputs"] = gate.placeholder(
            'a list of the files sent with the text, each {"role", "path", "mode"}, or [] for text only; '
            "mode is one the profile records: " + (", ".join(modes) or "none") + keys)
    if args.parameter:
        submission["parameters"] = parameters(args.parameter)
    submission["obligations"] = {
        "locks": gate.placeholder(
            "a list of the lock surfaces this frame shows, copied verbatim from the approved sheet, or []"),
        "permanent_features": gate.placeholder(
            "a list of the permanent features this frame shows, as phrases, or []"),
    }

    if kind in gate.SCENE_KINDS:
        errors = []
        gate.check_scene_plot(submission, kind, root, errors, [],
                              gate.shown_characters(submission, None))
        if errors:
            raise ValueError(refusals(errors))

    if args.reading_key or args.route_reading:
        submission["route_reading"] = reading_value(
            root, key=args.reading_key, record=Path(args.route_reading) if args.route_reading else None,
            applied=Path(args.applied) if args.applied else None)
    else:
        submission["route_reading"] = gate.placeholder(
            f"the reading of the {READING_ROUTE} route: run scripts/execution_routes.py read "
            f"{READING_ROUTE} --root PROJECT, then scripts/submission_draft.py reading "
            f"PROJECT/{relative} --project PROJECT --reading-key KEY")

    choices = visual_continuity.choices_from_arguments(args, profile)
    if choices is None:
        # The placeholder is saved in the project, so it names the project as PROJECT.
        command = (f"scripts/visual_continuity.py build PROJECT/{relative} --root PROJECT "
                   "--basis PATH --basis-locator TEXT --subject SUBJECT_ID CONTINUITY [CHARACTER_ID]")
        if kind == "shot":
            command += " --shot-camera PATH --shot-request PATH"
        submission["visual_continuity"] = gate.placeholder(f"the visual continuity block: run {command} --write")
    else:
        block = visual_continuity.build_block(submission, choices, root, profile)
        visual_continuity.attach(submission, block)

    import target_protocol
    selected_info = target_protocol.describe(args.target, profiles, service=args.service,
        operation=args.operation, context=({'output_kind': args.output_kind, 'purpose': args.guidance_purpose,
        'input_modes': sorted({i['mode'] for i in submission.get('inputs', []) if isinstance(i, dict) and 'mode' in i}),
        'visual_language': args.visual_language} if args.output_kind and args.guidance_purpose else None),
        guidance_paths=args.guidance)
    if args.operation:
        submission['operation'] = args.operation
    if offering:
        submission['model'] = offering['model_identifier']
    if args.output_kind:
        submission['output_kind'] = args.output_kind
    target_path.parent.mkdir(parents=True, exist_ok=True)
    c.atomic(target_path, gate.submission_bytes(submission))
    return {
        "ok": True,
        "written": relative,
        "execution_preparation": "Resolve execution choices with production_workflow.py build-inputs before rendering or sending.",
        "target_info": selected_info,
        "placeholders": [field for field, _ in gate.placeholders(submission)],
        "next": f"scripts/submission_gate.py {target_path} --root {root} --json",
    }


def attach_reading(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.project)
    path = Path(args.submission)
    submission = c.load(path)
    if not isinstance(submission, dict):
        raise ValueError("the submission must be one JSON object")
    submission["route_reading"] = reading_value(
        root, key=args.reading_key, record=Path(args.route_reading) if args.route_reading else None,
        applied=Path(args.applied) if args.applied else None)
    c.atomic(path, gate.submission_bytes(submission), replace=True)
    return {"ok": True, "written": args.submission,
            "placeholders": [field for field, _ in gate.placeholders(submission)]}


def add_reading_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--reading-key", metavar="KEY",
                       help="The key scripts/execution_routes.py read media printed")
    group.add_argument("--route-reading", metavar="FILE", help="A complete reading record")
    parser.add_argument("--applied", metavar="FILE",
                        help="With --reading-key: a JSON list of {path, quote, why} applications")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)

    new = commands.add_parser("new", help="Write a submission skeleton")
    new.add_argument("--project", required=True, help="The project root")
    new.add_argument("--out", required=True,
                     help="Project-relative path of the new submission file, under media/")
    new.add_argument("--kind", required=True, choices=gate.KINDS)
    new.add_argument("--target", required=True, help="A target id the profiles record")
    new.add_argument("--scene-plot", metavar="PATH", help="Project-relative approved scene plot")
    new.add_argument("--unit", metavar="ID", help="The shot, page or passage of that plot")
    new.add_argument("--panel", type=int, help="With kind page: one panel of that page, from 1")
    new.add_argument("--service", help="The service whose offering of the target this run uses")
    new.add_argument("--submission-id", help="Defaults to the file name without .submission.json")
    new.add_argument("--text-file", metavar="FILE",
                     help="The model-facing text, UTF-8; read from this path, not recorded")
    inputs = new.add_mutually_exclusive_group()
    inputs.add_argument("--input", action="append", nargs="+", metavar="VALUE",
                        help="ROLE PATH [MODE], once per file sent with the text; MODE is an input mode "
                             "the target profile records")
    inputs.add_argument("--no-inputs", action="store_true", help="Send the text alone")
    new.add_argument("--parameter", action="append", nargs=2, metavar=("NAME", "VALUE"),
                     help="A request setting, such as width 1024, once per setting. VALUE is read as JSON "
                          "when it parses and as text otherwise; the gate checks each against the offering")
    new.add_argument("--narrative", metavar="PATH",
                     help=f"Project-relative narrative. Defaults to {CANONICAL_FILES['narrative']} when present")
    new.add_argument("--character", action="append", metavar="ID", help="A character this submission depicts")
    new.add_argument("--profiles", type=Path, action="append", default=[],
                     help="A target profile directory searched before the suite's; repeatable")
    new.add_argument('--operation', help='Exact service operation for guidance and execution.')
    new.add_argument('--output-kind', help='Explicit output kind.')
    new.add_argument('--guidance-purpose', help='Use purpose for applicable target advice.')
    new.add_argument('--guidance', type=Path, action='append', default=[], help='Target-guidance data file; repeatable.')
    new.add_argument('--visual-language', action='append', default=[], help='Visual treatment selector; repeatable.')
    add_reading_arguments(new)
    visual_continuity.add_choice_arguments(new)

    reading = commands.add_parser("reading", help="Fill route_reading in an existing submission")
    reading.add_argument("submission")
    reading.add_argument("--project", required=True, help="The project root holding work/reads.jsonl")
    add_reading_arguments(reading)

    for command in (new, reading):
        report_output.add_json_flag(command)
    args = parser.parse_args(argv)
    report_output.use_json(args.json)
    if args.applied and not args.reading_key:
        parser.error("--applied goes with --reading-key")
    if args.command == "reading" and not (args.reading_key or args.route_reading):
        parser.error("reading needs --reading-key or --route-reading")
    try:
        result = draft(args) if args.command == "new" else attach_reading(args)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        report_output.emit({"ok": False, "error": str(exc)})
        return 1
    report_output.emit(result)
    return 0


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
