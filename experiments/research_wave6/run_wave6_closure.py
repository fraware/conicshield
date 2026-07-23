#!/usr/bin/env python3
"""Wave 6: agreement study, platform soak, stage-4 gate, deliverable packaging."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from conicshield.experimental.assurance.platform_soak import (
    aggregate_platform_soaks,
    run_platform_soak,
)
from conicshield.experimental.corpus.active_set_benchmark import (
    build_active_set_transition_benchmark,
    write_benchmark_manifest,
)
from conicshield.experimental.corpus.generate import load_all_scenarios, load_manifest
from conicshield.experimental.domains.stage4_gate import evaluate_stage4_gate
from conicshield.experimental.frontiers.safety_response_map import (
    export_safety_response_map,
    write_safety_response_map,
)
from conicshield.experimental.gradients.agreement_study import (
    run_agreement_study,
    write_ci_small_fixture,
)
from conicshield.experimental.training.r6_decision_scaffold import write_r6_decision_scaffold
from conicshield.specs.schema import SafetySpec

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "research" / "wave6"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # 1) CI-small agreement study (+ optional fixture refresh path)
    agree = run_agreement_study(
        ci_small=True,
        output_dir=OUT / "agreement_study",
        exact_command="python experiments/research_wave6/run_wave6_closure.py",
    )
    write_ci_small_fixture(agree)

    # 2) Platform soak + single-host aggregate schema exercise
    soak = run_platform_soak(
        output_dir=OUT / "platform_soak",
        exact_command="python experiments/research_wave6/run_wave6_closure.py::platform_soak",
    )
    agg = aggregate_platform_soaks([soak])
    (OUT / "platform_soak" / "platform_soak_aggregate.json").write_text(
        json.dumps(agg, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # 3) Stage-4 gate evaluator (expected blocked / pending)
    gate = evaluate_stage4_gate(evidence_dir=OUT / "stage4_gate")

    # 4) Active-set benchmark packaging
    bench = build_active_set_transition_benchmark()
    (OUT / "active_set_transition_benchmark.json").write_text(
        json.dumps(bench.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_benchmark_manifest()

    # 5) Safety response map from frontiers
    scenario = load_all_scenarios()[0]
    spec = SafetySpec.model_validate(scenario["spec"])
    response_map = export_safety_response_map(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
    )
    write_safety_response_map(OUT / "safety_response_map.json", response_map)

    # 6) R6 decision scaffold (BLOCKED, no results)
    r6_path = write_r6_decision_scaffold(path=OUT / "R6_DECISION_REPORT_SCAFFOLD.json")

    summary = {
        "corpus_version": load_manifest().get("corpus_version"),
        "agreement_overall": agree.overall,
        "agreement_negative": agree.negative_results,
        "platform_soak_passed": soak.all_passed,
        "stage4_gate": gate.as_dict(),
        "active_set_benchmark": {
            "benchmark_version": bench.benchmark_version,
            "n_cases": len(bench.cases),
            "regimes": bench.expected_regimes,
        },
        "safety_response_map_regimes": response_map.regime_counts,
        "r6_scaffold": str(r6_path),
        "honest_notes": [
            "research KKT ≠ native exact_backend_gradient",
            "stage 4 remains blocked unless all required criteria pass",
            "R6 remains BLOCKED — scaffold has no training results",
            "R4 multi-host soak still required for promotion",
        ],
    }
    (OUT / "wave6_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"wave6 corpus={summary['corpus_version']} "
        f"kkt_avail={agree.overall.get('kkt_available_rate')} "
        f"stage4={gate.stage4_status} "
        f"soak={soak.all_passed}"
    )


if __name__ == "__main__":
    main()
