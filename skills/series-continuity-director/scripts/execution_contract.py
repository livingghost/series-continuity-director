#!/usr/bin/env python3
"""Deterministic integrity, safe local I/O and locking for production records."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import tempfile
import time
import threading
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

from io_budget import read_stream
SHA = re.compile(r"^[0-9a-f]{64}$")
# Its content differs by platform, so a copier of generated trees skips it by name.
LOCK_NAME = ".production.lock"


def encoded(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def content_id(value: Any) -> str:
    return digest(encoded(value))


def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def decode(raw: bytes) -> Any:
    def bad(value: str) -> None:
        raise ValueError(f"non-finite JSON number: {value}")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=bad)


def exact(value: Any, fields: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{label}: expected fields {sorted(fields)}")


def text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: nonempty text required")
    return value


def sha(value: Any) -> str:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError("invalid SHA-256")
    return value


# A command reports these as one JSON error object: refused or malformed input,
# a missing or changed file, and a record whose shape is not the declared one.
EXPECTED_ERRORS = (ValueError, OSError, KeyError, IndexError, TypeError, AttributeError, RecursionError)


def failure(exc: BaseException) -> dict[str, Any]:
    """Describe an expected command failure as one JSON-ready object."""
    if isinstance(exc, KeyError):
        message = f"missing field: {exc.args[0]!r}" if exc.args else "missing field"
    elif isinstance(exc, RecursionError):
        message = "record nesting is too deep to read"
    elif isinstance(exc, (IndexError, TypeError, AttributeError)):
        message = "malformed record: " + str(exc)
    else:
        message = str(exc) or type(exc).__name__
    return {"ok": False, "error": message}


# The Win32 specification "Naming Files, Paths, and Namespaces" reserves these
# device names in every directory, with or without an extension.
DEVICE_NAMES = frozenset({"CON", "PRN", "AUX", "NUL"} | {
    prefix + digit for prefix in ("COM", "LPT") for digit in "0123456789\u00b9\u00b2\u00b3"})
# The same specification refuses these characters in a name. A colon also
# selects a drive or an NTFS alternate data stream.
RESERVED_CHARACTERS = frozenset('<>:"|?*') | {chr(code) for code in range(32)}


def portable_name(part: str) -> str:
    """Refuse a path component that Windows would read as another name.

    Windows drops a trailing dot or space, so `hero.png.` opens `hero.png`.
    A colon names a drive or a stream, so `hero.png:ads` is another file.
    A device name such as `NUL` or `nul.txt` opens a device. Such a component
    is refused on every platform, so one file keeps one recorded identifier.
    """
    if part.endswith((".", " ")):
        raise ValueError(f"path component ends with a dot or a space: {part!r}")
    if RESERVED_CHARACTERS & set(part):
        raise ValueError(f"path component holds a character Windows reserves: {part!r}")
    if part.split(".", 1)[0].rstrip(" ").upper() in DEVICE_NAMES:
        raise ValueError(f"path component is a Windows device name: {part!r}")
    return part


def local(root: Path, relative: str, *, exists: bool = True) -> Path:
    """Join a canonical, portable POSIX relative path to a project root.

    The root is resolved once, so a symbolic link above it is accepted. The
    macOS /tmp directory and a linked home directory are such links. The root
    itself and every component below it must not be a symbolic link, and the
    joined path must stay inside the resolved root.
    """
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("canonical project-relative POSIX path required")
    rel = PurePosixPath(relative)
    if rel.is_absolute() or rel.as_posix() != relative or any(x in {".", ".."} for x in rel.parts):
        raise ValueError("path must remain within the project")
    for part in rel.parts:
        portable_name(part)
    root = root.absolute()
    if root.is_symlink():
        raise ValueError("symbolic link in root")
    base = root.resolve()
    target = root.joinpath(*rel.parts)
    for p in [target, *target.parents]:
        if p == root:
            break
        if p.is_symlink():
            raise ValueError("symbolic link in project path")
    try:
        target.resolve().relative_to(base)
    except ValueError:
        raise ValueError("path must remain within the project") from None
    if exists and not target.exists():
        raise ValueError(f"missing file: {relative}")
    return target


def read(path: Path, maximum: int | None = None) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"not a regular file: {path.name}")
    with path.open("rb") as stream:
        return read_stream(stream, maximum, label=str(path))


def load(path: Path) -> Any:
    return decode(read(path))


def fsync_dir(path: Path) -> None:
    if os.name == "posix":
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def atomic(path: Path, raw: bytes, *, replace: bool = False) -> None:
    """Write `raw` durably to `path`.

    With `replace`, the complete bytes replace any existing file in one step.
    Without it, a hard link publishes the complete bytes in one step and
    refuses an existing name. FAT32, exFAT and some network shares refuse hard
    links. There the file is created only if the name is free, then written and
    flushed. It still refuses an existing name, but it is visible while it is
    written, and an interruption can leave it incomplete under its final name.
    Content-addressed records and objects reveal such a file by their hash check.
    """
    if path.is_symlink():
        raise ValueError("cannot write through symbolic link")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    temp = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(temp, path)
        else:
            # Exclusive atomic publication. The caller holds the project lock.
            try:
                os.link(temp, path)
            except FileExistsError:
                raise
            except OSError:
                create_exclusive(path, raw)
        fsync_dir(path.parent)
    finally:
        temp.unlink(missing_ok=True)


def create_exclusive(path: Path, raw: bytes) -> None:
    """Create `path` only if the name is free, then write and flush `raw`.

    The mode matches the temporary file that a hard link would have published.
    A failed write removes the file this call created.
    """
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def publish_directory(staging: Path, target: Path, *, patience: float = 10.0) -> None:
    """Rename a completed staging directory into place.

    Windows refuses to rename a directory while another process holds a handle
    inside it, and a scanner or indexer opening freshly written files does
    exactly that for a moment. A refusal is retried for `patience` seconds and
    then raised as it came.
    """
    deadline = time.monotonic() + patience
    while True:
        try:
            staging.rename(target)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.1)


_thread_locks: dict[str, Any] = {}
_lock_registry_guard = threading.Lock()
_held_locks = threading.local()


def _reset_process_locks() -> None:
    global _thread_locks, _lock_registry_guard, _held_locks
    _thread_locks = {}
    _lock_registry_guard = threading.Lock()
    _held_locks = threading.local()


if hasattr(os, 'register_at_fork'):
    os.register_at_fork(after_in_child=_reset_process_locks)


@contextlib.contextmanager
def lock(root: Path) -> Iterator[None]:
    """Hold one project lock across nested calls, threads and processes.

    Locking creates only the lock file. The root must already exist, so a
    mistyped root fails here instead of becoming a new directory tree.
    """
    root = root.absolute()
    if not root.is_dir():
        raise ValueError(f"project root is not an existing directory: {root}")
    key = str(root.resolve())
    with _lock_registry_guard:
        mutex = _thread_locks.setdefault(key, threading.RLock())
    with mutex:
        held = getattr(_held_locks, 'roots', None)
        if held is None:
            held = _held_locks.roots = set()
        if key in held:
            yield
            return
        with _os_lock(root):
            held.add(key)
            try:
                yield
            finally:
                held.remove(key)


@contextlib.contextmanager
def _os_lock(root: Path) -> Iterator[None]:
    """Cross-process advisory lock; a process crash releases the OS lock."""
    path = local(root, LOCK_NAME, exists=False)
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            # Another holder's byte lock refuses a read of that byte, so the
            # file is sized rather than read before locking. LK_LOCK gives up
            # after ten one-second attempts with a permission error; the POSIX
            # branch waits, so wait here as well.
            if os.fstat(stream.fileno()).st_size == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            while True:
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(0.05)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def object_store(run: Path, raw: bytes) -> str:
    key = digest(raw)
    path = local(run, "objects/" + key, exists=False)
    if path.exists():
        if read(path) != raw:
            raise ValueError("content-addressed object is corrupt")
    else:
        atomic(path, raw)
    return key


def object_read(run: Path, key: str) -> bytes:
    raw = read(local(run, "objects/" + sha(key)))
    if digest(raw) != key:
        raise ValueError("content-addressed object hash mismatch")
    return raw


def new_run_id() -> str:
    """Generate a time-ordered UUID using the UUIDv7 bit layout."""
    import secrets
    import time
    import uuid
    milliseconds = time.time_ns() // 1_000_000
    bits = ((milliseconds & ((1 << 48) - 1)) << 80) | (7 << 76)
    bits |= secrets.randbits(12) << 64
    bits |= (2 << 62) | secrets.randbits(62)
    return str(uuid.UUID(int=bits))
