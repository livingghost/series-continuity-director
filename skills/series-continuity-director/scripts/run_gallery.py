#!/usr/bin/env python3
"""Every dispatched run of a project in order, each beside its text, model, settings, seed and results.

    python scripts/run_gallery.py <project> [--out <file.html>]
    python scripts/run_gallery.py --self-test

Reads the production runs under `production/` that hold a dispatch claim and
writes `runs/gallery.html` for a person and `runs/gallery.json` for a tool.
`init_project.py` writes both at the start, and `production_dispatch.py`
rewrites them after every send and recovery.

The page is built from the recorded evidence and nothing else. Each field comes
from the request layout that the transport's `compile_request` declared and the
dispatcher sealed into `request-contract.json`:

- `model`, `operation`, `primary_text` and `negative_text` name their fields;
- `management` names envelope fields such as a task identifier;
- `media` names the fields that carry uploaded inputs;
- every other request field is a setting, keyed by its dotted path.

No field name of any one service is known here.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _get(request: Any, path: list | None) -> Any:
    if path is None:
        return None
    value = request
    for part in path:
        if isinstance(value, dict) and isinstance(part, str) and part in value:
            value = value[part]
        elif isinstance(value, list) and type(part) is int and 0 <= part < len(value):
            value = value[part]
        else:
            return None
    return value


def _leaves(value: Any, path: list) -> list[tuple[list, Any]]:
    if isinstance(value, dict) and value:
        return [leaf for key, child in value.items() for leaf in _leaves(child, path + [key])]
    return [(path, value)]


def _dotted(path: list) -> str:
    return ".".join(str(part) for part in path)


def request_fields(request: dict, layout: dict) -> dict[str, Any]:
    """Split one request into the gallery's fields using only its declared layout."""
    named = [layout.get("model"), layout.get("operation"), layout.get("primary_text"), layout.get("negative_text")]
    media = [entry["field"] for entry in layout.get("media") or []]
    management = [list(path) for path in layout.get("management") or []]
    taken = [path for path in named + media + management if path]

    def covered(path: list) -> bool:
        return any(path[:len(owner)] == owner for owner in taken)

    settings = {}
    for path, value in _leaves(request, []):
        if not path or covered(path):
            continue
        # An array of media values is one field; its members are the media paths.
        if isinstance(value, list) and any(owner[:len(path)] == path for owner in media):
            continue
        settings[_dotted(path)] = value
    return {
        "model": _get(request, layout.get("model")),
        "operation": _get(request, layout.get("operation")),
        "text": _get(request, layout.get("primary_text")),
        "negative_text": _get(request, layout.get("negative_text")),
        "management": {_dotted(path): _get(request, path) for path in management},
        "settings": settings,
    }


