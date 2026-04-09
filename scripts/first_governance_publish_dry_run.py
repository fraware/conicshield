#!/usr/bin/env python3
"""Run finalize_cli then release_cli --dry-run for a candidate bundle (P0 publish rehearsal).

Does not mutate CURRENT.json or the registry. Use after:
  - validate_run_bundle passes on benchmarks/runs/<run_id>/
  - parity.cli green (parity_summary.json path below)
  - governance_decision.md present in the run dir (for real publish)

Example:

  python scripts/first_governance_publish_dry_run.py \\
    --run-dir benchmarks/runs/my-run-id \\
    --parity-summary-path output/native_parity_local/parity_summary.json
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    p = argparse.ArgumentParser(description="Finalize + release dry-run for a governed run directory.")
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument(
        "--family-id",
        default="conicshield-transition-bank-v1",
    )
    p.add_argument("--task-contract-version", default="v1")
    p.add_argument("--fixture-version", default="fixture-v1")
    p.add_argument(
        "--reference-fixture-dir",
        type=Path,
        default=None,
        help="Default: tests/fixtures/parity_reference",
    )
    p.add_argument("--parity-summary-path", type=Path, default=None)
    p.add_argument(
        "--current-release-path",
        type=Path,
        default=None,
        help="Default: benchmarks/releases/<family-id>/CURRENT.json",
    )
    args = p.parse_args()
    root = _root()
    exe = sys.executable
    fixture = args.reference_fixture_dir or (root / "tests" / "fixtures" / "parity_reference")
    current = args.current_release_path or (root / "benchmarks" / "releases" / args.family_id / "CURRENT.json")

    fin = [
        exe,
        "-m",
        "conicshield.governance.finalize_cli",
        "--run-dir",
        str(args.run_dir.resolve()),
        "--family-id",
        args.family_id,
        "--task-contract-version",
        args.task_contract_version,
        "--fixture-version",
        args.fixture_version,
        "--reference-fixture-dir",
        str(fixture.resolve()),
        "--current-release-path",
        str(current.resolve()),
    ]
    if args.parity_summary_path is not None:
        fin.extend(["--parity-summary-path", str(args.parity_summary_path.resolve())])

    print("== finalize_cli ==")
    r1 = subprocess.run(fin, cwd=root, check=False)
    if r1.returncode != 0:
        return r1.returncode

    rel = [
        exe,
        "-m",
        "conicshield.governance.release_cli",
        "--run-dir",
        str(args.run_dir.resolve()),
        "--family-id",
        args.family_id,
        "--reason",
        "dry-run rehearsal (first_governance_publish_dry_run.py)",
        "--dry-run",
    ]
    print("== release_cli --dry-run ==")
    r2 = subprocess.run(rel, cwd=root, check=False)
    return r2.returncode


if __name__ == "__main__":
    raise SystemExit(main())
