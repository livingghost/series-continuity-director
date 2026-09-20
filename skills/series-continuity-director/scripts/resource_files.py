#!/usr/bin/env python3
"""Resolve an explicitly selected resource file or the suite's own catalog.

SERIES_RESOURCES can name one explicit JSON resource configuration: {"resources": {role: path}}.
Those paths are relative to that configuration's directory. No installation,
package manifest, private state store, home directory or sibling tree is searched.
"""
from __future__ import annotations
import os
from pathlib import Path
from integration_contract import contained_path, read_json

ROOT = Path(__file__).resolve().parents[1]
CONFIG_ENV = "SERIES_RESOURCES"


def _file(path: Path) -> Path:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"resource is not a regular file: {path}")
    # Keep the declared spelling: a root reached through a junction or a short
    # name answers under its own name, and a symbolic link was refused above.
    return path if path.is_absolute() else path.absolute()


def _catalog(path: Path) -> dict[str, str]:
    value = read_json(path)
    if set(value) != {"resources"} or not isinstance(value["resources"], dict):
        raise ValueError("resource configuration must contain a resources object")
    for name, rel in value["resources"].items():
        if not name.strip() or not isinstance(rel, str) or not rel.strip():
            raise ValueError("resource roles and paths must be nonempty strings")
    return value["resources"]


def resolve_resource(name: str, explicit: str | None = None, env_var: str | None = None) -> Path | None:
    if explicit:
        return _file(Path(explicit).expanduser())
    if env_var and os.environ.get(env_var):
        return _file(Path(os.environ[env_var]).expanduser())
    configured = os.environ.get(CONFIG_ENV)
    if configured:
        path = _file(Path(configured).expanduser())
        resources = _catalog(path)
        if name in resources:
            return _file(contained_path(path.parent, resources[name]))
    resources = _catalog(ROOT / "assets/resources/catalog.json")
    rel = resources.get(name)
    return _file(contained_path(ROOT, rel)) if rel is not None else None
