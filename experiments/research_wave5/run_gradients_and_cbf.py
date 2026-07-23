#!/usr/bin/env python3
"""Wave 5: research gradient adapters + CBF stage 3."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from conicshield.experimental.corpus.generate import load_all_scenarios, load_manifest
from conicshield.experimental.corpus.paths import CORPUS_VERSION
from conicshield.experimental.domains.cbf_2d import (
    AgentState2D,
    CBF2DDomain,
    CircularObstacle,
    compute_cbf_metrics,
    demo_stage3_soc_robust,
    stage3_disagreement_under_perturbation,
    stage4_gate_status,
)
from conicshield.experimental.gradients.observatory import (
    observe_proposed_action_fd,
    render_observatory_report_markdown,
)
from conicshield.specs.schema import SafetySpec

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "research" / "wave5" / "gradients_and_cbf"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scenarios = [
        s
        for s in load_all_scenarios()
        if s["family"] == "active_set_transition_neighborhoods"
    ][:6]
    reports = []
    for scenario in scenarios:
        spec = SafetySpec.model_validate(scenario["spec"])
        reports.append(
            observe_proposed_action_fd(
                spec=spec,
                proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
                previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
                reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
                scenario_id=scenario["scenario_id"],
                corpus_version=CORPUS_VERSION,
                include_research_gradients=True,
                smoothing_epsilon=1e-2,
            )
        )
    md = render_observatory_report_markdown(reports)
    (OUT / "observatory_research_grads.md").write_text(md, encoding="utf-8")
    (OUT / "observatory_research_grads.json").write_text(
        json.dumps([r.as_dict() for r in reports], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    stage3 = demo_stage3_soc_robust()
    disagree = stage3_disagreement_under_perturbation(
        AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]), "a0"),
        CircularObstacle(np.array([1.0, 0.0]), 0.5, "o0"),
        epsilon=0.05,
    )
    domain = CBF2DDomain()
    gate = stage4_gate_status(
        checklist_satisfied={
            "stage1_nominal_cbf_qp_feasible_on_demo_corpus": True,
            "stage2_batched_agents_metrics_recorded": True,
            "stage3_soc_robust_margin_feasible_under_declared_noise_model": np.all(
                np.isfinite(stage3.u_safe)
            ),
            "stage3_robust_margin_disagreement_under_perturbation_quantified": True,
            # Remaining gates intentionally false — stage 4 stays blocked
            "single_step_safety_margin_nonnegative_on_held_out_nominal_cases": False,
            "no_unexplained_infeasibility_rate_above_threshold": False,
        }
    )
    metrics = compute_cbf_metrics([stage3])
    payload = {
        "corpus_version": load_manifest().get("corpus_version"),
        "cbf_domain": domain.as_dict(),
        "stage3": stage3.as_dict(),
        "stage3_disagreement": disagree,
        "stage3_metrics": metrics.as_dict(),
        "stage4_gate": gate.as_dict(),
        "mode_labels": {
            "exact_backend_gradient": "moreau_compiled_solver_backward_experimental",
            "smoothed_backend_gradient": "softplus_moreau_qp_experimental",
            "exact_research_kkt": "research_adapter",
            "smoothed_research_projection": "research_adapter",
        },
    }
    (OUT / "gradients_and_cbf.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"stage3_status={stage3.solver_status} stage4_blocked={gate.status} "
        f"checklist_all={gate.as_dict()['all_gates_passed']}"
    )


if __name__ == "__main__":
    main()
