#!/usr/bin/env python3
"""Ensure production solver defaults remain pinned and quarantine is isolated."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=None)
    args = p.parse_args()
    root = args.root or _repo_root()
    policy_path = root / "packaging" / "solver_stack_policy.json"
    if not policy_path.is_file():
        print(f"ERROR: missing {policy_path}", file=sys.stderr)
        return 2
    policy: dict[str, Any] = json.loads(policy_path.read_text(encoding="utf-8"))
    defaults = policy.get("production_defaults") or {}
    failures: list[str] = []
    for name, row in defaults.items():
        rel = str(row.get("constraints_file") or "")
        path = root / rel
        if not path.is_file():
            failures.append(f"production default {name}: missing constraints {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        # Soft pin presence: at least one == pin (version lock).
        if "==" not in text and "MOREAU_VERSION" not in text:
            failures.append(f"production default {name}: {rel} has no version pins")

    quarantine = policy.get("quarantine") or {}
    for cand in quarantine.get("candidates") or []:
        # Candidates must not point at production constraint files.
        cpath = str(cand.get("constraints_file") or "")
        if cpath.startswith("packaging/constraints/") and "/quarantine/" not in cpath:
            failures.append(
                f"quarantine candidate {cand.get('id')!r} must not overwrite "
                f"production constraints path {cpath!r}; use packaging/quarantine/"
            )

    if failures:
        for row in failures:
            print(f"ERROR: {row}", file=sys.stderr)
        return 1
    print("OK: solver stack policy consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
