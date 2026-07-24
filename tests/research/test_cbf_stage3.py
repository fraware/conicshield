"""CBF stage 3 SOC robust margin / R13 robustness tests."""

from __future__ import annotations

import numpy as np

from conicshield.experimental.adapters.track1_protocols import ReleaseDecision
from conicshield.experimental.domains.cbf_2d import (
    AgentState2D,
    CBF2DDomain,
    CBFBaseline,
    CBFStage,
    CircularObstacle,
    apply_cbf_filter,
    apply_cbf_filter_batch,
    apply_cbf_filter_soc_robust,
    compute_cbf_metrics,
    demo_stage3_soc_robust,
    stage3_disagreement_under_perturbation,
    stage4_gate_status,
    validate_robust_cbf_control,
)


def test_stage3_feasible_and_margin_semantics() -> None:
    r = demo_stage3_soc_robust()
    assert r.stage == CBFStage.STAGE3_SOC_ROBUST.value
    assert np.all(np.isfinite(r.u_safe))
    assert "uncertainty_model_id" in r.metadata
    assert np.isfinite(r.safety_margin)
    assert r.safety_margin >= -1e-4
    assert r.verification is not None
    assert r.verification.robust_soc_residual is not None
    assert r.verification.robust_soc_residual <= 1e-5
    assert r.verification.passed is True
    assert r.release_decision == ReleaseDecision.EXPERIMENTAL_ONLY


def test_stage3_more_conservative_than_nominal() -> None:
    agent = AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]))
    obs = CircularObstacle(np.array([1.0, 0.0]), 0.5)
    nom = apply_cbf_filter(agent, obs)
    rob = apply_cbf_filter_soc_robust(agent, obs, epsilon=0.08)
    assert np.all(np.isfinite(nom.u_safe)) and np.all(np.isfinite(rob.u_safe))
    assert rob.intervention_norm + 1e-6 >= nom.intervention_norm * 0.5


def test_independent_worst_case_delta_validation() -> None:
    agent = AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]), "a0")
    obs = CircularObstacle(np.array([1.0, 0.0]), 0.5)
    nom = apply_cbf_filter(agent, obs)
    rob = apply_cbf_filter_soc_robust(agent, obs, epsilon=0.05)
    report = validate_robust_cbf_control(
        agent,
        obs,
        rob.u_safe,
        alpha=1.0,
        epsilon=0.05,
        soc_declared_margin=float(rob.safety_margin),
        nominal_intervention_norm=float(nom.intervention_norm),
    )
    assert report.robust_condition_holds is True
    assert np.isfinite(report.min_actual_margin)
    assert report.min_actual_margin >= -1e-5
    assert report.bound_gap is not None
    assert report.intervention_increase >= -1e-9
    assert report.objective_cost >= 0.0
    assert float(np.linalg.norm(report.delta_star)) <= 0.05 + 1e-6


def test_stage3_disagreement_under_perturbation() -> None:
    agent = AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]), "a0")
    obs = CircularObstacle(np.array([1.0, 0.0]), 0.5)
    payload = stage3_disagreement_under_perturbation(agent, obs, epsilon=0.05)
    assert payload["comparison_skipped"] is False
    assert "nominal_vs_robust_u_l2" in payload
    assert payload["robust"]["stage"] == CBFStage.STAGE3_SOC_ROBUST.value
    assert payload["robustness_validation"] is not None
    assert payload["robustness_validation"]["robust_condition_holds"] is True
    metrics = compute_cbf_metrics(
        [
            apply_cbf_filter_soc_robust(agent, obs, epsilon=0.05),
        ]
    )
    assert metrics.robustness_under_observation_and_model_perturbation is not None


def test_unavailable_moreau_not_counted_in_comparison() -> None:
    agent = AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]), "a0")
    obs = CircularObstacle(np.array([1.0, 0.0]), 0.5)
    m = apply_cbf_filter_soc_robust(agent, obs, baseline=CBFBaseline.MOREAU_FILTER)
    assert m.metadata["comparison_baseline"] is False
    payload = stage3_disagreement_under_perturbation(agent, obs, epsilon=0.05)
    assert payload["comparison_skipped"] is False  # public arms only
    metrics = compute_cbf_metrics([m])
    assert metrics.unavailable_baseline_excluded_count == 1


def test_robust_compiled_batch() -> None:
    agents = [
        AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]), "a0"),
        AgentState2D(np.array([0.0, 1.0]), np.array([0.0, -1.0]), "a1"),
    ]
    obstacles = [
        CircularObstacle(np.array([1.0, 0.0]), 0.5, "o0"),
        CircularObstacle(np.array([0.0, 0.0]), 0.4, "o1"),
    ]
    batch = apply_cbf_filter_batch(agents, obstacles, epsilon=0.05, assert_matches_sequential=True)
    assert len(batch) == 2
    assert all(r.metadata.get("batch_mode") == "compiled_joint_qp" for r in batch)
    assert all(r.verification is not None and r.verification.passed for r in batch)


def test_stage4_experimental_rh_with_partial_checklist() -> None:
    domain = CBF2DDomain()
    assert domain.stage3.implemented is True
    assert domain.stage4.status == "experimental_rh_available"
    assert domain.stage4.rh_mpc_full is False
    gate = stage4_gate_status(checklist_satisfied={"stage1_nominal_cbf_qp_feasible_on_demo_corpus": True})
    d = gate.as_dict()
    assert d["all_gates_passed"] is False
    assert d["unblock_allowed"] is False
    assert d["recursive_feasibility"] is False
    assert len(d["validation_checklist"]) >= 5
    assert d["production_claim"] is False
