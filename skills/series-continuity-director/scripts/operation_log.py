#!/usr/bin/env python3
"""Write local diagnostic operation logs without creating production authority.

Operation logs describe what a CLI attempted and observed. They are not approval,
canon, selection, or dispatch evidence. Secrets are removed before bytes are
written. Project logs live under logs/operations; project-free diagnostics use a
user-local directory.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Iterator

SECRET_KEYS = re.compile(r"(?:api[_-]?key|authorization|password|secret|token|cookie|signature|signed[_-]?url)", re.I)
BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+\-/]+=*")
URL_SECRET = re.compile(r"([?&](?:token|key|signature|sig|credential)=)[^&\s]+", re.I)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def operation_id() -> str:
    # UUID is an operation identifier, not a file-format version.
    return str(uuid.uuid4())


def _redact_text(value: str) -> str:
    value = BEARER.sub("Bearer <redacted>", value)
    return URL_SECRET.sub(lambda m: m.group(1) + "<redacted>", value)


def redact(value: Any, key: str | None = None) -> Any:
    if key and SECRET_KEYS.search(key):
        return "<redacted>"
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, tuple):
        return [redact(v) for v in value]
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _redact_text(str(value))


def _base(root: Path | None) -> Path:
    if root is not None and root.exists() and root.is_dir():
        return root / "logs" / "operations"
    return Path.home() / ".series-continuity-director" / "logs" / "operations"


class OperationLog:
    def __init__(self, command: str, *, root: Path | None = None, arguments: Any = None,
                 parent_operation: str | None = None, related: dict[str, str] | None = None):
        self.command = command
        self.root = root.absolute() if root is not None else None
        self.id = operation_id()
        self.started_at = now()
        self.arguments = redact(arguments or {})
        self.parent_operation = parent_operation
        self.related = redact(related or {})
        day = self.started_at[:10]
        self.directory = _base(self.root) / day / self.id
        self.directory.mkdir(parents=True, exist_ok=False)
        self.events_path = self.directory / "events.jsonl"
        self.sequence = 0
        self.complete = False
        self._write_json("operation.json", {
            "operation_id": self.id,
            "command": command,
            "started_at": self.started_at,
            "parent_operation": parent_operation,
            "related": self.related,
            "arguments": self.arguments,
        })
        self.event("operation_started", result="running")

    def _write_json(self, name: str, value: Any) -> None:
        (self.directory / name).write_text(json.dumps(redact(value), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")

    def event(self, event: str, **data: Any) -> None:
        self.sequence += 1
        row = {"event": event, "operation_id": self.id, "sequence": self.sequence, "timestamp": now(), **redact(data)}
        with self.events_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")

    def artifact(self, *, role: str, path: Path, sha256: str | None = None) -> None:
        current = []
        target = self.directory / "artifacts.json"
        if target.exists():
            current = json.loads(target.read_text(encoding="utf-8"))
        row = {"role": role, "path": path.as_posix()}
        if sha256 is not None:
            row["sha256"] = sha256
        current.append(row)
        self._write_json("artifacts.json", current)
        self.event("artifact_recorded", **row)

    def finish(self, result: str = "success", **data: Any) -> None:
        if self.complete:
            return
        self.event("operation_finished", result=result, **data)
        self.complete = True

    def fail(self, exc: BaseException) -> None:
        if self.complete:
            return
        self.event("operation_failed", result="failed", error_type=type(exc).__name__, error=str(exc))
        self.complete = True


@contextlib.contextmanager
def operation(command: str, *, root: Path | None = None, arguments: Any = None,
              parent_operation: str | None = None, related: dict[str, str] | None = None) -> Iterator[OperationLog]:
    log = OperationLog(command, root=root, arguments=arguments, parent_operation=parent_operation, related=related)
    try:
        yield log
    except BaseException as exc:
        log.fail(exc)
        raise
    else:
        log.finish()
