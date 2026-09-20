"""Validate the target-profile catalog."""
from __future__ import annotations

import json

from target_protocol import validate_catalog


def main() -> int:
    report = validate_catalog()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
