#!/usr/bin/env python3
"""Run the maintainer community-dataset finalize flow (mutates repo files).

Audience: maintainer aligning COMMUNITY_METADATA, bundle READMEs, and the published-run index.
Prerequisites: repo checkout; ``pip install -e ".[dev]"``; run from repo root.
Proves: ``finalize_community_dataset`` + index ``--check`` leave metadata, READMEs, and index aligned.
Does not prove: licensed vendor publish, parity replay, or that changes should be committed without review.
Expected: exit 0; OK alignment message. Use ``--check-only`` to verify without writing.

Warning: default mode updates files under ``benchmarks/published_runs/`` and the index.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from _common import configure_stdio, repo_root, section


def main() -> int:
    configure_stdio()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--check-only",
        action="store_true",
        help="Only run refresh_published_run_index.py --check (no finalize).",
    )
    args = p.parse_args()

    root = repo_root()
    py = sys.executable

    if args.check_only:
        section("Index check only")
        subprocess.check_call(
            [py, str(root / "scripts" / "refresh_published_run_index.py"), "--check"],
            cwd=str(root),
        )
        print("OK: index matches on-disk bundle files")
        return 0

    section("finalize_community_dataset")
    subprocess.check_call(
        [py, str(root / "scripts" / "finalize_community_dataset.py")],
        cwd=str(root),
    )

    section("refresh_published_run_index.py --check")
    subprocess.check_call(
        [py, str(root / "scripts" / "refresh_published_run_index.py"), "--check"],
        cwd=str(root),
    )

    section("Done")
    print("OK: community metadata, READMEs, index, and bundle profile are aligned")
    print("Review git diff before commit; then: make verify-v1-lock-quick")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
