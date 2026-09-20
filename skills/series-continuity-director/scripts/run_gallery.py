#!/usr/bin/env python3
"""Every run of a project in order, each beside the text, the model, the settings, the seed, and what came back.

    python scripts/run_gallery.py <project> [--out <file.html>]
    python scripts/run_gallery.py --self-test

Reads the run records `dispatch.py` writes under `runs/` and writes
`runs/gallery.html` for a person and `runs/gallery.json` for a tool. The page is
built from the records and nothing else, so a result that is not in it is a
result that was not recorded through the gate and the dispatcher.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Request keys that are not settings of the result: the model and text are shown
# on their own, media by role, and the envelope names the run.
NOT_A_SETTING = ("model", "positivePrompt", "negativePrompt", "inputs", "taskType", "taskUUID", "deliveryMethod")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_records(project: Path) -> list[tuple[str, dict[str, Any]]]:
    runs = project / "runs"
    found = []
    for path in sorted(runs.glob("*.json")) if runs.is_dir() else []:
        if path.name in ("gallery.json",):
            continue
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and "submitted" in value:
            found.append((path.name, value))
    return found


def index(project: Path) -> dict[str, Any]:
    entries = []
    for name, record in read_records(project):
        sent = record.get("submitted") if isinstance(record.get("submitted"), dict) else {}
        entries.append({
            "record": f"runs/{name}",
            "at": record.get("at"),
            "submission_id": record.get("submission_id"),
            "target": record.get("target"),
            "service": record.get("service"),
            "service_observed_at": record.get("service_observed_at"),
            "model": sent.get("model"),
            "text": sent.get("positivePrompt"),
            "negative_text": sent.get("negativePrompt"),
            "settings": {key: value for key, value in sent.items() if key not in NOT_A_SETTING},
            "media": record.get("inputs") or [],
            "results": record.get("results") or [],
            "refused": record.get("refused") or [],
            "gate": record.get("gate"),
        })
    entries.sort(key=lambda entry: (str(entry.get("at") or ""), str(entry.get("record"))))
    return {"project": project.name, "generated_at": now(), "entries": entries}


def _escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render(page: dict[str, Any]) -> str:
    """One page, no scripts; result files by path relative to the project root, from runs/."""
    blocks = []
    for entry in page["entries"]:
        settings = "".join(
            f"<tr><th>{_escape(key)}</th><td>{_escape(json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value)}</td></tr>"
            for key, value in sorted((entry.get("settings") or {}).items())
        )
        media = "".join(f"<tr><th>{_escape(item.get('role'))}</th><td>{_escape(item.get('path'))}</td></tr>" for item in entry.get("media") or [])
        images = "".join(
            f'<a href="../{_escape(result.get("path"))}"><img src="../{_escape(result.get("path"))}" alt="{_escape(result.get("path"))}"></a>'
            f'<p class="hash">seed {_escape(result.get("seed"))} {_escape(result.get("sha256"))}</p>'
            for result in entry.get("results") or []
        ) or ('<div class="none">refused: ' + _escape(json.dumps(entry.get("refused"), ensure_ascii=False)) + "</div>" if entry.get("refused") else '<div class="none">no result</div>')
        blocks.append(f"""
<section class="run {'refused' if entry.get('refused') else 'returned'}">
  <div class="image">{images}</div>
  <div class="facts">
    <h2>{_escape(entry.get('submission_id'))} <span class="status">{_escape(entry.get('target'))} on {_escape(entry.get('service'))}</span></h2>
    <p class="when">{_escape(entry.get('at'))} <span class="record">{_escape(entry.get('record'))}</span></p>
    <p><b>model</b> {_escape(entry.get('model'))} <b>service record observed</b> {_escape(entry.get('service_observed_at'))}</p>
    <p><b>text</b></p><pre>{_escape(entry.get('text'))}</pre>
    {('<p><b>negative</b></p><pre>' + _escape(entry.get('negative_text')) + '</pre>') if entry.get('negative_text') else ''}
    <table>{settings}{media}</table>
  </div>
