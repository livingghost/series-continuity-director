#!/usr/bin/env python3
"""Open one production line (an episode-shaped media namespace) inside an existing project."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from project_layout import PROJECT_ID_RE, episode_media_directory_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Open a production line in a Series Continuity Director project")
    parser.add_argument("--project", required=True, help="Existing project directory")
    parser.add_argument("--line", required=True, help="Line id, for example E03 or E02-M")
    args = parser.parse_args()

    if not PROJECT_ID_RE.fullmatch(args.line):
        raise SystemExit("line must be 2 to 64 ASCII letters, digits, dots, underscores, or hyphens")
    project = Path(args.project).resolve()
    if not (project / "project-manifest.json").is_file():
        raise SystemExit(f"not a project directory: {project}")
    line_id = args.line.lower()
    root = project / "media" / "episodes" / line_id
    if root.exists():
        raise SystemExit(f"line already exists: {root}")
    created = []
    for rel in episode_media_directory_paths(line_id):
        (project / rel).mkdir(parents=True)
        created.append(rel)
    print(json.dumps({"ok": True, "project": str(project), "line": line_id, "created": created}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
