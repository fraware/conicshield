#!/usr/bin/env python3
"""Assert batch_solve_report meets benchmarks/reports/batch_acceptance_policy.json tiers."""

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


def _tier_policy(policy: dict[str, Any], tier: str) -> dict[str, Any]:
    if tier in policy and isinstance(policy[tier], dict):
        block = dict(policy[tier])
        block.setdefault("device", policy.get("device"))
        return block
    if tier == "viability":
        return policy
    raise KeyError(f"unknown tier {tier!r}")


def check_batch_report(*, report: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    """Return failure messages. Empty list means acceptance passed."""
    failures: list[str] = []
    min_bs = int(policy.get("min_batch_size", 4))
    min_speedup = float(policy.get("min_speedup_ratio", 1.05))
    want_device = policy.get("device")
    mode = str(policy.get("acceptance_mode", "any_row_meets"))
    comparisons = report.get("comparisons") or []
    if not comparisons:
        failures.append("no comparisons in batch_solve_report")
        return failures

    eligible: list[dict[str, Any]] = []
    for row in comparisons:
        if not isinstance(row, dict):
            continue
        bs = row.get("batch_size")
        if bs is not None and int(bs) < min_bs:
            continue
        if want_device and row.get("device") != want_device:
            continue
        eligible.append(row)

    if not eligible:
        failures.append(f"no comparison row with batch_size>={min_bs} and device={want_device!r}")
        return failures

    if mode == "any_row_meets":
        best = max(float(r.get("speedup_ratio") or 0.0) for r in eligible)
        if best < min_speedup:
            failures.append(
                f"no row met min_speedup_ratio={min_speedup} (best speedup_ratio={best:.4f} "
                f"across {len(eligible)} eligible rows)"
            )
        return failures

    for row in eligible:
        bs = row.get("batch_size")
        speedup = float(row.get("speedup_ratio") or 0.0)
        if speedup < min_speedup:
            failures.append(
                f"speedup_ratio={speedup:.4f} < {min_speedup} "
                f"(batch_size={bs}, device={row.get('device')})"
            )
    return failures


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--report",
        type=Path,
        default=None,
        help="batch_solve_report.json (default: output/batch_solve_report.json).",
    )
    p.add_argument(
        "--tier",
        choices=("viability", "throughput_advisory"),
        default="viability",
        help="Policy tier (default: viability, enforced).",
    )
    args = p.parse_args()
    root = _repo_root()
    report_path = args.report or (root / "output" / "batch_solve_report.json")
    if not report_path.is_file():
        print(f"Missing report: {report_path}", file=sys.stderr)
        return 2
    root_policy = _load_policy(root)
    tier_policy = _tier_policy(root_policy, args.tier)
    enforcement = str(tier_policy.get("enforcement", "required"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    failures = check_batch_report(report=report, policy=tier_policy)
    label = f"batch {args.tier}"
    if failures:
        if enforcement == "advisory":
            print(f"{label} ADVISORY (not met):", file=sys.stderr)
            for f in failures:
                print(f"  - {f}", file=sys.stderr)
            print(f"{label}: advisory only — exit 0")
            return 0
        print(f"{label} FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print(f"{label} OK ({report_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
