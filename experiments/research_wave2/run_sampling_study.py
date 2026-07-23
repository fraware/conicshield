#!/usr/bin/env python3
"""Wave 2: sampling study + candidate-stack promotion + hypothesis evaluation."""

from __future__ import annotations

import json
from pathlib import Path

from conicshield.experimental.solver_assurance.hypotheses_eval import build_evaluation_report
from conicshield.experimental.solver_assurance.promotion_protocol import run_candidate_stack_promotion
from conicshield.experimental.solver_assurance.sampling_study import run_sampling_study

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "research" / "wave2"
FIXTURES = ROOT / "research" / "solver-assurance-and-gradients" / "fixtures"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    FIXTURES.mkdir(parents=True, exist_ok=True)

    study = run_sampling_study(
        output_dir=OUT / "sampling_study",
        ci_small=True,
        exact_command="python experiments/research_wave2/run_sampling_study.py",
    )
    # Committed CI-small fixture (summary without bulky internals already)
    fixture_path = FIXTURES / "sampling_study_ci_small.json"
    fixture_path.write_text(json.dumps(study.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    promo = run_candidate_stack_promotion(
        output_dir=OUT / "candidate_stack_promotion",
        exact_command="python experiments/research_wave2/run_candidate_stack_promotion.py",
    )
    report = build_evaluation_report(sampling_study=study.as_dict())
    report.to_json(OUT / "hypothesis_evaluation.json")
    report.to_json(FIXTURES / "hypothesis_evaluation_wave2.json")

    print(f"sampling cells={len(study.results)} fixture={fixture_path}")
    print(f"promotion affected_families={promo.results.get('affected_scenario_families')}")
    print(f"hypothesis evaluations={len(report.evaluations)}")


if __name__ == "__main__":
    main()
