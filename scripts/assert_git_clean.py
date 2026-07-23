#!/usr/bin/env python3
"""Fail if the Git worktree is dirty (verification must be read-only)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--label",
        default="verification",
        help="Human label for the failing job (default: verification).",
    )
    args = p.parse_args()
    root = _repo_root()
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout or "git status failed", file=sys.stderr)
        return 2
    dirty = [line for line in (proc.stdout or "").splitlines() if line.strip()]
    if dirty:
        print(
            f"ERROR: {args.label} left the Git worktree dirty "
            f"({len(dirty)} path(s)). verify-*/check-* must be read-only.",
            file=sys.stderr,
        )
        for line in dirty[:50]:
            print(line, file=sys.stderr)
        if len(dirty) > 50:
            print(f"... and {len(dirty) - 50} more", file=sys.stderr)
        return 1
    print(f"OK: worktree clean after {args.label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
