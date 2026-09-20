#!/usr/bin/env python3
"""Read `asset-registry.md` and check the authority of its records.

The registry decides which file a later session submits. That decision is carried
by two fields: `role`, the job an asset holds, and `status`, one of `candidate`,
`accepted`, `superseded`, or `stale`. Exactly one asset is `accepted` for a role.

The checks here are the ones a machine can settle. Whether an asset still looks
right after its upstream changed is an inspection; whether the registry claims
two accepted assets for one role, or leaves a produced file unrecorded, is not.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

STATUSES = ("candidate", "accepted", "superseded", "stale")
CURRENT = ("accepted", "stale")

RECORD_HEADING = re.compile(r"^###\s+(?P<id>\S+)\s*(?:-\s*(?P<label>.*))?$")
FIELD = re.compile(r"^(?P<indent>\s*)-\s*(?P<key>[^:]+):\s*(?P<value>.*)$")
BULLET = re.compile(r"^\s+-\s*(?P<value>.+)$")
# A placeholder in the shipped template still reads as a record. It names no file
# and holds no role, and treating it as an asset would fail every new project.
FILE_KEYS = ("file", "files and views")

# One list, read two ways. `MEDIA_SUFFIXES` decides what counts as produced media
# on disk, and `PATH_TOKEN` finds the same names inside a record. A suffix known
# to only one of them makes a correctly registered file look unregistered, and it
# does so for as long as the two lists disagree.
MEDIA_EXTENSIONS = (
    "png", "jpg", "jpeg", "webp", "gif", "bmp", "tif", "tiff",
    "mp4", "mov", "webm", "mkv", "wav", "mp3", "m4a", "flac", "aac", "ogg",
)
MEDIA_SUFFIXES = {"." + extension for extension in MEDIA_EXTENSIONS}
# Longest first, so `tiff` is not read as `tif` followed by a stray letter.
PATH_TOKEN = re.compile(
    r"[\w./-]+\.(?:"
    + "|".join(sorted(MEDIA_EXTENSIONS, key=lambda value: (-len(value), value)))
    + r")\b",
    re.IGNORECASE,
)


def parse(text: str) -> list[dict[str, Any]]:
    """Split the registry into records, each a heading plus its flat field map."""

    records: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    last_key: str | None = None
    for number, line in enumerate(text.splitlines(), 1):
        heading = RECORD_HEADING.match(line)
        if heading:
            current = {
                "id": heading.group("id"),
                "label": (heading.group("label") or "").strip(),
                "line": number,
                "fields": {},
                "lists": {},
            }
            records.append(current)
            last_key = None
            continue
        if current is None:
            continue
        field = FIELD.match(line)
        if field and not field.group("indent"):
            last_key = field.group("key").strip().lower()
            current["fields"][last_key] = field.group("value").strip()
            current["lists"][last_key] = []
            continue
        bullet = BULLET.match(line)
        if bullet and last_key is not None:
            current["lists"][last_key].append(bullet.group("value").strip())
    return records


def normalize(name: str) -> tuple[str, ...]:
    """A path as comparable segments, whichever separator and case wrote it."""

    return tuple(
        part for part in name.replace("\\", "/").lower().split("/")
        if part and part != "."
    )


def names_same_file(recorded: tuple[str, ...], relative: tuple[str, ...]) -> bool:
    """A record may name a bare file name or any tail of the path.

    Compared on whole segments, so `a.png` does not answer for `extra-a.png` and
    a real gap in the registry stays visible.
    """

    return bool(recorded) and len(recorded) <= len(relative) and relative[-len(recorded):] == recorded


def files_of(record: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in FILE_KEYS:
        values.append(record["fields"].get(key, ""))
        values.extend(record["lists"].get(key, []))
    found: list[str] = []
    for value in values:
        found.extend(PATH_TOKEN.findall(value))
    return found


def is_placeholder(record: dict[str, Any]) -> bool:
    return not files_of(record) and not record["fields"].get("role")


def upstream_of(record: dict[str, Any], known: set[str]) -> list[str]:
    value = " ".join([record["fields"].get("derived from", ""), *record["lists"].get("derived from", [])])
    return [token for token in re.findall(r"[A-Za-z0-9][\w-]*", value) if token in known]


def check(text: str, media_files: list[str], *, warn_limit: int = 20) -> tuple[list[str], list[str]]:
    """Return errors and warnings for one registry.

    `warn_limit` caps the unrecorded-media warnings and replaces the remainder
    with one line carrying the count.
    """

    errors: list[str] = []
    warnings: list[str] = []
    records = parse(text)
    known = {record["id"] for record in records}
    live = [record for record in records if not is_placeholder(record)]

    by_role: dict[str, list[dict[str, Any]]] = {}
    for record in live:
        where = f"asset-registry.md:{record['line']} {record['id']}"
        status = record["fields"].get("status", "")
        role = record["fields"].get("role", "")
        if status not in STATUSES:
            errors.append(f"{where}: status must be one of {', '.join(STATUSES)}, found {status or 'nothing'}")
        if not role:
            errors.append(f"{where}: record names a file but holds no role")
            continue
        by_role.setdefault(role, []).append(record)

    for role, holders in sorted(by_role.items()):
        accepted = [record for record in holders if record["fields"].get("status") == "accepted"]
        if len(accepted) > 1:
            ids = ", ".join(record["id"] for record in accepted)
            errors.append(f"asset-registry.md: role {role} carries {len(accepted)} accepted assets: {ids}")
        stale = [record for record in holders if record["fields"].get("status") == "stale"]
        if len(accepted) + len(stale) > 1 and not accepted:
            ids = ", ".join(record["id"] for record in stale)
            errors.append(f"asset-registry.md: role {role} carries {len(stale)} stale assets: {ids}")

    # Staleness travels along `derived from`. An asset that still claims to be
    # accepted while the asset under it is superseded or stale has not been
    # inspected against the change, and the registry is saying it has.
    status_of = {record["id"]: record["fields"].get("status", "") for record in live}
    for record in live:
        if record["fields"].get("status") != "accepted":
            continue
        for parent in upstream_of(record, known):
            if status_of.get(parent) in ("superseded", "stale"):
                errors.append(
                    f"asset-registry.md:{record['line']} {record['id']}: accepted, but its upstream "
                    f"{parent} is {status_of[parent]}. Inspect it against the current upstream or mark it stale."
                )
                break

    recorded = {normalize(name) for record in live for name in files_of(record)}
    unrecorded = [
        relative for relative in media_files
        if not any(names_same_file(name, normalize(relative)) for name in recorded)
    ]
    warnings.extend(f"{relative}: produced media with no registry record" for relative in unrecorded[:warn_limit])
    if len(unrecorded) > warn_limit:
        warnings.append(
            f"{len(unrecorded) - warn_limit} further files under media/ have no registry record"
        )
    return errors, warnings


def media_files(project: Path) -> list[str]:
    """List the produced media under `media/`, and only that.

    A spec, a plan, a prompt file and a README sit beside the media they made and
    are not themselves media.
    """

    media = project / "media"
    if not media.is_dir():
        return []
    return sorted(
        str(path.relative_to(project)).replace("\\", "/")
        for path in media.rglob("*")
        if path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() in MEDIA_SUFFIXES
    )