</section>""")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{_escape(page.get('project'))} runs</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 1.5rem; color: #222; background: #fafafa; }}
h1 {{ font-size: 1.4rem; }} h2 {{ font-size: 1rem; margin: 0 0 .25rem; }}
.run {{ display: grid; grid-template-columns: 320px 1fr; gap: 1rem; padding: 1rem; margin: 0 0 1rem; background: #fff; border: 1px solid #ddd; }}
.run.refused {{ border-color: #c55; }}
.image img {{ max-width: 320px; max-height: 320px; display: block; }} .none {{ color: #999; }}
.status, .record {{ font-weight: normal; color: #666; }} .when, .hash {{ color: #777; font-size: .85rem; }}
pre {{ white-space: pre-wrap; background: #f4f4f4; padding: .5rem; margin: 0 0 .5rem; }}
table {{ border-collapse: collapse; font-size: .9rem; }} th {{ text-align: left; padding: .1rem .6rem .1rem 0; color: #555; }} td {{ padding: .1rem 0; }}
</style></head>
<body><h1>{_escape(page.get('project'))}: {len(page['entries'])} runs, generated {_escape(page.get('generated_at'))}</h1>
{''.join(blocks)}
</body></html>
"""


def stale(project: Path) -> str | None:
    """Why the gallery on disk is not the one the run records would produce, or None."""
    json_path = project / "runs" / "gallery.json"
    if not json_path.is_file() or not (project / "runs" / "gallery.html").is_file():
        return "runs/gallery.json or runs/gallery.html is missing"
    try:
        held = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"runs/gallery.json: {exc}"
    if not isinstance(held, dict) or held.get("entries") != index(project)["entries"]:
        return "runs/gallery.json does not list what the run records hold"
    return None


def write(project: Path, out: Path | None = None) -> tuple[Path, Path]:
    page = index(project)
    html_path = (out or (project / "runs" / "gallery.html")).resolve()
    json_path = html_path.with_suffix(".json")
    html_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(page, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    html_path.write_text(render(page), encoding="utf-8", newline="\n")
    return html_path, json_path


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        (project / "runs").mkdir(parents=True)
        (project / "media").mkdir()
        (project / "media" / "b.png").write_bytes(b"\x89PNG")
        later = {"at": "2026-09-13T10:00:00Z", "submission_id": "s02", "target": "t", "service": "svc", "service_observed_at": "2026-09-13",
                 "gate": {"status": "admitted", "unmeasured": []},
                 "submitted": {"taskType": "imageInference", "taskUUID": "x", "model": "vendor:m@1", "positivePrompt": "a heron on a post", "width": 1024, "height": 1024, "seed": 3},
                 "inputs": [{"role": "reference", "path": "media/a.png", "id": "u1"}],
                 "results": [{"path": "media/b.png", "sha256": "0" * 64, "seed": 3, "task": "x"}]}
        earlier = {"at": "2026-09-13T09:00:00Z", "submission_id": "s01", "target": "t", "service": "svc",
                   "submitted": {"taskType": "imageInference", "taskUUID": "y", "model": "vendor:m@1", "positivePrompt": "a heron", "duration": 3},
                   "refused": [{"code": "invalidVideoDurationInteger"}]}
        (project / "runs" / "s02-x.json").write_text(json.dumps(later), encoding="utf-8")
        (project / "runs" / "s01-refused.json").write_text(json.dumps(earlier), encoding="utf-8")
        html_path, json_path = write(project)
        page = json.loads(json_path.read_text(encoding="utf-8"))
        checks = [
            ("runs are listed oldest first", [e["submission_id"] for e in page["entries"]] == ["s01", "s02"]),
            ("the settings are the request without the model, the text, the media, and the envelope", page["entries"][1]["settings"] == {"width": 1024, "height": 1024, "seed": 3}),
            ("a refused run keeps its refusal", page["entries"][0]["refused"] == [{"code": "invalidVideoDurationInteger"}]),
            ("the page shows the result by path and the text", 'src="../media/b.png"' in html_path.read_text(encoding="utf-8") and "a heron on a post" in html_path.read_text(encoding="utf-8")),
            ("the gallery's own files are not read as runs", len(index(project)["entries"]) == 2),
        ]
    failures = [name for name, passed in checks if not passed]
    print(json.dumps({"ok": not failures, "checks": len(checks), "failures": failures}, indent=2))
    return 0 if not failures else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("project", type=Path, nargs="?")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.project is None:
        parser.error("a project directory, or --self-test")
    try:
        html_path, json_path = write(args.project.resolve(), args.out)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {html_path} and {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
