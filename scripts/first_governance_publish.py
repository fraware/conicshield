#!/usr/bin/env python3
"""Finalize + publish + strict audit for the first governed family run."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    p = argparse.ArgumentParser(
        description="Finalize, publish, and strict-audit a governed run."
    )
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--family-id", default="conicshield-transition-bank-v1")
    p.add_argument("--task-contract-version", default="v1")
    p.add_argument("--fixture-version", default="fixture-v1")
    p.add_argument("--reason", default="first governed publish")
    p.add_argument("--reference-fixture-dir", type=Path, default=None)
    p.add_argument("--parity-summary-path", type=Path, default=None)
    p.add_argument("--current-release-path", type=Path, default=None)
    args = p.parse_args()

    root = _root()
    run_dir = args.run_dir.resolve()
    decision = run_dir / "governance_decision.md"
    if not decision.exists():
        print(f"Missing decision record: {decision}", file=sys.stderr)
        print(
            "Copy benchmarks/templates/governance_decision.template.md first.",
            file=sys.stderr,
        )
        return 2

    fixture = args.reference_fixture_dir or (
        root / "tests" / "fixtures" / "parity_reference"
    )
    current = args.current_release_path or (
        root / "benchmarks" / "releases" / args.family_id / "CURRENT.json"
    )
    exe = sys.executable
    finalize_cmd = [
        exe,
        "-m",
        "conicshield.governance.finalize_cli",
        "--run-dir",
        str(run_dir),
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
        finalize_cmd.extend(
            ["--parity-summary-path", str(args.parity_summary_path.resolve())]
        )

    release_cmd = [
        exe,
        "-m",
        "conicshield.governance.release_cli",
        "--run-dir",
        str(run_dir),
        "--family-id",
        args.family_id,
        "--reason",
        args.reason,
    ]
    strict_audit_cmd = [
        exe,
        "-m",
        "conicshield.governance.audit_cli",
        "--strict",
    ]

    print("== finalize_cli ==")
    if subprocess.run(finalize_cmd, cwd=root, check=False).returncode != 0:
        return 1
    print("== release_cli ==")
    if subprocess.run(release_cmd, cwd=root, check=False).returncode != 0:
        return 1
    print("== audit_cli --strict ==")
    return subprocess.run(strict_audit_cmd, cwd=root, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
