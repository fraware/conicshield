#!/usr/bin/env python3
"""Demonstrate ``finalize_community_dataset`` then index integrity check."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    py = sys.executable
    subprocess.check_call([py, str(root / "scripts" / "finalize_community_dataset.py")], cwd=str(root))
    subprocess.check_call(
        [py, str(root / "scripts" / "refresh_published_run_index.py"), "--check"],
        cwd=str(root),
    )
    print("OK: community metadata, READMEs, index, and bundle profile are aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
