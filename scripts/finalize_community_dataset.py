#!/usr/bin/env python3
"""Sync community metadata, publication READMEs, index hashes, and validate contracts."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run(cmd: list[str], *, cwd: Path) -> int:
    print("Running:", " ".join(cmd), file=sys.stderr)
    return subprocess.call(cmd, cwd=str(cwd))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip validate_published_bundle_profile (metadata/readme/index only).",
    )
    args = p.parse_args()
    root = _repo_root()
    py = sys.executable
    steps = [
        [py, str(root / "scripts" / "sync_community_metadata.py")],
        [py, str(root / "scripts" / "sync_published_run_readmes.py")],
        [py, str(root / "scripts" / "refresh_published_run_index.py")],
    ]
    if not args.skip_verify:
        steps.append([py, str(root / "scripts" / "validate_published_bundle_profile.py")])
    for cmd in steps:
        if _run(cmd, cwd=root) != 0:
            return 1
    print("OK: community dataset layer finalized", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
