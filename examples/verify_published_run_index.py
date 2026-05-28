#!/usr/bin/env python3
"""Verify the published-run integrity index and family current run.

Audience: researcher building tools on ``PUBLISHED_RUN_INDEX.json``.
Prerequisites: ``pip install -e .`` from repository root; run with cwd = repo root.
Proves: ``refresh_published_run_index.py --check``, ``list_runs``, ``get_current_run``, ``verify_run``.
Does not prove: scientific conclusions, publish pipeline correctness beyond on-disk hashes.
Expected: index OK; all indexed runs verify; ``current_run_id`` is ``host-realistic-20260525``.
"""

from __future__ import annotations

import subprocess
import sys

from _common import FAMILY_ID, configure_stdio, repo_root, section

from conicshield.published_runs import get_current_run, index_path, list_runs, verify_run


def main() -> int:
    configure_stdio()
    root = repo_root()
    py = sys.executable

    section("Index path")
    idx = index_path(repo_root=root)
    print(idx.relative_to(root))

    section("Index integrity (refresh_published_run_index.py --check)")
    subprocess.check_call(
        [py, str(root / "scripts" / "refresh_published_run_index.py"), "--check"],
        cwd=str(root),
    )
    print("OK")

    section("Indexed runs (list_runs)")
    entries = list_runs(repo_root=root)
    for entry in entries:
        print(f"  {entry.run_id}")
        print(f"    path: {entry.repository_relative_path}")
        print(f"    files in integrity map: {len(entry.integrity)}")

    section("Per-run verify_run")
    for entry in entries:
        verify_run(entry.run_id, repo_root=root)
        print(f"  OK  {entry.run_id}")

    section("Family current (get_current_run)")
    current = get_current_run(FAMILY_ID, repo_root=root)
    print("family:", FAMILY_ID)
    print("current_run_id:", current.run_id)
    if current.community:
        print("evidence_tier:", current.community.evidence_tier)
        print("is_family_current_run:", current.community.is_family_current_run)

    section("Done")
    print("Next: python examples/load_published_runs_api.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
