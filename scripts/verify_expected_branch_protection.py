#!/usr/bin/env python3
"""Audit helper: expected required checks on ``main`` vs GitHub (when ``gh`` is available)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_spec(root: Path) -> dict[str, Any]:
    path = root / ".github" / "expected-branch-protection-main.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _gh_json(args: list[str]) -> dict[str, Any] | None:
    try:
        proc = subprocess.run(
            ["gh", *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    return json.loads(proc.stdout)


def _remote_required_contexts(_root: Path) -> set[str] | None:
    remote = _gh_json(["api", "repos/:owner/:repo/branches/main/protection"])
    if remote is None:
        return None
    checks = remote.get("required_status_checks") or {}
    contexts = checks.get("contexts") or checks.get("checks")
    if contexts is None:
        return None
    if contexts and isinstance(contexts[0], dict):
        return {str(c.get("context", c.get("name", ""))) for c in contexts}
    return {str(c) for c in contexts}


def main() -> int:
    root = _repo_root()
    spec = _load_spec(root)
    expected_required = set(spec["required_status_checks"])
    expected_not = set(spec["not_required_status_checks"])

    print("Expected required status checks on main:")
    for name in spec["required_status_checks"]:
        print(f"  - {name}")
    print("\nNOT required (Policy B):", ", ".join(sorted(expected_not)))
    print("\nDocs:", ", ".join(spec.get("docs", [])))
    print("Record screenshot: docs/BRANCH_PROTECTION_RECORD.md")

    remote = _remote_required_contexts(root)
    if remote is None:
        print("\nRemote: skipped (run `gh auth login` to compare GitHub branch protection).")
        return 0

    missing = expected_required - remote
    extra_required = remote - expected_required
    wrongly_required = expected_not & remote

    print("\nRemote required contexts:", ", ".join(sorted(remote)) or "(none)")

    errors: list[str] = []
    if missing:
        errors.append(f"missing on GitHub: {sorted(missing)}")
    if extra_required:
        errors.append(f"unexpected on GitHub (not in spec): {sorted(extra_required)}")
    if wrongly_required:
        errors.append(f"forbidden checks enabled on GitHub: {sorted(wrongly_required)}")

    if errors:
        for line in errors:
            print(f"ERROR: {line}", file=sys.stderr)
        return 1

    print("\nRemote branch protection matches expected required checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
