#!/usr/bin/env python3
"""Build or verify the canonical mixed-viewpoint example."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples" / "mixed-viewpoint-workshop" / "build_example.py"

if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    sys.path.insert(0, str(SCRIPT.parent))
    runpy.run_path(str(SCRIPT), run_name="__main__")
