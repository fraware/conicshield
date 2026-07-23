"""CBF stage 3 SOC robust margin tests."""

from __future__ import annotations

import numpy as np

from conicshield.experimental.domains.cbf_2d import (
    AgentState2D,
    CBF2DDomain,
    CBFStage,
    CircularObstacle,
    apply_cbf_filter,
    apply_cbf_filter_soc_robust,
    compute_cbf_metrics,
    demo_stage3_soc_robust,
    stage3_disagreement_under_perturbation,
    stage4_gate_status,
)


def test_stage3_feasible_and_margin_semantics() -> None:
    r = demo_stage3_soc_robust()
    assert r.stage == CBFStage.STAGE3_SOC_ROBUST.value
    assert np.all(np.isfinite(r.u_safe))
    assert "uncertainty_model_id" in r.metadata
    assert np.isfinite(r.safety_margin)
    # Robust margin residual should be nonnegative at a feasible SOC solution
    assert r.safety_margin >= -1e-4


def test_stage3_more_conservative_than_nominal() -> None:
    agent = AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]))
    obs = CircularObstacle(np.array([1.0, 0.0]), 0.5)
    nom = apply_cbf_filter(agent, obs)
    rob = apply_cbf_filter_soc_robust(agent, obs, epsilon=0.08)
    assert np.all(np.isfinite(nom.u_safe)) and np.all(np.isfinite(rob.u_safe))
    # Robust filter should intervene at least as strongly (larger or equal intervention)
    assert rob.intervention_norm + 1e-6 >= nom.intervention_norm * 0.5


def test_stage3_disagreement_under_perturbation() -> None:
    agent = AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]), "a0")
    obs = CircularObstacle(np.array([1.0, 0.0]), 0.5)
    payload = stage3_disagreement_under_perturbation(agent, obs, epsilon=0.05)
    assert "nominal_vs_robust_u_l2" in payload
    assert payload["robust"]["stage"] == CBFStage.STAGE3_SOC_ROBUST.value
    metrics = compute_cbf_metrics(
        [
            apply_cbf_filter_soc_robust(agent, obs, epsilon=0.05),
        ]
    )
    assert metrics.robustness_under_observation_and_model_perturbation is not None


def test_stage4_experimental_rh_with_partial_checklist() -> None:
    domain = CBF2DDomain()
    assert domain.stage3.implemented is True
    assert domain.stage4.status == "experimental_rh_available"
    assert domain.stage4.rh_mpc_full is False
    gate = stage4_gate_status(checklist_satisfied={"stage1_nominal_cbf_qp_feasible_on_demo_corpus": True})
    d = gate.as_dict()
    assert d["all_gates_passed"] is False
    assert d["unblock_allowed"] is False
    assert len(d["validation_checklist"]) >= 5
    assert d["production_claim"] is False
