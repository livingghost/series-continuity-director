#!/usr/bin/env python3
"""Validate Series Continuity Director source, protocols, example, and adapters.

The static checks read the tree in this process. Every command in CHECKS runs
as its own process, several at a time, and the report lists them in the order
they are declared. The report is JSON on standard output. Progress, failure
output and warnings go to standard error, one line per finished check.
"""
from __future__ import annotations

import sys

# The static checks read the tree while the commands run beside them, so this
# process writes no bytecode into it either.
sys.dont_write_bytecode = True

import argparse  # noqa: E402
import ast  # noqa: E402
import fnmatch  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import py_compile  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import tomllib  # noqa: E402
import traceback  # noqa: E402
import unicodedata  # noqa: E402
from concurrent.futures import Future, ThreadPoolExecutor, as_completed  # noqa: E402
from contextlib import nullcontext  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402
from pathlib import Path  # noqa: E402
from urllib.parse import unquote  # noqa: E402

import narrative_corpus  # noqa: E402
import refusal_coverage  # noqa: E402
from project_layout import NARRATIVE_SUBDIRECTORIES, STATE_SUBDIRECTORIES  # noqa: E402
from state_protocol import unsupported_schema_keywords as unsupported_state_schema_keywords  # noqa: E402
from validate_test_cases import EDITORIAL_CASE_NUMBERS, EXECUTED_CASE_NUMBERS  # noqa: E402
from viewpoint_protocol import unsupported_schema_keywords as unsupported_viewpoint_schema_keywords  # noqa: E402

from tree_layout import (  # noqa: E402
    REPO_FILES,
    SUITE,
    check_layout,
    require_repository_root,
)

# The suite. The repository above it is resolved once, below.
ROOT = SUITE
FORBIDDEN_PUNCTUATION = {"\u2014": "Unicode em dash", "\u2013": "Unicode en dash"}

EXCLUDED_PARTS = {"__pycache__", ".git", ".pytest_cache", "dist"}
# A host keeps its own session data at the repository root, such as the
# worktrees an agent host creates under .claude/. None of it is a release member.
HOST_LOCAL_ROOTS = {".claude"}
EXPECTED_KNOWLEDGE_SOURCES = [
    "references/scene-persona.md",
    "references/source-material.md",
    "references/agent-evaluation.md",
    "references/repair-analysis.md",
    "references/narrative-authoring.md",
    "references/creative-options.md",
    "references/evidence-review.md",
    "references/production-direction.md",
    "references/production-execution.md",
    "references/tactic-consultation.md",
    "references/production-repair.md",
    "references/timed-production.md",

    "references/state-and-trust.md",
    "references/continuity-core.md",
    "references/story-structure.md",
    "references/visual-language.md",
    "references/scoped-lexicon.md",
    "references/temporal-state.md",
    "references/runtime-capabilities.md",
    "references/viewpoint-profiles.md",
    "references/third-person-camera.md",
    "references/first-person-camera.md",
    "references/blocking-and-coverage.md",
    "references/viewpoint-transitions.md",
    "references/shot-continuity.md",
    "references/prompt-composition.md",
    "references/operational-distinctions.md",
    "references/model-facing-artifacts.md",
    "references/target-adaptation.md",
    "references/contact-scenes.md",
    "references/performance-details.md",
    "references/atmosphere-quality.md",
    "references/dialogue-and-audio.md",
    "references/post-production.md",
    "references/visual-contracts.md",
    "references/morphology-and-species-contracts.md",
    "references/templates.md",
]




def carried_implementation_hashes(document: str) -> dict[str, str]:
    """The hashes the narrative contract publishes for the files that answer it."""

    found: dict[str, str] = {}
    for line in document.split(chr(10)):
        parts = line.split()
        if len(parts) == 2 and parts[0].startswith("scripts/") and len(parts[1]) == 64:
            found[parts[0]] = parts[1]
    return found


def check_carried_implementation(root, contract_relative, errors) -> None:
    """The reader that answers the contract, against the hash the contract publishes.

    An installation reads only itself, so nothing here can compare this copy of
    the reader with a copy anywhere else. What it can do is check that the reader
    and the document stating its rules were changed together, which is what keeps
    an edit to one from drifting away from the other in silence.
    """

    contract = root / contract_relative
    if not contract.is_file():
        errors.append(f"the narrative contract is missing: {contract_relative}")
        return
    published = carried_implementation_hashes(contract.read_text(encoding="utf-8"))
    if not published:
        errors.append(f"{contract_relative} publishes no implementation hashes")
        return
    for relative, expected in sorted(published.items()):
        path = root / relative
        if not path.is_file():
            errors.append(f"{contract_relative} publishes a hash for {relative}, which is absent")
            continue
        found = hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if found != expected:
            errors.append(
                f"{relative} does not match the hash the narrative contract publishes: "
                f"{found[:12]} against {expected[:12]}; the reader and the document that publishes "
                "its hash travel together, and an edit to one has to travel with the other"
            )

PUBLISHED_BLOCK = re.compile(
    "```text" + chr(10) + "(?:scripts/\\S+[ \\t]+[0-9a-f]{64}" + chr(10) + ")+```" + chr(10))


def contract_digest(document: str) -> str:
    """The contract over everything except the block that publishes reader hashes.

    The reader carries this document's hash and this document carries the
    reader's, which cannot both be computed unless one of them is taken over
    less than the whole. The protocol already cuts that way: `content_sha256`
    is taken with the `approved` block removed, because an approval cannot be
    part of what it approves. A published hash cannot be part of what it
    publishes either.
    """

    stripped = PUBLISHED_BLOCK.sub("", document.replace(chr(13) + chr(10), chr(10)))
    return hashlib.sha256(stripped.encode("utf-8")).hexdigest()


def check_contract_document(root, contract_relative, errors) -> None:
    """The contract document, against the hash the reader that answers it carries.

    Two copies of this contract are meant to be the same document. Nothing here
    can see the other copy, but both copies carry a reader whose hash this
    document publishes, and that reader names the hash of this document, so a
    copy edited on one side stops matching its own reader and is refused where
    it was edited rather than diverging in silence.
    """

    contract = root / contract_relative
    reader = root / "scripts" / "narrative.py"
    if not contract.is_file() or not reader.is_file():
        return
    text = reader.read_text(encoding="utf-8")
    match = re.search(r"(?m)^CONTRACT_SHA256 = \"([0-9a-f]{64})\"$", text)
    if not match:
        errors.append("scripts/narrative.py publishes no CONTRACT_SHA256 for the contract it answers")
        return
    found = contract_digest(contract.read_text(encoding="utf-8"))
    if found != match.group(1):
        errors.append(
            f"{contract_relative} does not match the hash its reader carries: "
            f"{found[:12]} against {match.group(1)[:12]}; the contract and the reader that "
            "answers it travel together, and an edit to one has to travel with the other"
        )


