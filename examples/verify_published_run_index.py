#!/usr/bin/env python3
"""Verify PUBLISHED_RUN_INDEX integrity and list governed run ids."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from conicshield.published_runs import get_current_run, index_path, list_runs, verify_run


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    py = sys.executable
    idx = index_path(repo_root=root)
    print("index:", idx)
    subprocess.check_call(
        [py, str(root / "scripts" / "refresh_published_run_index.py"), "--check"],
        cwd=str(root),
    )
    print("index integrity OK")

    for entry in list_runs(repo_root=root):
        print(f"  run_id={entry.run_id}  path={entry.repository_relative_path}")

    current = get_current_run("conicshield-transition-bank-v1", repo_root=root)
    print("\ncurrent_run_id:", current.run_id)
    verify_run(current.run_id, repo_root=root)
    print("verify_run OK:", current.run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