def run_time(run: str) -> str:
    """The creation time a UUIDv7 run identifier carries, in UTC."""
    milliseconds = uuid.UUID(run).int >> 80
    return datetime.fromtimestamp(milliseconds / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def dispatched(project: Path) -> list[dict[str, Any]]:
    """Every production run with a dispatch claim, read through its integrity checks."""
    import execution_contract as c
    import production_workflow as w
    import transport_contract
    entries = []
    for run in w.run_ids(project):
        base = {"record": f"production/{run}", "at": run_time(run)}
        try:
            run_path, _, _, rows = w.load_run(project, run)
            claims = [row for row in rows if row["event"] == "dispatch-claim"]
            if not claims:
                continue
            claim = claims[-1]
            manifest = claim["data"]["manifest"]
            journal = {row["data"]["stage"]: c.decode(c.object_read(run_path, row["data"]["files"][0]["sha256"]))
                       for row in rows if row["event"] == "dispatch-trace" and row["data"]["claim"] == claim["sha256"]}
            results = [row for row in rows if row["event"] == "dispatch-results" and row["data"]["claim"] == claim["sha256"]]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            entries.append({**base, "integrity": str(exc)})
            continue
        contract = journal.get("request-contract.json")
        request = journal.get("request.json") or (contract or {}).get("request") or {}
        fields = request_fields(request, contract["layout"]) if contract else {}
        outcome = (journal.get("transport-outcome.json") or {}).get("outcome")
        refused = None
        if outcome == transport_contract.REFUSED and "answer.json" in journal:
            try:
                refused = transport_contract.load(manifest["service"]).rejections(journal["answer.json"])
            except (ValueError, ImportError) as exc:
                refused = [{"unread": str(exc)}]
        downloads = {value["path"]: value for stage, value in journal.items() if stage.startswith("download-")}
        spec = manifest["spec"]
        entries.append({
            **base,
            "submission_id": spec.get("submission_id"),
            "target": spec.get("target"),
            "service": spec.get("service"),
            "service_observed_at": manifest["service"].get("observed_at"),
            "gate": {"status": manifest["gate"].get("status"), "unmeasured": manifest["gate"].get("unmeasured", [])},
            **fields,
            "media": [{"role": item.get("role"), "path": item.get("path")} for item in spec.get("inputs") or []],
            "outcome": outcome if "answer.json" in journal else "no recorded response",
            "results": [{"path": item["path"], "sha256": item["sha256"],
                         "seed": (downloads.get(item["path"], {}).get("result") or {}).get("seed")}
                        for row in results[-1:] for item in row["data"]["files"]],
            "refused": refused,
        })
    return entries


def index(project: Path) -> dict[str, Any]:
    entries = dispatched(project)
    entries.sort(key=lambda entry: (str(entry.get("at") or ""), str(entry.get("record"))))
    return {"project": project.name, "generated_at": now(), "entries": entries}


def _escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _cell(value: Any) -> str:
    return _escape(json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value)


def render(page: dict[str, Any]) -> str:
    """One page, no scripts; result files by path relative to the project root, from runs/."""
    blocks = []
    for entry in page["entries"]:
        if "integrity" in entry:
            blocks.append(f'<section class="run refused"><div class="facts"><h2>{_escape(entry["record"])}</h2>'
                          f'<p>integrity: {_escape(entry["integrity"])}</p></div></section>')
            continue
        rows = "".join(f"<tr><th>{_escape(key)}</th><td>{_cell(value)}</td></tr>"
                       for key, value in sorted((entry.get("settings") or {}).items()))
        rows += "".join(f"<tr><th>{_escape(key)}</th><td>{_cell(value)}</td></tr>"
                        for key, value in sorted((entry.get("management") or {}).items()))
        rows += "".join(f"<tr><th>{_escape(item.get('role'))}</th><td>{_escape(item.get('path'))}</td></tr>"
                        for item in entry.get("media") or [])
        images = "".join(
            f'<a href="../{_escape(result.get("path"))}"><img src="../{_escape(result.get("path"))}" alt="{_escape(result.get("path"))}"></a>'
            f'<p class="hash">seed {_escape(result.get("seed"))} {_escape(result.get("sha256"))}</p>'
            for result in entry.get("results") or []
        ) or ('<div class="none">refused: ' + _cell(entry.get("refused")) + "</div>" if entry.get("refused")
              else f'<div class="none">{_escape(entry.get("outcome"))}; no result</div>')
        blocks.append(f"""
<section class="run {'refused' if entry.get('refused') else 'returned'}">
  <div class="image">{images}</div>
  <div class="facts">
    <h2>{_escape(entry.get('submission_id'))} <span class="status">{_escape(entry.get('target'))} on {_escape(entry.get('service'))}</span></h2>
    <p class="when">{_escape(entry.get('at'))} <span class="record">{_escape(entry.get('record'))}</span> {_escape(entry.get('outcome'))}</p>
    <p><b>model</b> {_escape(entry.get('model'))} <b>operation</b> {_escape(entry.get('operation'))} <b>service record observed</b> {_escape(entry.get('service_observed_at'))}</p>
    <p><b>text</b></p><pre>{_escape(entry.get('text'))}</pre>
    {('<p><b>negative</b></p><pre>' + _escape(entry.get('negative_text')) + '</pre>') if entry.get('negative_text') else ''}
    <table>{rows}</table>
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
    # A synthetic layout that no real service uses: nested envelope, `prompt` text.
    layout = {"model": ["engine"], "operation": ["action"], "primary_text": ["prompt"], "negative_text": ["avoid"],
              "output_count": ["count"], "fixed_output_count": None, "seed": ["seed"],
              "media": [{"index": 0, "field": ["attachments", 0]}], "management": [["envelope", "request_id"]],
              "content": [], "fields": []}
    request = {"action": "generate", "engine": "synthetic:model", "prompt": "a heron on a post", "avoid": "a second bird",
               "count": 1, "seed": 3, "size": {"width": 1024, "height": 1024}, "attachments": ["upload-1"],
               "envelope": {"request_id": "synthetic-request"}}
    fields = request_fields(request, layout)
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        (project / "production").mkdir(parents=True)
        (project / "production" / "production-task.json").write_text("{}", encoding="utf-8")
        html_path, json_path = write(project)
        page = json.loads(json_path.read_text(encoding="utf-8"))
        checks = [
            ("the text, negative text and model come from the declared layout",
             (fields["text"], fields["negative_text"], fields["model"], fields["operation"])
             == ("a heron on a post", "a second bird", "synthetic:model", "generate")),
            ("management fields are listed apart from the settings",
             fields["management"] == {"envelope.request_id": "synthetic-request"}),
            ("the settings are every other field, by dotted path",
             fields["settings"] == {"count": 1, "seed": 3, "size.width": 1024, "size.height": 1024}),
            ("a UUIDv7 run identifier gives its creation time",
             run_time("0190a1b2-c3d4-7e5f-8a6b-7c8d9e0f1a2b").startswith("2024-07-")),
            ("a project without dispatched runs has an empty gallery", page["entries"] == [] and stale(project) is None),
            ("the page is written without scripts", "<script" not in html_path.read_text(encoding="utf-8")),
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
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {html_path} and {json_path}")
    return 0


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
