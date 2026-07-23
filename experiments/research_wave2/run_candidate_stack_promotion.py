#!/usr/bin/env python3
"""Wave 2: candidate stack promotion (Clarabel approved vs SCS candidate)."""

from __future__ import annotations

from pathlib import Path

from conicshield.experimental.solver_assurance.promotion_protocol import run_candidate_stack_promotion

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "research" / "wave2" / "candidate_stack_promotion"


def main() -> None:
    protocol = run_candidate_stack_promotion(
        output_dir=OUT,
        exact_command="python experiments/research_wave2/run_candidate_stack_promotion.py",
    )
    freq = protocol.results.get("disagreement_frequency") or {}
    print(
        f"{protocol.approved_backend} vs {protocol.candidate_backend}: "
        f"status_rate={freq.get('status_disagreement_rate')} "
        f"consequential_rate={freq.get('consequential_rate')}"
    )


if __name__ == "__main__":
    main()