STATIC = "static"
# The Agent Skills specification states that a loaded SKILL.md body stays under
# this many tokens.
TOKEN_BUDGET = 5000


@dataclass(frozen=True)
class Check:
    """A command the aggregate runs, under the name `--only` and `--list` use.

    Each step is a script path relative to the suite, then its arguments. The
    steps run in order, and `{temp}` in an argument names one fresh temporary
    directory the steps share. A check writes only into temporary directories
    of its own, so any two checks can run at the same time. `alone` states why
    a check cannot, and such a check runs by itself after the others.
    """

    name: str
    steps: tuple[tuple[str, ...], ...]
    alone: str = ""


def command(*argv: str) -> Check:
    return Check(" ".join(argv), (argv,))


# Generated outputs, protocol validators and every smoke test. Each check is
# declared once, and the release build runs all of them on the staged tree.
CHECKS: tuple[Check, ...] = (
    command("scripts/dependencies_smoke_test.py"),
    command("scripts/release_management_smoke_test.py"),
    command("scripts/release_contract.py"),
    command("scripts/readme_smoke_test.py"),
    command("scripts/scene_material_smoke_test.py"),
    command("scripts/agent_evaluation_smoke_test.py"),
    command("scripts/resource_handling_smoke_test.py"),
    command("scripts/evidence_tools_smoke_test.py"),
    command("scripts/creative_options_smoke_test.py"),
    command("scripts/dependencies.py", "--scope", "media"),
    command("scripts/production_direction_smoke_test.py"),
    command("scripts/production_workflow_smoke_test.py"),
    command("scripts/production_resume_smoke_test.py"),
    command("scripts/production_inputs_smoke_test.py"),
    command("scripts/tactic_consultation_smoke_test.py"),
    command("examples/tactic-consultation/build_example.py", "--check"),
    command("scripts/production_input_model_smoke_test.py"),
    command("scripts/dispatch_preview_smoke_test.py"),
    command("scripts/schema_observation_smoke_test.py"),
    command("examples/model-evidence/build_example.py", "--check"),
    command("scripts/production_variation_smoke_test.py"),
    command("scripts/route_reading_smoke_test.py"),
    command("scripts/visual_continuity_smoke_test.py"),
    command("scripts/request_contract_smoke_test.py"),
    command("scripts/request_validation_smoke_test.py"),
    command("scripts/reservation_lifecycle_smoke_test.py"),
    command("scripts/reference_activation_gate_smoke_test.py"),
    command("examples/input-assembly/build_example.py", "--check"),
    command("examples/submission-gate/build_example.py", "--check"),
    command("examples/resume-recording/build_example.py", "--check"),
    command("scripts/production_integrity_smoke_test.py"),
    command("scripts/production_dispatch_smoke_test.py"),
    command("scripts/timed_sequence_smoke_test.py"),
    command("scripts/production_examples_smoke_test.py"),
    command("scripts/build_resources.py", "--check"),
    command("scripts/layer_boundaries_smoke_test.py"),
    command("scripts/public_boundary_smoke_test.py"),
    command("scripts/protocol_contract_smoke_test.py"),
    command("scripts/project_workflow_smoke_test.py"),
    command("scripts/build_example.py", "--check"),
    command("scripts/build_flat.py", "--check"),
    command("scripts/validate_state_protocol.py"),
    command("scripts/validate_viewpoint_protocol.py"),
    command("scripts/validate_target_protocol.py"),
    command("scripts/validate_integration.py"),
    command("scripts/validate_test_cases.py"),
    command("scripts/validate_knowledge_integrity.py"),
    command("scripts/submission_gate_smoke_test.py"),
    command("scripts/narrative_smoke_test.py"),
    command("scripts/scene_plot_smoke_test.py"),
    command("scripts/narrative_index_smoke_test.py"),
    command("scripts/asset_registry_smoke_test.py"),
    command("scripts/build_host_packages.py", "--check"),
    command("scripts/build_host_packages_smoke_test.py"),
    command("scripts/validate_host_manifests.py"),
    command("scripts/host_manifest_smoke_test.py"),
    command("scripts/cli_encoding_smoke_test.py"),
    command("scripts/report_output_smoke_test.py"),

    # The project scaffold and its validator are current public interfaces.
    Check("project scaffold", (
        ("scripts/init_project.py", "--out", "{temp}/validation-series",
         "--series-id", "VALIDATION-SERIES", "--title", "Validation Series"),
        ("scripts/validate_project.py", "{temp}/validation-series"),
    )),
)

# Smoke tests the aggregate leaves out, each mapped to the reason. Every other
# scripts/*_smoke_test.py has to be a check above.
UNLISTED_SMOKE_TESTS: dict[str, str] = {}


@dataclass
class Outcome:
    name: str
    returncode: int
    # The failing step's command line and output, written for a person.
    output: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def run_check(check: Check) -> Outcome:
    """Run the steps of one check in order, stopping at the first that fails."""

    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    uses_temp = any("{temp}" in part for step in check.steps for part in step)
    with (tempfile.TemporaryDirectory(prefix="scd-check-") if uses_temp else nullcontext("")) as temp:
        for step in check.steps:
            argv = [sys.executable, *(part.replace("{temp}", temp) for part in step)]
            # A child may write in the console's code page or in UTF-8; either
            # decodes here without stopping the run.
            proc = subprocess.run(
                argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                encoding="utf-8", errors="replace", check=False,
            )
            if proc.returncode != 0:
                sections = [f"$ python {' '.join(argv[1:])}", f"exit status {proc.returncode}"]
                for label, text in (("standard output", proc.stdout), ("standard error", proc.stderr)):
                    if text.strip():
                        sections.append(f"--- {label} ---\n{text.rstrip()}")
                return Outcome(
                    check.name, proc.returncode, "\n".join(sections),
                    [f"command failed: {check.name}\n{proc.stderr or proc.stdout}"],
                )
    return Outcome(check.name, 0)


def select(patterns: list[str] | None) -> tuple[bool, list[Check]]:
    """Whether the static checks run, and which commands, in declared order."""

    if not patterns:
        return True, list(CHECKS)
    names = [STATIC, *(check.name for check in CHECKS)]
    chosen: set[str] = set()
    for pattern in patterns:
        matched = [name for name in names if name == pattern or fnmatch.fnmatchcase(name, pattern)]
        if not matched:
            raise ValueError(f"no check is named {pattern!r}; --list prints the names")
        chosen.update(matched)
    return STATIC in chosen, [check for check in CHECKS if check.name in chosen]


