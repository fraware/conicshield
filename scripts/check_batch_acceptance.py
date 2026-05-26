#!/usr/bin/env python3
"""Assert batch_solve_report meets benchmarks/reports/batch_acceptance_policy.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_policy(root: Path) -> dict[str, Any]:
    path = root / "benchmarks" / "reports" / "batch_acceptance_policy.json"
    return json.loads(path.read_text(encoding="utf-8"))


def check_batch_report(*, report: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    min_bs = int(policy.get("min_batch_size", 4))
    min_speedup = float(policy.get("min_speedup_ratio", 1.05))
    want_device = policy.get("device")
    comparisons = report.get("comparisons") or []
    if not comparisons:
        failures.append("no comparisons in batch_solve_report")
        return failures
    matched = False
    for row in comparisons:
        if not isinstance(row, dict):
            continue
        bs = row.get("batch_size")
        if bs is not None and int(bs) < min_bs:
            continue
        if want_device and row.get("device") != want_device:
            continue
        speedup = float(row.get("speedup_ratio") or 0.0)
        if speedup < min_speedup:
            failures.append(
                f"speedup_ratio={speedup:.4f} < {min_speedup} "
                f"(batch_size={bs}, device={row.get('device')})"
            )
        matched = True
    if not matched:
        failures.append(f"no comparison row with batch_size>={min_bs} and device={want_device!r}")
    return failures


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--report",
        type=Path,
        default=None,
        help="batch_solve_report.json (default: output/batch_solve_report.json).",
    )
    args = p.parse_args()
    root = _repo_root()
    report_path = args.report or (root / "output" / "batch_solve_report.json")
    if not report_path.is_file():
        print(f"Missing report: {report_path}", file=sys.stderr)
        return 2
    policy = _load_policy(root)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    failures = check_batch_report(report=report, policy=policy)
    if failures:
        print("batch acceptance FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print(f"batch acceptance OK ({report_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
