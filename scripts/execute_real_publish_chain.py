#!/usr/bin/env python3
"""Execute real publish chain with strict governance checks."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run(cmd: list[str], *, cwd: Path) -> int:
    print("$", " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd, check=False).returncode


def main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "Validate -> finalize -> release dry-run -> publish -> strict audit."
        )
    )
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--family-id", default="conicshield-transition-bank-v1")
    p.add_argument("--task-contract-version", default="v1")
    p.add_argument("--fixture-version", default="fixture-v1")
    p.add_argument("--reason", required=True)
    p.add_argument("--reference-fixture-dir", type=Path, default=None)
    p.add_argument("--parity-summary-path", type=Path, default=None)
    p.add_argument("--current-release-path", type=Path, default=None)
    p.add_argument("--solver-versions", type=Path, default=None)
    p.add_argument("--solver-version-date-utc", type=str, default=None)
    args = p.parse_args()

    root = _root()
    run_dir = args.run_dir.resolve()
    fixture_dir = args.reference_fixture_dir or (
        root / "tests" / "fixtures" / "parity_reference"
    )
    current_release = args.current_release_path or (
        root / "benchmarks" / "releases" / args.family_id / "CURRENT.json"
    )
    decision_record = run_dir / "governance_decision.md"
    if not decision_record.exists():
        print(f"Missing {decision_record}", file=sys.stderr)
        print(
            "Copy benchmarks/templates/governance_decision.template.md first.",
            file=sys.stderr,
        )
        return 2

    exe = sys.executable
    if _run(
        [
            exe,
            "-m",
            "conicshield.artifacts.validator_cli",
            "--run-dir",
            str(run_dir),
        ],
        cwd=root,
    ) != 0:
        return 1

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
        str(fixture_dir.resolve()),
        "--current-release-path",
        str(current_release.resolve()),
    ]
    if args.parity_summary_path is not None:
        finalize_cmd.extend(
            ["--parity-summary-path", str(args.parity_summary_path.resolve())]
        )
    if _run(finalize_cmd, cwd=root) != 0:
        return 1

    if _run(
        [
            exe,
            "-m",
            "conicshield.governance.release_cli",
            "--run-dir",
            str(run_dir),
            "--family-id",
            args.family_id,
            "--reason",
            args.reason,
            "--dry-run",
        ],
        cwd=root,
    ) != 0:
        return 1

    if _run(
        [
            exe,
            "-m",
            "conicshield.governance.release_cli",
            "--run-dir",
            str(run_dir),
            "--family-id",
            args.family_id,
            "--reason",
            args.reason,
        ],
        cwd=root,
    ) != 0:
        return 1

    if _run(
        [exe, "-m", "conicshield.governance.audit_cli", "--strict"],
        cwd=root,
    ) != 0:
        return 1

    if args.solver_versions is not None:
        update_cmd = [
            exe,
            str(
                root / "scripts" / "update_engineering_status_from_solver_versions.py"
            ),
            "--solver-versions",
            str(args.solver_versions.resolve()),
        ]
        if args.solver_version_date_utc:
            update_cmd.extend(["--date-utc", args.solver_version_date_utc])
        if _run(update_cmd, cwd=root) != 0:
            return 1

    print("Real publish chain completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