def smoke_test_coverage(errors: list[str]) -> None:
    """Every smoke test on disk is a check, or is left out with a stated reason."""

    present = {path.name for path in (ROOT / "scripts").glob("*_smoke_test.py")}
    listed = {
        Path(step[0]).name for check in CHECKS for step in check.steps
        if step[0].startswith("scripts/")
    }
    for name in sorted(present - listed - set(UNLISTED_SMOKE_TESTS)):
        errors.append(
            f"scripts/{name} runs nowhere: add it to CHECKS in scripts/validate_skill.py, "
            "or to UNLISTED_SMOKE_TESTS with the reason it is left out"
        )
    for name, reason in sorted(UNLISTED_SMOKE_TESTS.items()):
        if name in listed:
            errors.append(f"scripts/{name} is both a check and left out in UNLISTED_SMOKE_TESTS")
        if name not in present:
            errors.append(f"UNLISTED_SMOKE_TESTS names scripts/{name}, which does not exist")
        if not reason.strip():
            errors.append(f"UNLISTED_SMOKE_TESTS leaves out scripts/{name} without a reason")


def tree_state(repo: Path, includes: list[str]) -> dict[str, tuple[int, int]]:
    """Size and modification time of every file the release ships.

    A check writes only into its own temporary directories. Comparing this
    state before and after the run is what establishes that for the checks
    running side by side.
    """

    state: dict[str, tuple[int, int]] = {}
    for item in includes:
        base = repo / item
        paths = [base] if base.is_file() else base.rglob("*") if base.is_dir() else []
        for path in paths:
            relative = path.relative_to(repo)
            if any(part in EXCLUDED_PARTS for part in relative.parts) or not path.is_file():
                continue
            status = path.stat()
            state[relative.as_posix()] = (status.st_size, status.st_mtime_ns)
    return state


class Progress:
    """One line per finished check on standard error, and readable failures.

    Under GitHub Actions a failure's output folds into a group and each error
    becomes an annotation on the run.
    """

    def __init__(self, total: int) -> None:
        self.total = total
        self.done = 0
        self.github = bool(os.environ.get("GITHUB_ACTIONS"))

    @staticmethod
    def escape(text: str) -> str:
        return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")

    def emit(self, line: str = "") -> None:
        print(line, file=sys.stderr, flush=True)

    def finished(self, outcome: Outcome) -> None:
        self.done += 1
        width = len(str(self.total))
        state = "pass" if outcome.returncode == 0 else "FAIL"
        self.emit(f"[{self.done:>{width}}/{self.total}] {state} {outcome.name}")
        if outcome.returncode == 0 or not outcome.output:
            return
        self.emit("::group::" + outcome.name if self.github else f"----- {outcome.name} -----")
        self.emit(outcome.output)
        self.emit("::endgroup::" if self.github else f"----- end of {outcome.name} -----")

    def report(self, errors: list[str], warnings: list[str]) -> None:
        """Each message on one line, after the progress lines."""

        for message in warnings:
            self.emit(("::warning::" + self.escape(message)) if self.github else "warning: " + message)
        for message in errors:
            self.emit(("::error::" + self.escape(message)) if self.github else "error: " + message)


def read_text(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append(f"{path.relative_to(ROOT)}: text file is not UTF-8")
        return ""


def markdown_links(text: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"!?(?:\[[^\]]*\])\(([^)]+)\)", text)]


def markdown_headings(text: str, level: int = 2) -> list[str]:
    prefix = "#" * level + " "
    headings: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and line.startswith(prefix):
            headings.append(line[len(prefix):].strip())
    return headings


def normalized_heading(value: str) -> str:
    return re.sub(r"^\d+\.\s*", "", value).strip().casefold()



def non_english_characters(text: str) -> dict[int, str]:
    """Map each line number to the characters on it written in another script.

    A letter outside the Latin script, or a punctuation mark from the CJK and
    fullwidth blocks, marks text that is not English, whichever language it
    is. Accented Latin letters, symbols and typographic punctuation pass, so a
    name such as Zoë or a section sign is not an error.
    """

    found: dict[int, str] = {}
    for number, line in enumerate(text.splitlines(), 1):
        characters = ""
        for character in line:
            code_point = ord(character)
            if code_point < 0x80 or character in characters:
                continue
            foreign_letter = (
                unicodedata.category(character).startswith("L")
                and not unicodedata.name(character, "").startswith("LATIN")
            )
            cjk_punctuation = (
                0x3000 <= code_point <= 0x303F
                or 0xFE30 <= code_point <= 0xFE4F
                or 0xFF00 <= code_point <= 0xFFEF
            )
            if foreign_letter or cjk_punctuation:
                characters += character
        if characters:
            found[number] = characters
    return found


def english_instruction_document(repo: Path, path: Path) -> bool:
    """Whether a text file is an instruction document that must be English.

    The root README, CONTRIBUTING and CHANGELOG, and every Markdown document
    and the agent manifest inside the suite, except the project templates and
    the worked example. A persona form under the templates carries exact
    forms in a character's language by design.
    """

    if path.suffix.lower() != ".md" and path.name != "openai.yaml":
        return False
    if path.parent == repo:
        return True
    if not path.is_relative_to(ROOT):
        return False
    return path.relative_to(ROOT).parts[0] not in {"assets", "examples"}


