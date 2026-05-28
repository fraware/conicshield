#!/usr/bin/env python3
"""Warn when inter-sim-rl REVISION changed since the last full flagship refresh."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--revision-file",
        type=Path,
        default=None,
        help="Default: third_party/inter-sim-rl/REVISION",
    )
    args = p.parse_args()
    root = _repo_root()
    rev_path = args.revision_file or (root / "third_party" / "inter-sim-rl" / "REVISION")
    if not rev_path.is_file():
        print(f"Missing {rev_path}", file=sys.stderr)
        return 2
    current = ""
    for line in rev_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("sha="):
            current = line.split("=", 1)[1].strip()
            break
    if not current:
        current = rev_path.read_text(encoding="utf-8").strip()
    prov_path = root / "benchmarks" / "external_evidence" / "EXPORT_PROVENANCE.json"
    prov = json.loads(prov_path.read_text(encoding="utf-8"))
    recorded = prov.get("inter_sim_revision_sha")
    if recorded == current:
        print(f"inter-sim REVISION matches export provenance ({current[:12]}…)")
        return 0
    if recorded:
        print(
            f"inter-sim REVISION changed ({recorded[:12]}… -> {current[:12]}…); "
            "run make host-realistic-refresh-cycle-licensed per HOST_REALISTIC_CADENCE_POLICY.md",
            file=sys.stderr,
        )
        return 1
    print(
        f"EXPORT_PROVENANCE missing inter_sim_revision_sha; record a refresh after setting pin {current[:12]}…",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
