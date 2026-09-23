#!/usr/bin/env python3
"""Regenerate every derived file, each after the files it is derived from.

    python scripts/build_derived.py            rewrite every derived file
    python scripts/build_derived.py --check    compare each with a fresh build; write nothing

A change to a source reaches its derived files only in this order:

1. the directing vocabulary, from the cinematic lexicon;
2. the narrative contract's corpus, from the case tables of its smoke tests;
3. the narrative contract's seal, over the readers and the corpus, and the
   public contract manifest's, over the schemas;
4. the one-file adapter, from the references and the protocol documents;
5. the worked continuity example;
6. the host files, from SKILL.md and the package manifest;
7. the checked examples, whose reading records pin SKILL.md and the route documents.

It stops at the first step that fails and names it.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
STEPS = (
    "scripts/build_resources.py",
    "scripts/narrative_corpus.py",
    "scripts/seal_contract.py",
    "scripts/build_flat.py",
    "scripts/build_example.py",
    "scripts/build_host_packages.py",
    "examples/submission-gate/build_example.py",
    "examples/input-assembly/build_example.py",
    "examples/model-evidence/build_example.py",
    "examples/resume-recording/build_example.py",
    "examples/tactic-consultation/build_example.py",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="Compare every derived file with a fresh build and write nothing")
    args = parser.parse_args(argv)
    for number, step in enumerate(STEPS, 1):
        command = [sys.executable, str(SUITE / step), *(["--check"] if args.check else [])]
        done = subprocess.run(command, cwd=SUITE, capture_output=True, text=True, encoding="utf-8",
                              errors="replace")
        print(f"[{number}/{len(STEPS)}] {'pass' if done.returncode == 0 else 'FAIL'} {step}", flush=True)
        if done.returncode:
            print((done.stdout + done.stderr).rstrip(), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
