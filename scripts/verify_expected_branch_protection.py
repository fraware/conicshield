#!/usr/bin/env python3
"""Print expected required checks for main (audit helper; GitHub UI is source of truth)."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / ".github" / "expected-branch-protection-main.json"
    spec = json.loads(path.read_text(encoding="utf-8"))
    required = spec["required_status_checks"]
    print("Expected required status checks on main:")
    for name in required:
        print(f"  - {name}")
    print("\nNOT required (Policy B):", ", ".join(spec["not_required_status_checks"]))
    print("\nRecord GitHub Settings screenshot in docs/BRANCH_PROTECTION_RECORD.md")
  optional = """
Optional: with GH_TOKEN and admin access:
  gh api repos/:owner/:repo/branches/main/protection
"""
    print(optional)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
