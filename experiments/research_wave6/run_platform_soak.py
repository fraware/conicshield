#!/usr/bin/env python3
"""Wave 6: R4 platform-matrix soak (extends clean-env soak)."""

from __future__ import annotations

from pathlib import Path

from conicshield.experimental.assurance.platform_soak import (
    aggregate_platform_soaks,
    run_platform_soak,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "research" / "wave6" / "platform_soak"


def main() -> int:
    report = run_platform_soak(
        output_dir=OUT,
        exact_command="python experiments/research_wave6/run_platform_soak.py",
    )
    agg = aggregate_platform_soaks([report])
    (OUT / "platform_soak_aggregate.json").write_text(
        __import__("json").dumps(agg, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"platform soak all_passed={report.all_passed} blockers={len(report.r4_blockers)}")
    return 0 if report.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
