#!/usr/bin/env python3
"""Wave 1 entry: public-solver shadow harness."""

from __future__ import annotations

from pathlib import Path

from conicshield.experimental.solver_assurance.shadow_harness import run_shadow_harness


def main() -> None:
    out = Path("output/research/shadow_harness")
    summary = run_shadow_harness(
        output_dir=out,
        exact_command="python experiments/research_wave1/run_shadow_harness.py",
    )
    print(
        f"shadow harness: {summary['shadowed_count']}/{summary['scenario_count']} shadowed; "
        f"status disagreements={summary['status_disagreement_count']}"
    )


if __name__ == "__main__":
    main()
