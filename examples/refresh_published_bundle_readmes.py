#!/usr/bin/env python3
"""Demonstrate sync_community_metadata + sync_published_run_readmes + index check."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], root: Path) -> None:
    print(">", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(root))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    py = sys.executable
    _run([py, str(root / "scripts" / "sync_community_metadata.py")], root)
    _run([py, str(root / "scripts" / "sync_published_run_readmes.py")], root)
    _run([py, str(root / "scripts" / "refresh_published_run_index.py"), "--check"], root)
    print("OK: community metadata, READMEs, and index are aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
