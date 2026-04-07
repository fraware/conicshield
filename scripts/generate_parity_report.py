#!/usr/bin/env python3
"""Generate parity_report.md from parity_summary.json (optional parity_steps.jsonl line count)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from conicshield.parity.gates import list_default_parity_gate_violations
from conicshield.parity.replay import ParitySummary


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_summary(path: Path) -> ParitySummary:
    data = json.loads(path.read_text(encoding="utf-8"))
    return ParitySummary(
        total_steps=int(data["total_steps"]),
        action_match_rate=float(data["action_match_rate"]),
        max_corrected_linf=float(data["max_corrected_linf"]),
        p95_corrected_linf=float(data["p95_corrected_linf"]),
        max_corrected_l2=float(data["max_corrected_l2"]),
        p95_corrected_l2=float(data["p95_corrected_l2"]),
        active_constraints_match_rate=float(data["active_constraints_match_rate"]),
    )


def _count_jsonl_lines(path: Path) -> int | None:
    if not path.is_file():
        return None
    n = 0
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                n += 1
    return n


def main() -> int:
    parser = argparse.ArgumentParser(description="Write parity_report.md from parity_summary.json.")
    parser.add_argument(
        "--parity-summary",
        default=str(_repo_root() / "output" / "native_parity_local" / "parity_summary.json"),
        help="Path to parity_summary.json",
    )
    parser.add_argument(
        "--parity-steps",
        default="",
        help="Optional path to parity_steps.jsonl (for step count cross-check)",
    )
    parser.add_argument(
        "--out-dir",
        default=str(_repo_root() / "output" / "native_parity_local"),
        help="Directory for parity_report.md",
    )
    args = parser.parse_args()
    summary_path = Path(args.parity_summary).resolve()
    out_dir = Path(args.out_dir).resolve()

    if not summary_path.is_file():
        print(f"Missing parity summary: {summary_path}", file=sys.stderr)
        return 1

    summary = _load_summary(summary_path)
    violations = list_default_parity_gate_violations(summary)
    steps_path = Path(args.parity_steps).resolve() if args.parity_steps else out_dir / "parity_steps.jsonl"
    n_steps = _count_jsonl_lines(steps_path)

    ts = datetime.now(tz=UTC).isoformat()
    gate_state = "pass" if not violations else "fail"

    lines = [
        "# Native parity report",
        "",
        f"**Generated:** {ts}",
        f"**Source:** `{summary_path}`",
        "",
        "## Summary metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| total_steps | {summary.total_steps} |",
        f"| action_match_rate | {summary.action_match_rate:.8f} |",
        f"| active_constraints_match_rate | {summary.active_constraints_match_rate:.8f} |",
        f"| max_corrected_linf | {summary.max_corrected_linf:.6e} |",
        f"| p95_corrected_linf | {summary.p95_corrected_linf:.6e} |",
        f"| max_corrected_l2 | {summary.max_corrected_l2:.6e} |",
        f"| p95_corrected_l2 | {summary.p95_corrected_l2:.6e} |",
        "",
    ]
    if n_steps is not None:
        lines.extend(
            [
                f"**parity_steps.jsonl lines:** {n_steps} (expected {summary.total_steps} from summary)",
                "",
            ]
        )

    lines.extend(
        [
            "## Default gates (`conicshield.parity.gates`)",
            "",
            f"**Gate state:** **{gate_state}**",
            "",
        ]
    )
    if violations:
        lines.append("Violations:")
        for v in violations:
            lines.append(f"- {v}")
    else:
        lines.append("No violations.")
    lines.append("")

    out_path = out_dir / "parity_report.md"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(out_path)
    return 0 if gate_state == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
