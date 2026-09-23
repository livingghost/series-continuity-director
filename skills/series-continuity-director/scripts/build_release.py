#!/usr/bin/env python3
"""Build and verify a deterministic Series Continuity Director release ZIP.

The build copies the Git-tracked release members into a stage and runs
validate_skill.py on the stage once. It then zips the stage, extracts the
archive, and compares every extracted file with the stage byte for byte.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tree_layout import require_repository_root  # noqa: E402

# The archive mirrors the repository, so the release is built from the repository
# root and the extracted tree has the same shape as a checkout. A script inside it
# then resolves both roots exactly as it does here.
ROOT = require_repository_root()
EXCLUDED_NAMES = {"__pycache__", ".DS_Store", ".pytest_cache", ".git"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tmp", ".bak"}


def load_manifest(root: Path = ROOT) -> dict[str, Any]:
    with (root / "package-manifest.toml").open("rb") as handle:
        return tomllib.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def should_exclude(relative: Path) -> bool:
    if any(part in EXCLUDED_NAMES for part in relative.parts):
        return True
    if relative.suffix.lower() in EXCLUDED_SUFFIXES or relative.name.endswith("~"):
        return True
    return False


def git_file_list(source: Path, *arguments: str) -> set[Path]:
    proc = subprocess.run(
        ["git", "-C", str(source), "ls-files", "-z", *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "release builds require a Git worktree with an explicit tracked file set: "
            + proc.stderr.decode("utf-8", errors="replace").strip()
        )
    return {
        Path(item.decode("utf-8"))
        for item in proc.stdout.split(b"\0")
        if item
    }


def is_release_include(relative: Path, includes: list[str]) -> bool:
    return any(
        relative == Path(item) or Path(item) in relative.parents
        for item in includes
    )


def copy_release_tree(
    source: Path,
    destination: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=False)
    includes = manifest["release"]["include"]
    tracked = git_file_list(source)
    selected = sorted(
        (
            relative for relative in tracked
            if is_release_include(relative, includes) and not should_exclude(relative)
        ),
        key=lambda value: value.as_posix(),
    )
    for rel in includes:
        src = source / rel
        if not src.exists():
            raise FileNotFoundError(src)
        rel_path = Path(rel)
        if src.is_file() and rel_path not in selected:
            raise RuntimeError(f"release include is not tracked by Git: {rel}")
        if src.is_dir() and not any(rel_path in item.parents for item in selected):
            raise RuntimeError(f"release include contains no tracked files: {rel}")
    for relative in selected:
        src = source / relative
        if not src.is_file():
            raise RuntimeError(f"tracked release member is not a file: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)

    local_untracked = git_file_list(source, "--others", "--exclude-standard")
    local_ignored = git_file_list(source, "--others", "--ignored", "--exclude-standard")
    excluded_local = sorted(
        {
            relative.as_posix()
            for relative in local_untracked | local_ignored
            if is_release_include(relative, includes)
        }
    )
    return {
        "tracked_members": [item.as_posix() for item in selected],
        "excluded_local_files": excluded_local,
    }


def validate_stage(stage: Path, reports_dir: Path, suite: str) -> dict[str, Any]:
    """Run every repository check once, on exactly the files the archive will hold.

    The aggregate runs the release contract, its regressions, every validator
    and every smoke test. Its progress streams to this process's standard error
    as each check finishes, and its JSON report goes to the reports directory.
    """

    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run(
        [sys.executable, f"{suite}/scripts/validate_skill.py"], cwd=stage, env=env,
        stdout=subprocess.PIPE, stderr=None, encoding="utf-8", errors="replace", check=False,
    )
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        report = {"ok": False, "errors": ["validate_skill.py printed no JSON report"], "stdout": proc.stdout}
    path = reports_dir / "staged-skill.json"
    write_json(path, report)
    if proc.returncode != 0 or report.get("ok") is not True:
        raise RuntimeError(f"the staged tree failed validation; the report is {path}")
    return report


def tree_files(root: Path) -> dict[str, Path]:
    return {path.relative_to(root).as_posix(): path for path in root.rglob("*") if path.is_file()}


def compare_trees(staged: Path, extracted: Path) -> list[str]:
    """Every difference between the validated stage and what the archive gives back.

    Equal names and equal bytes mean the extracted tree is the tree that passed
    validation, so the checks are not run a second time on it.
    """

    expected, found = tree_files(staged), tree_files(extracted)
    problems = [f"absent from the extracted archive: {name}" for name in sorted(expected.keys() - found.keys())]
    problems += [f"not in the staged tree: {name}" for name in sorted(found.keys() - expected.keys())]
    problems += [
        f"bytes differ from the staged tree: {name}"
        for name in sorted(expected.keys() & found.keys())
        if expected[name].read_bytes() != found[name].read_bytes()
    ]
    return problems


def write_deterministic_zip(source_root: Path, output: Path) -> None:
    prefix = source_root.name
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.unlink(missing_ok=True)
    with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        directories = {Path(prefix)}
        for path in source_root.rglob("*"):
            rel = Path(prefix) / path.relative_to(source_root)
            if path.is_dir():
                directories.add(rel)
            else:
                directories.update(parent for parent in rel.parents if parent != Path("."))
        for directory in sorted(directories, key=lambda value: (len(value.parts), value.as_posix())):
            info = zipfile.ZipInfo(directory.as_posix().rstrip("/") + "/", date_time=(1980, 1, 1, 0, 0, 0))
            # ZipInfo otherwise records a host-specific creator value in the
            # central directory, making identical archives differ by OS.
            info.create_system = 3
            info.external_attr = ((stat.S_IFDIR | 0o755) & 0xFFFF) << 16
            info.external_attr |= 0x10
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, b"")
        # Sort on the POSIX relative path, not the Path object: Path comparison
        # folds case on Windows and does not on POSIX, which would order archive
        # members differently per platform and break byte-identical rebuilds.
        files = (p for p in source_root.rglob("*") if p.is_file())
        for path in sorted(files, key=lambda value: value.relative_to(source_root).as_posix()):
            rel = Path(prefix) / path.relative_to(source_root)
            info = zipfile.ZipInfo(rel.as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            # Scripts are invoked through the Python interpreter; all regular
            # files use one canonical 0644 mode for host-independent archives.
            info.external_attr = ((stat.S_IFREG | 0o644) & 0xFFFF) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    temp.replace(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(ROOT))
    parser.add_argument("--out", required=True)
    parser.add_argument("--reports-dir", required=True)
    parser.add_argument("--keep-stage")
    args = parser.parse_args(argv)

    source = Path(args.source).resolve()
    output = Path(args.out).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(source)
    from release_contract import check as check_release_contract
    identity = check_release_contract(source)
    if not identity["ok"]:
        raise ValueError("invalid product release identity: " + "; ".join(identity["errors"]))
    name = manifest["package"]["name"]
    version = manifest["package"]["version"]
    prefix = name
    suite = manifest["hosts"]["suite_root"]

    with tempfile.TemporaryDirectory(prefix="scd-release-") as temp:
        temp_root = Path(temp)
        stage = temp_root / prefix
        membership = copy_release_tree(source, stage, manifest)
        # A stale generated file fails here rather than being regenerated
        # before packaging: the aggregate runs every generator's --check.
        validate_stage(stage, reports_dir, suite)
        write_deterministic_zip(stage, output)

        with zipfile.ZipFile(output) as archive:
            corrupt = archive.testzip()
            members = archive.namelist()
            if corrupt:
                raise RuntimeError(f"corrupt ZIP member: {corrupt}")
            top_levels = sorted({Path(name).parts[0] for name in members if Path(name).parts})
            forbidden = [name for name in members if should_exclude(Path(name))]
            if top_levels != [name]:
                raise RuntimeError(f"unexpected top-level folders: {top_levels}")
            if forbidden:
                raise RuntimeError(f"forbidden archive members: {forbidden}")
            extract_root = temp_root / "extracted"
            archive.extractall(extract_root)

        extracted = extract_root / name
        differences = compare_trees(stage, extracted)
        write_json(reports_dir / "extracted-comparison.json", {
            "ok": not differences, "compared_with": "the validated staged tree",
            "files": len(tree_files(extracted)), "differences": differences,
        })
        if differences:
            raise RuntimeError("the extracted archive differs from the validated stage: " + "; ".join(differences[:10]))

        if args.keep_stage:
            keep = Path(args.keep_stage).resolve()
            if keep.exists():
                shutil.rmtree(keep)
            shutil.copytree(stage, keep)

    digest = sha256_file(output)
    sha_path = output.with_suffix(output.suffix + ".sha256")
    sha_path.write_text(f"{digest}  {output.name}\n", encoding="utf-8", newline="\n")

    with zipfile.ZipFile(output) as archive:
        members = archive.namelist()
        # The raw ZIP digest depends on the deflate implementation, which varies
        # between zlib builds. This digest covers member names and their
        # decompressed bytes, so it is comparable across platforms.
        content = hashlib.sha256()
        for member in members:
            content.update(member.encode("utf-8"))
            if not member.endswith("/"):
                content.update(hashlib.sha256(archive.read(member)).digest())
    archive_check = {
        "package": name,
        "version": version,
        "archive": str(output),
        "sha256": digest,
        "content_sha256": content.hexdigest(),
        "member_count": len(members),
        "top_level_folders": sorted({Path(member).parts[0] for member in members if Path(member).parts}),
        "forbidden_members": [member for member in members if should_exclude(Path(member))],
        "tracked_source_members": membership["tracked_members"],
        "local_files_excluded_from_release": membership["excluded_local_files"],
        "changelog_present": any(Path(member).name == "CHANGELOG.md" for member in members),
        "generated_media_quality": "not evaluated",
        "ok": True,
    }
    write_json(reports_dir / "archive-check.json", archive_check)
    summary = {
        "package": name,
        "version": version,
        "archive": str(output),
        "sha256_file": str(sha_path),
        "reports_dir": str(reports_dir),
        "ok": True,
    }
    write_json(reports_dir / "package-summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