def static_checks(repo: Path, manifest: dict) -> tuple[list[str], list[str], dict]:
    """Every check that reads the tree in this process, with its errors, warnings and stats."""

    errors: list[str] = []
    warnings: list[str] = []
    stats: dict = {}

    # The declared shape, compared against the tree.
    errors.extend(check_layout(repo))

    package = manifest.get("package", {})
    if package.get("name") != "series-continuity-director":
        errors.append("package.name must be series-continuity-director")
    version = str(package.get("version") or "")
    from release_contract import validate_metadata, validate_changelog
    errors.extend(validate_metadata(manifest))

    skill = read_text(ROOT / "SKILL.md", errors)
    # Distribution identity is owned by package-manifest.toml; generated host metadata reads it.
    if not re.search(r'^name:\s*series-continuity-director\s*$', skill, re.MULTILINE):
        errors.append("SKILL.md name must be series-continuity-director")

    # The Agent Skills specification caps `name` at 64 characters and
    # `description` at 1024, and recommends a body under 500 lines because a host
    # loads all of it once the skill activates. A host refuses the first two, and
    # no repository check said so until here.
    for field, cap in (("name", 64), ("description", 1024)):
        found = re.search(rf"^{field}:\s*(.+)$", skill, re.MULTILINE)
        if found and len(found.group(1).strip()) > cap:
            errors.append(
                f"SKILL.md {field} is {len(found.group(1).strip())} characters; "
                f"the specification caps it at {cap}"
            )
    # The body is what follows the closing frontmatter delimiter, and the
    # delimiter is a line of its own. Splitting on the substring would cut at a
    # triple dash inside a value.
    body = re.split(r"(?m)^---\s*$", skill, maxsplit=2)
    body_lines = len(body[-1].splitlines())
    stats["skill_body_lines"] = body_lines
    # Body length is observable, not a release failure. A recommended length
    # cannot establish whether a reader has the explanations needed to use it.
    # No tokenizer ships here, so four characters per token stands in for one,
    # and the stat and the warning both say it is an estimate.
    estimated_tokens = -(-len(body[-1]) // 4)
    stats["skill_body_tokens_estimate"] = estimated_tokens
    if estimated_tokens > TOKEN_BUDGET:
        warnings.append(
            f"SKILL.md body is an estimated {estimated_tokens} tokens (characters / 4); "
            f"the specification states under {TOKEN_BUDGET}"
        )
    agent = read_text(ROOT / "agents" / "openai.yaml", errors)
    for key in ("interface:", "policy:"):
        if key not in agent:
            errors.append(f"agents/openai.yaml must declare {key.rstrip(':')}")
    capability_path = ROOT / "protocols" / "interchange" / "integration-capabilities.json"
    try:
        capabilities = json.loads(capability_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"protocols/interchange/integration-capabilities.json: {exc}")
    else:
        from integration_contract import validate_capabilities
        errors.extend(validate_capabilities(capabilities)["errors"])

    changelog_path = repo / "CHANGELOG.md"
    if not changelog_path.is_file():
        errors.append("missing required root file: CHANGELOG.md")
    else:
        changelog = read_text(changelog_path, errors)
        errors.extend(validate_changelog(changelog, version, style="dated"))

    release_output = manifest.get("release", {}).get("output")
    expected_release = f"dist/series-continuity-director-{version}.zip"
    if release_output != expected_release:
        errors.append(f"release.output must be {expected_release}")
    readme = read_text(repo / "README.md", errors)
    if re.search(r"(?m)^# Series Continuity Director$", readme) is None:
        errors.append("README must use the stable product heading without embedding the release version")

    # Both workflows run the release build, which runs every check on the staged
    # tree, and publication binds the tag to the product version. A release
    # archive carries no workflows, so this reads them only in a checkout.
    workflows = repo / ".github" / "workflows"
    for name in ("ci.yml", "release.yml"):
        if (workflows / name).is_file():
            text = read_text(workflows / name, errors)
            if "scripts/build_release.py" not in text:
                errors.append(f".github/workflows/{name} must run scripts/build_release.py")
            if name == "release.yml" and 'release_contract.py --tag "$GITHUB_REF_NAME"' not in text:
                errors.append(".github/workflows/release.yml must bind the tag with release_contract.py --tag")

    for rel in REPO_FILES:
        if not (repo / rel).is_file():
            errors.append(f"missing required repository file: {rel}")
    for rel in ("protocols/shared-state", "protocols/viewpoint"):
        if not (ROOT / rel).is_dir():
            errors.append(f"missing canonical unversioned protocol directory: {rel}")

    sources = manifest.get("knowledge", {}).get("sources", [])
    if not isinstance(sources, list):
        errors.append("knowledge.sources must be a list")
        sources = []
    elif sources != EXPECTED_KNOWLEDGE_SOURCES:
        errors.append("knowledge.sources must equal the canonical runtime reference list in order")
    if len(sources) != len(set(sources)):
        errors.append("knowledge.sources contains duplicates")
    for rel in sources:
        if not isinstance(rel, str) or not rel.startswith("references/") or not (ROOT / rel).is_file():
            errors.append(f"invalid knowledge source: {rel}")

    # One flat adapter, built from SKILL.md plus every knowledge source plus the
    # canonical example and test cases. The worked director package is the piece
    # an operator most needs to see, so it belongs in the adapter a host reads.
    flat = manifest.get("flat", {})
    expected = [
        "SKILL.md",
        *sources,
        "examples/mixed-viewpoint-workshop/README.md",
        "examples/mixed-viewpoint-workshop/director-package.md",
        "examples/test-cases.md",
    ]
    if flat.get("sources") != expected:
        errors.append("flat.sources must equal SKILL.md, every knowledge source in order, then the canonical example and test cases")
    output = flat.get("output")
    if not isinstance(output, str) or not (ROOT / output).is_file():
        errors.append("flat.output is missing")
    else:
        from build_flat import render as render_flat
        try:
            if (ROOT / output).read_text(encoding="utf-8") != render_flat(ROOT, manifest):
                errors.append("flat.output differs from its complete declared sources; regenerate the adapter")
        except (OSError, ValueError, KeyError) as exc:
            errors.append("flat adapter source validation failed: " + str(exc))

    # Text scan.
    text_files = 0
    markdown_files = 0
    repository_link_errors = 0
    # Links are checked across the whole repository, not only the suite.
    for path in sorted(repo.rglob("*")):
        relative_parts = path.relative_to(repo).parts
        if (not path.is_file() or any(part in EXCLUDED_PARTS for part in relative_parts)
                or relative_parts[0] in HOST_LOCAL_ROOTS):
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".zip"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        text_files += 1
        # Punctuation style checks bind shipped structural text.
        # Repository controls and plans are not shipped and are not bound by them.
        if path.is_relative_to(ROOT):
            for token, label in FORBIDDEN_PUNCTUATION.items():
                if token in text:
                    errors.append(f"{path.relative_to(repo)}: contains {label}")
        # Instruction documents are English, whatever the other language is.
        if english_instruction_document(repo, path):
            found = non_english_characters(text)
            if found:
                number, characters = next(iter(found.items()))
                errors.append(
                    f"{path.relative_to(repo)}:{number}: instruction document is not English ({characters})"
                )
        if path.suffix.lower() == ".md":
            markdown_files += 1
            for raw in markdown_links(text):
                if not raw or raw.startswith(("#", "http://", "https://", "mailto:", "data:")):
                    continue
                target_text = unquote(raw.split("#", 1)[0])
                target = (path.parent / target_text).resolve()
                try:
                    target.relative_to(repo.resolve())
                except ValueError:
                    errors.append(f"{path.relative_to(repo)}: repository-relative link escapes the repository: {raw}")
                    repository_link_errors += 1
                    continue
                if not target.exists():
                    errors.append(f"{path.relative_to(repo)}: broken repository-relative link: {raw}")
                    repository_link_errors += 1

    # JSON and JSONL parsing.
    json_files = 0
    jsonl_records = 0
    for path in sorted(ROOT.rglob("*.json")):
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        json_files += 1
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
    for path in sorted(ROOT.rglob("*.jsonl")):
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                value = json.loads(line)
                jsonl_records += 1
            except Exception as exc:
                errors.append(f"{path.relative_to(ROOT)}:{line_number}: invalid JSONL: {exc}")

    # Lint every protocol schema statically. Instance-driven validation only
    # visits schemas and branches reached by shipped artifacts, so an unknown
    # constraint in an unused branch must still fail repository validation.
    for schema_dir, unsupported_keywords in (
        (ROOT / "protocols" / "shared-state" / "schemas", unsupported_state_schema_keywords),
        (ROOT / "protocols" / "viewpoint" / "schemas", unsupported_viewpoint_schema_keywords),
    ):
        for path in sorted(schema_dir.rglob("*.schema.json")):
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"{path.relative_to(ROOT)}: invalid JSON schema: {exc}")
                continue
            for finding in unsupported_keywords(document):
                errors.append(
                    f"{path.relative_to(ROOT)}: schema keyword is authored but never enforced at {finding}"
                )

    # Python syntax without leaving bytecode in the tree.
    python_files = 0
    with tempfile.TemporaryDirectory(prefix="scd-pyc-") as temp:
        temp_root = Path(temp)
        for path in sorted(ROOT.rglob("*.py")):
            if any(part in EXCLUDED_PARTS for part in path.parts):
                continue
            python_files += 1
            try:
                py_compile.compile(str(path), cfile=str(temp_root / f"{python_files}.pyc"), doraise=True)
            except py_compile.PyCompileError as exc:
                errors.append(f"{path.relative_to(ROOT)}: Python compile failed: {exc.msg}")

    # Declared optional imports belong to media operations. Core imports stay
    # available on a bare interpreter; the executable dependency test checks it.
    from dependencies import source_import_errors, declaration
    local_modules = {path.stem for path in (ROOT / "scripts").glob("*.py")}
    dependency_rules = declaration()
    for path in sorted((ROOT / "scripts").glob("*.py")):
        errors.extend(source_import_errors(path, dependency_rules, local_modules))

    # Every smoke test on disk runs, or is left out with its reason.
    smoke_test_coverage(errors)

    example_result = read_text(ROOT / "examples/mixed-viewpoint-workshop/result-log.md", errors)
    if not re.search(r"Run status:\s*not run", example_result, re.IGNORECASE):
        errors.append("canonical example result log must state Run status: not run")
    if re.search(r"accepted variant|returned variant|rendered successfully", example_result, re.IGNORECASE):
        errors.append("canonical not-run example must not claim returned output")

    tests = read_text(ROOT / "examples/test-cases.md", errors)
    case_matches = list(re.finditer(r"(?m)^##\s+(\d+)\.\s+.+$", tests))
    case_numbers = [int(match.group(1)) for match in case_matches]
    # The runner declares how many cases there are; this checks the catalog runs
    # to that number without a gap. Two counts written in two files drift.
    from validate_test_cases import CATALOG_CASES

    if case_numbers != list(range(1, CATALOG_CASES + 1)):
        errors.append(
            "examples/test-cases.md must contain sequential cases 1 through "
            f"{CATALOG_CASES}"
        )
    dispositions: dict[int, str] = {}
    for index, match in enumerate(case_matches):
        number = int(match.group(1))
        end = case_matches[index + 1].start() if index + 1 < len(case_matches) else len(tests)
        body = tests[match.end():end]
        markers = re.findall(r"(?m)^Enforcement:\s*(executed|editorial review)\s*$", body)
        if len(markers) != 1:
            errors.append(f"examples/test-cases.md case {number} must have exactly one Enforcement marker")
            continue
        dispositions[number] = markers[0]
    declared_executed = {number for number, mode in dispositions.items() if mode == "executed"}
    declared_editorial = {number for number, mode in dispositions.items() if mode == "editorial review"}
    if declared_executed != set(EXECUTED_CASE_NUMBERS):
        errors.append(
            "examples/test-cases.md executed markers differ from the executable/delegated case map: "
            f"missing={sorted(set(EXECUTED_CASE_NUMBERS) - declared_executed)} "
            f"extra={sorted(declared_executed - set(EXECUTED_CASE_NUMBERS))}"
        )
    if declared_editorial != set(EDITORIAL_CASE_NUMBERS):
        errors.append(
            "examples/test-cases.md editorial markers differ from the explicit review set: "
            f"missing={sorted(set(EDITORIAL_CASE_NUMBERS) - declared_editorial)} "
            f"extra={sorted(declared_editorial - set(EDITORIAL_CASE_NUMBERS))}"
        )
    missing_disposition = set(case_numbers) - declared_executed - declared_editorial
    if missing_disposition:
        errors.append(f"test cases have no disposition: {sorted(missing_disposition)}")

    # Reference structure and project-layout consistency.
    expected_reference_sections = {
        "references/atmosphere-quality.md": [
            "Environment as an acting system",
            "Weather carriers and body response",
            "Water and wet state",
            "Smoke, steam, dust, fog, and suspended material",
            "Light source, landing, and continuity",
            "Color stability in warm scenes",
            "Layered environmental density",
            "Viewpoint and atmosphere",
            "Night scenes",
            "Cultural, seasonal, and locale context",
            "Environment-driven appearance adaptation",
            "Image quality follows the approved visual language",
            "Atmosphere and quality review",
        ],
        "references/dialogue-and-audio.md": [
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
        "references/performance-details.md": [
            "Four performance states",
            "Observable performance channels and ownership",
            "Expression tiers",
            "Performance under viewpoint and focalization",
            "Stillness",
            "Idle pose, signature move, and recurring behavior",
            "Dialogue performance",
            "Relationship-specific performance",
            "Environmental performance",
            "Performance review",
            "Material and light as performance",
            "Choosing a performance from persona and intention",
            "Coordinated details and simultaneous actions",
            "Species and form vocabulary idea bank",
            "Large form-specific action in short segments",
        ],
        "references/contact-scenes.md": [
            "Universal contact record",
            "Viewpoint-specific staging",
            "Handoffs and transfers",
            "Hugs and body enclosure",
            "Face and near-face contact",
            "Carrying, lifting, and support",
            "Medical and care contact",
            "Combat and forced contact",
            "State, inventory, and canon",
            "Contact risk and camera choice",
            "Contact continuity review",
        ],
        "references/model-facing-artifacts.md": [
            "Keep production artifacts distinct",
            "Creative requirement transfer",
            "Preserve specificity by moving it, not deleting it",
            "Self-contained exact text",
            "Concise is not generic",
            "Media contribution record",
            "Viewpoint transfer",
            "The shot-request",
            "Explicit deferral",
            "Result evidence",
            "Artifact completion test",
            "Character reference sheet, and the order of regeneration",
        ],
        "references/runtime-capabilities.md": [
            "Evidence priority and freshness",
            "Separate fact, decision, and observation",
            "Operation card",
            "Supported operation families and required evidence",
            "Asset type, operation, and intended influence",
            "Input-combination proof",
            "Binding syntax",
            "Reusable target profile",
            "Clip packing",
            "Viewpoint and target operations",
            "Rejection diagnosis",
            "Operational packaging gate",
            "Services, models, and offerings",
        ],
        "references/target-adaptation.md": [
            "Define the irreducible shot",
            "Select the operation by the hardest evidence",
            "Rewrite according to submitted evidence",
            "Translate viewpoint into concrete target direction",
            "Prompt rewriting and hidden transformation",
            "Negative and exclusion fields",
            "Viewpoint-specific fallback",
            "State-specific fallback",
            "Adaptation trace",
            "Observable distinction test",
            "Target adaptation completion test",
        ],
        "references/first-person-camera.md": [
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
        "references/scoped-lexicon.md": [
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
        "references/operational-distinctions.md": [
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
        "references/story-structure.md": [
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
        "references/post-production.md": [
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
    }
    for rel, expected in expected_reference_sections.items():
        headings = markdown_headings(read_text(ROOT / rel, errors), 2)
        numbered = [re.sub(r"^\d+\.\s*", "", heading).strip() for heading in headings]
        if numbered != expected:
            errors.append(f"{rel}: canonical section structure drifted; expected {expected}, found {numbered}")

    # Section numbering binds every runtime reference, not only the ones above.
    # The map states what a particular file must say; this states that any of
    # them is still in order, so the rule reaches the file where the next section
    # is added rather than only the files somebody remembered to declare.
    for path in sorted((ROOT / "references").glob("*.md")):
        rel = f"references/{path.name}"
        seen: dict[str, int] = {}
        for index, heading in enumerate(markdown_headings(read_text(path, errors), 2), 1):
            match = re.fullmatch(r"(\d+)\.\s+(.+)", heading)
            if not match:
                errors.append(f"{rel}: level-2 section {heading!r} carries no number")
                continue
            if int(match.group(1)) != index:
                errors.append(
                    f"{rel}: section numbering must be continuous from 1; "
                    f"found {heading!r} at position {index}"
                )
            title = normalized_heading(heading)
            if title in seen:
                errors.append(
                    f"{rel}: level-2 heading {match.group(2)!r} repeats the title of section {seen[title]}"
                )
            else:
                seen[title] = index

    # Reachability. A reference nobody routes to is a file that was written and
    # is never read, and a command nobody documents is a command whose failure
    # nobody can reproduce. Neither has a threshold: the question is whether the
    # set is covered, and a single uncovered member is the answer.
    skill_text = read_text(ROOT / "SKILL.md", errors)
    # Routed means named in a routing table row, not mentioned anywhere in the
    # file. A name in a sentence tells a reader the document exists; a row tells
    # them when to open it.
    routing_rows = [
        line for line in skill_text.splitlines()
        if line.startswith("|") and "`" in line
    ]
    routed_names = set(re.findall(r"`([A-Za-z0-9_.-]+\.md)`", "\n".join(routing_rows)))
    stats["routing_table_rows"] = len(routing_rows)
    reference_files = sorted((ROOT / "references").rglob("*.md"))
    unrouted = [
        path.relative_to(ROOT).as_posix()
        for path in reference_files
        if path.name not in routed_names
    ]
    stats["reference_documents"] = len(reference_files)
    stats["unrouted_reference_documents"] = unrouted
    for relative in unrouted:
        errors.append(f"reference document is unreachable from SKILL.md: {relative}")

    # A command is documented by the file that routes the work it belongs to:
    # SKILL.md and the references for the runtime commands, the protocol readmes
    # for the protocol tools, and the command-line reference for the rest.
    documenting = "\n".join(
        [skill_text]
        + [
            read_text(path, errors)
            for path in sorted((ROOT / "references").rglob("*.md"))
            + sorted((ROOT / "protocols").rglob("*.md"))
            + [ROOT / "scripts" / "README.md"]
        ]
    )
    entrypoints = [
        path for path in sorted((ROOT / "scripts").glob("*.py"))
        if re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]\s*:", path.read_text(encoding="utf-8"))
    ]
    undocumented = [path.name for path in entrypoints if path.name not in documenting]
    stats["script_entrypoints"] = len(entrypoints)
    stats["undocumented_script_entrypoints"] = undocumented
    for name in undocumented:
        errors.append(f"script entrypoint is documented nowhere the suite routes to: scripts/{name}")

    # The narrative half is declared in one place and documented in two, and a
    # directory that exists in the declaration and in neither document is a
    # directory nobody is told to use. The top level is listed in the narrative
    # readme and the four world subjects in the world readme, so the union of
    # the two has to be the declaration exactly.
    narrative_readme = read_text(ROOT / "assets/project-templates/narrative/README.md", errors)
    world_readme = read_text(ROOT / "assets/project-templates/narrative/world/README.md", errors)
    top_level = re.findall(r"^- `([^`]+?)/`", narrative_readme, re.MULTILINE)
    world_level = re.findall(r"^- `([^`]+?)/`", world_readme, re.MULTILINE)
    documented = sorted(
        [name for name in top_level if name != "world"]
        + [f"world/{name}" for name in world_level]
    )
    if documented != sorted(NARRATIVE_SUBDIRECTORIES):
        errors.append(
            "assets/project-templates/narrative: the directories the readmes name must equal "
            f"{sorted(NARRATIVE_SUBDIRECTORIES)}, found {documented}"
        )

    # The field lists a reader copies from, against the keys the readers accept.
    # A document that shows a complete list and omits a required field is a
    # document that teaches an artifact the validator refuses.
    from narrative import ROOT_KEYS as NARRATIVE_KEYS
    from scene_plot import ROOT_KEYS as SCENE_PLOT_KEYS

    structure = read_text(ROOT / "references/story-structure.md", errors)
    for artifact, accepted in (("narrative", NARRATIVE_KEYS), ("scene-plot", SCENE_PLOT_KEYS)):
        marker = f'artifact_type   "{artifact}"'
        if marker not in structure:
            errors.append(f"references/story-structure.md shows no field list for {artifact!r}")
            continue
        block = structure[structure.index(marker):]
        block = block[: block.index("```")]
        shown = set()
        for line in block.split(chr(10)):
            if not line or line.startswith(" "):
                continue
            parts = line.split()
            if not parts:
                continue
            # The first token names the field. A line may name two, and it says
            # so with a comma: "chapter, order  which chapter, and where in it".
            names = [parts[0]]
            while names[-1].endswith(",") and len(names) < len(parts):
                names.append(parts[len(names)])
            for part in names:
                name = part.strip(",")
                if name.isidentifier():
                    shown.add(name)
        absent = sorted(accepted - shown)
        if absent:
            errors.append(
                f"references/story-structure.md shows the {artifact} field list and omits "
                f"{absent}, which the reader accepts"
            )
        invented = sorted(shown - accepted)
        if invented:
            errors.append(
                f"references/story-structure.md shows {invented} in the {artifact} field list "
                "and the reader does not accept them"
            )

    check_carried_implementation(ROOT, "protocols/narrative/README.md", errors)
    # From where the check itself scans, which in a checkout is the repository
    # and in a distributed skill is the skill.
    check_contract_document(ROOT, "protocols/narrative/README.md", errors)
    # Every refusal a carried reader can make is named by a case in the suite
    # that exercises it, so deleting the refusal turns that case red.
    refusal_coverage.check(ROOT, [
        ("scripts/narrative.py",
         ["scripts/narrative_smoke_test.py", "scripts/narrative_index_smoke_test.py"]),
        ("scripts/scene_plot.py", ["scripts/scene_plot_smoke_test.py"]),
    ], errors)
    # The corpus the contract publishes is what those suites' case tables
    # assert, and the readers here reach every verdict in it.
    narrative_corpus.check(ROOT, errors)

    # Every enumeration a document and a constant both carry. Only the two
    # directory lists were compared, so a value added to the code and not to the
    # document was silent, which is the drift the declared lists exist to stop.
    from narrative import MEDIA
    from scene_plot import (
        FOCALIZATIONS,
        INTERIOR_EXTERIOR,
        PASSAGE_MODES,
        REALIZATIONS,
    )
    from submission_gate import RULES

    routed_text = "".join(
        read_text(path, errors)
        for path in sorted((ROOT / "references").rglob("*.md"))
        + sorted((ROOT / "protocols").rglob("*.md"))
    )
    declared_enumerations = {
        "refusal code": sorted(RULES),
        "realization kind": sorted(REALIZATIONS),
        "focalization": list(FOCALIZATIONS),
        "passage mode": list(PASSAGE_MODES),
        "interior or exterior": list(INTERIOR_EXTERIOR),
        "medium": sorted(MEDIA),
    }
    for label, values in sorted(declared_enumerations.items()):
        absent = [value for value in values if value not in routed_text]
        if absent:
            errors.append(
                f"every {label} the code accepts has to be named in a routed document, and "
                f"these are in none: {absent}"
            )
    stats["declared_enumerations"] = {
        label: len(values) for label, values in sorted(declared_enumerations.items())
    }

    canonical_state_dirs = list(STATE_SUBDIRECTORIES)
    state_readme = read_text(ROOT / "assets/project-templates/state/README.md", errors)
    state_readme_dirs = re.findall(r"^- `([^`]+?)/`", state_readme, re.MULTILINE)
    if state_readme_dirs != canonical_state_dirs:
        errors.append(f"assets/project-templates/state/README.md: state directories must equal {canonical_state_dirs}, found {state_readme_dirs}")
    protocol_readme = read_text(ROOT / "protocols/shared-state/README.md", errors)
    protocol_dirs = re.findall(r"^  ([a-z][a-z0-9-]*)/$", protocol_readme, re.MULTILINE)
    if protocol_dirs != canonical_state_dirs:
        errors.append(f"protocols/shared-state/README.md: state directories must equal {canonical_state_dirs}, found {protocol_dirs}")
    temporal = read_text(ROOT / "references/temporal-state.md", errors)
    temporal_dirs = re.findall(r"^state/([a-z][a-z0-9-]*)/", temporal, re.MULTILINE)
    if temporal_dirs != canonical_state_dirs:
        errors.append(f"references/temporal-state.md: state directories must equal {canonical_state_dirs}, found {temporal_dirs}")

    state_and_trust = read_text(ROOT / "references/state-and-trust.md", errors)
    template_links = {
        "series-state.md": "../assets/project-templates/series-state.md",
        "character-profiles.md": "../assets/project-templates/character-profiles.md",
        "asset-registry.md": "../assets/project-templates/asset-registry.md",
        "production-state.md": "../assets/project-templates/production-state.md",
        "state/events.jsonl": "../assets/project-templates/state/events.jsonl",
    }
    for label, target in template_links.items():
        if f"]({target})" not in state_and_trust:
            errors.append(f"references/state-and-trust.md: missing canonical template link for {label}")

    template_markers = {
        "series-state.md": [
            "delivery aspect and edit convention",
            "## Open arcs and planned reveals",
            "## Project pointers",
        ],
        "character-profiles.md": [
            "#### Stable identity pointers",
            "#### Approved identity summary",
            "#### Proposed traits",
        ],
        "asset-registry.md": [
            "## Registry rules",
            "### C01-IDENTITY",
            "### S01-SCENE",
            "### P01-PROP",
            "### V01-VIDEO",
            "### A01-AUDIO-PERFORMANCE",
            "consent and licensing notes",
        ],
        "production-state.md": [
            "## Target surface evidence",
            "## Operation cards",
            "## Exact submission records",
            "## Direct observations",
        ],
    }
    for filename, required in template_markers.items():
        template = read_text(ROOT / "assets/project-templates" / filename, errors)
        for marker in required:
            if marker not in template:
                errors.append(f"assets/project-templates/{filename}: missing canonical marker {marker!r}")
    for obsolete in ("aspect and editing convention", "### C01-REFERENCE"):
        if obsolete in state_and_trust:
            errors.append(f"references/state-and-trust.md: contains obsolete project-template wording {obsolete!r}")

    # Runtime markers prove explicit viewpoint and current production procedures are present.
    markers = {
        "SKILL.md": ["No viewpoint is implicit", "production_workflow.py", "viewpoint changes do not alter character state", "shot-request"],
        "references/story-structure.md": ["Five story functions", "Relationship progression", "Retellability check"],
        "references/visual-language.md": ["Series visual anchor", "Viewpoint-specific style translation", "Style continuity review"],
        "references/scoped-lexicon.md": ["Vocabulary rules are scoped by function", "Clean-realism quality profile", "Sound words are not visual-grade words"],
        "references/operational-distinctions.md": ["A start frame is not a character reference", "Workflow stages are evidence changes, not mental modes"],
        "references/viewpoint-profiles.md": ["Camera ownership", "Knowledge scope", "Point of audition"],
        "references/third-person-camera.md": ["Axis of action", "Screen direction", "Movement vocabulary"],
        "references/viewpoint-transitions.md": ["Viewpoint Transitions", "Knowledge changes", "State changes"],
        "references/visual-contracts.md": ["Per-shot request", "Candidate and adoption separation", "Re-anchor ladder"],
    }
    for rel, required in markers.items():
        text = read_text(ROOT / rel, errors).casefold()
        for marker in required:
            if marker.casefold() not in text:
                errors.append(f"{rel}: missing required marker {marker!r}")


    stats.update({
        "package": package.get("name", ""),
        "version": version,
        "knowledge_sources": len(sources),
        "text_files": text_files,
        "markdown_files": markdown_files,
        "json_files": json_files,
        "jsonl_records": jsonl_records,
        "python_files": python_files,
        "repository_link_errors": repository_link_errors,
    })
    return errors, warnings, stats


def run_static(repo: Path, manifest: dict) -> Outcome:
    try:
        errors, warnings, stats = static_checks(repo, manifest)
    except Exception:
        errors, warnings, stats = [f"the static checks raised:\n{traceback.format_exc()}"], [], {}
    return Outcome(STATIC, 1 if errors else 0, errors=errors, warnings=warnings, stats=stats)


def job_count(value: str) -> int:
    count = int(value)
    if count < 1:
        raise argparse.ArgumentTypeError("--jobs takes 1 or more")
    return count


def arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run every repository check. The static checks read the tree in this process, "
            "and each command runs as its own process, several at a time."
        ),
        epilog=(
            "The report is JSON on standard output. Standard error carries one line per "
            "finished check, the output of each failure, and the warnings."
        ),
    )
    parser.add_argument(
        "--list", action="store_true",
        help="print the name of every check, one per line, and run nothing",
    )
    parser.add_argument(
        "--only", action="append", metavar="NAME",
        help=(
            "run only this check; repeat for more. NAME is a name --list prints, such as "
            f"{STATIC!r} or 'scripts/narrative_smoke_test.py', or a glob such as 'examples/*'"
        ),
    )
    parser.add_argument(
        "--jobs", type=job_count, default=os.cpu_count() or 1, metavar="N",
        help=(
            "run at most N commands at a time (default: the processor count, %(default)s "
            "here); 1 runs them one after another"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    # A failure's output can hold characters the console cannot encode; they
    # print escaped instead of ending the run.
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="backslashreplace")
    if args.list:
        print("\n".join([STATIC, *(check.name for check in CHECKS)]))
        return 0
    try:
        with_static, checks = select(args.only)
    except ValueError as exc:
        print(f"validate_skill.py: {exc}", file=sys.stderr)
        return 2

    try:
        repo = require_repository_root()
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 1
    try:
        with (repo / "package-manifest.toml").open("rb") as handle:
            manifest = tomllib.load(handle)
    except Exception as exc:
        print(json.dumps({"ok": False, "errors": [f"package-manifest.toml: {exc}"]}, indent=2))
        return 1

    includes = manifest.get("release", {}).get("include", [])
    progress = Progress(len(checks) + int(with_static))
    progress.emit(f"validate_skill: {progress.total} checks, at most {args.jobs} at a time")
    before = tree_state(repo, includes)
    outcomes: dict[str, Outcome] = {}
    running: dict[Future, str] = {}
    pool = ThreadPoolExecutor(max_workers=args.jobs)
    try:
        if with_static:
            running[pool.submit(run_static, repo, manifest)] = STATIC
        for check in checks:
            if not check.alone:
                running[pool.submit(run_check, check)] = check.name
        for future in as_completed(list(running)):
            outcome = future.result()
            outcomes[outcome.name] = outcome
            progress.finished(outcome)
        # Nothing else runs by now, so each of these runs by itself.
        for check in checks:
            if check.alone:
                future = pool.submit(run_check, check)
                running[future] = check.name
                outcomes[check.name] = future.result()
                progress.finished(outcomes[check.name])
    except KeyboardInterrupt:
        # A check that never returns, such as one waiting on a lock, is named
        # here when the run is interrupted.
        unfinished = [name for future, name in running.items() if not future.done()]
        progress.emit("interrupted; unfinished: " + (", ".join(unfinished) or "none"))
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    pool.shutdown()
    after = tree_state(repo, includes)

    errors: list[str] = []
    warnings: list[str] = []
    stats: dict = {}
    # What standard error lists at the end: each static error, and one line
    # per failed command, whose output was printed when it finished.
    shown: list[str] = []
    if STATIC in outcomes:
        errors += outcomes[STATIC].errors
        warnings += outcomes[STATIC].warnings
        stats.update(outcomes[STATIC].stats)
        shown += outcomes[STATIC].errors
    results = []
    for check in checks:
        outcome = outcomes[check.name]
        results.append({"command": check.name, "returncode": outcome.returncode})
        errors += outcome.errors
        if outcome.returncode:
            shown.append(f"command failed with exit status {outcome.returncode}: {check.name}")
    changed = sorted(
        (set(before) ^ set(after))
        | {path for path in set(before) & set(after) if before[path] != after[path]}
    )
    if changed:
        message = (
            "the shipped tree changed while the checks ran, and a check writes only into its "
            f"own temporary directories: {', '.join(changed[:10])}"
            + (f" and {len(changed) - 10} more" if len(changed) > 10 else "")
        )
        errors.append(message)
        shown.append(message)
    stats["commands"] = results
    stats["jobs"] = args.jobs

    report = {"ok": not errors, "errors": errors, "warnings": warnings, "stats": stats,
              "generated_media_quality": "not evaluated"}
    if args.only:
        report["selected"] = [STATIC] * int(with_static) + [check.name for check in checks]
    progress.report(shown, warnings)
    failed = [name for name, outcome in outcomes.items() if outcome.returncode]
    progress.emit(
        f"validate_skill: {progress.total - len(failed)} of {progress.total} checks passed"
        + (f"; failed: {', '.join(failed)}" if failed else "")
        + ("" if report["ok"] or failed else "; the errors above fail the run")
    )
    # ASCII escapes keep the report readable whatever decoder its reader uses.
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
