#!/usr/bin/env python3
"""Fail when flagship refresh triggers changed without an updated refresh log in the same diff."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_TRIGGER_PREFIXES = (
    "third_party/inter-sim-rl/REVISION",
    "scripts/export_inter_sim_offline_graph.py",
    "scripts/capture_inter_sim_offline_graph.py",
    "scripts/refresh_live_upstream_export.py",
    "scripts/produce_reference_bundle.py",
    "scripts/run_host_realistic_publish.py",
    "scripts/host_realistic_refresh_cycle.py",
    "conicshield/governance/finalize.py",
    "conicshield/governance/release.py",
    "conicshield/governance/reference_authority.py",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _changed_files(base_ref: str, repo: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        proc = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=False,
        )
    return [ln.strip().replace("\\", "/") for ln in proc.stdout.splitlines() if ln.strip()]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-ref", default="origin/main", help="Merge base for PR diff.")
    args = p.parse_args()
    repo = _repo_root()
    changed = _changed_files(args.base_ref, repo)
    if not changed:
        return 0

    triggered = [f for f in changed if any(f == t or f.startswith(t.rstrip("/") + "/") for t in _TRIGGER_PREFIXES)]
    if not triggered:
        return 0

    log_updated = any(
        f == "docs/REFERENCE_AUTHORITY_LOG.md"
        or f == "benchmarks/external_evidence/EXPORT_PROVENANCE.json"
        or f.startswith("benchmarks/published_runs/host-realistic-")
        for f in changed
    )
    if log_updated:
        print("Flagship refresh triggers changed; provenance/log updated in same diff.")
        return 0

    print("Flagship refresh triggers changed without provenance update:", file=sys.stderr)
    for f in triggered:
        print(f"  - {f}", file=sys.stderr)
    print(
        "Run HOST_REALISTIC_REFRESH_PROCEDURE.md and commit REFERENCE_AUTHORITY_LOG + EXPORT_PROVENANCE.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
