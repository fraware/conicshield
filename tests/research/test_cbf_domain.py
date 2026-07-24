"""CBF domain stage 1–2 / R13 tests."""

from __future__ import annotations

import numpy as np
import pytest

from conicshield.experimental.adapters.track1_protocols import ReleaseDecision
from conicshield.experimental.domains.cbf_2d import (
    BATCH_MODE_COMPILED,
    BATCH_MODE_SEQUENTIAL,
    DYNAMICS_MODEL_ID,
    AgentState2D,
    CBF2DDomain,
    CBFBaseline,
    CBFStage,
    CircularObstacle,
    apply_cbf_filter,
    apply_cbf_filter_batch,
    apply_cbf_filter_batched,
    barrier_value,
    compute_cbf_metrics,
    demo_stage1_scenario,
    demo_stage2_batch,
    validate_cbf_inputs,
)


def test_barrier_and_stage1_intervention() -> None:
    agent = AgentState2D(
        position=np.array([0.0, 0.0], dtype=np.float64),
        u_desired=np.array([1.0, 0.0], dtype=np.float64),
    )
    obs = CircularObstacle(center=np.array([1.0, 0.0], dtype=np.float64), radius=0.5)
    assert barrier_value(agent.position, obs) > 0
    result = apply_cbf_filter(agent, obs)
    assert result.stage == CBFStage.STAGE1_NOMINAL.value
    assert np.all(np.isfinite(result.u_safe))
    assert result.verification is not None
    assert result.verification.finite_value is True
    assert result.verification.norm_bound_residual <= 1e-5
    assert result.verification.cbf_residual <= 1e-5
    assert result.release_decision == ReleaseDecision.EXPERIMENTAL_ONLY
    assert result.metadata["dynamics_model_id"] == DYNAMICS_MODEL_ID
    assert result.canonical_status.value in {"optimal", "optimal_inaccurate", "unknown"} or result.intervened


def test_input_validation_rejects_bad_inputs() -> None:
    agent = AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]))
    obs = CircularObstacle(np.array([1.0, 0.0]), 0.5)
    with pytest.raises(ValueError, match="r > 0"):
        validate_cbf_inputs(agent, CircularObstacle(np.array([1.0, 0.0]), 0.0), alpha=1.0, u_max=1.0)
    with pytest.raises(ValueError, match="alpha"):
        validate_cbf_inputs(agent, obs, alpha=-0.1, u_max=1.0)
    with pytest.raises(ValueError, match="u_max"):
        validate_cbf_inputs(agent, obs, alpha=1.0, u_max=0.0)
    with pytest.raises(ValueError, match="epsilon"):
        validate_cbf_inputs(agent, obs, alpha=1.0, u_max=1.0, epsilon=-1.0)
    with pytest.raises(ValueError, match="finite 2D"):
        validate_cbf_inputs(
            AgentState2D(np.array([np.nan, 0.0]), np.array([1.0, 0.0])),
            obs,
            alpha=1.0,
            u_max=1.0,
        )


def test_no_filter_baseline() -> None:
    r = apply_cbf_filter(
        AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0])),
        CircularObstacle(np.array([1.0, 0.0]), 0.5),
        baseline=CBFBaseline.NO_FILTER,
    )
    assert r.intervened is False
    assert np.allclose(r.u_safe, r.u_desired)


def test_moreau_and_exact_baselines_explicitly_unavailable() -> None:
    agent = AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]))
    obs = CircularObstacle(np.array([1.0, 0.0]), 0.5)
    m = apply_cbf_filter(agent, obs, baseline=CBFBaseline.MOREAU_FILTER)
    e = apply_cbf_filter(agent, obs, baseline=CBFBaseline.EXACT_VS_SMOOTHED)
    assert m.fallback and e.fallback
    assert m.metadata.get("comparison_baseline") is False
    assert e.metadata.get("comparison_baseline") is False
    assert m.metadata.get("stub") is not True
    assert m.release_decision == ReleaseDecision.FALLBACK
    metrics = compute_cbf_metrics([m, e, apply_cbf_filter(agent, obs)])
    assert metrics.unavailable_baseline_excluded_count == 2
    # Unavailable NaN stubs must not inflate comparison intervention stats alone
    assert metrics.intervention_frequency <= 1.0


def test_release_not_based_on_solver_value_alone() -> None:
    agent = AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]))
    obs = CircularObstacle(np.array([1.0, 0.0]), 0.5)
    r = apply_cbf_filter(agent, obs)
    assert r.verification is not None
    assert r.verification.passed is True
    assert "cvxpy_value_alone_insufficient" not in r.verification.notes
    # Reject path: nonfinite candidate never releases
    from conicshield.experimental.domains.cbf_2d import (
        _public_solver_provenance,
        cbf_affine_constraint,
        verify_cbf_candidate,
    )

    a, b = cbf_affine_constraint(agent.position, obs, alpha=1.0)
    bad = verify_cbf_candidate(
        np.array([np.nan, np.nan]),
        u_des=agent.u_desired,
        a=a,
        b=b,
        u_max=1.0,
        solver_status="optimal",
        solver_provenance=_public_solver_provenance("CLARABEL"),
    )
    assert bad.passed is False
    assert bad.release_decision == ReleaseDecision.REJECT


def test_stage2_compiled_batch_and_metrics() -> None:
    results = demo_stage2_batch()
    assert len(results) == 2
    assert all(r.stage == CBFStage.STAGE2_BATCHED.value for r in results)
    assert all(r.metadata.get("batch_mode") == BATCH_MODE_COMPILED for r in results)
    assert all(r.metadata.get("batch_equals_sequential") is True for r in results)
    metrics = compute_cbf_metrics(results)
    assert 0.0 <= metrics.intervention_frequency <= 1.0
    assert metrics.task_completion >= 0.0
    domain = CBF2DDomain()
    assert domain.stage4.status == "experimental_rh_available"
    assert domain.stage4.rh_mpc_full is False
    assert domain.stage4.recursive_feasibility is False
    assert domain.stage4.multi_robot is False
    assert domain.stage3.implemented is True
    assert demo_stage1_scenario().agent_id == "a0"


def test_batch_matches_sequential_per_row() -> None:
    agents = [
        AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]), "a0"),
        AgentState2D(np.array([0.5, 0.5]), np.array([0.2, -0.8]), "a1"),
    ]
    obstacles = [
        CircularObstacle(np.array([1.0, 0.0]), 0.5, "o0"),
        CircularObstacle(np.array([0.0, 0.0]), 0.3, "o1"),
    ]
    batch = apply_cbf_filter_batch(agents, obstacles, assert_matches_sequential=True)
    seq = apply_cbf_filter_batched(agents, obstacles)
    assert all(r.metadata["batch_emulation"] == BATCH_MODE_SEQUENTIAL for r in seq)
    for b, s in zip(batch, seq, strict=True):
        assert np.allclose(b.u_safe, s.u_safe, atol=1e-4)


def test_batched_pair_length() -> None:
    with pytest.raises(ValueError):
        apply_cbf_filter_batch(
            [AgentState2D(np.zeros(2), np.ones(2))],
            [],
        )
