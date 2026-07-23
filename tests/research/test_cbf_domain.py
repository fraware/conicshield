"""CBF domain stage 1–2 tests."""

from __future__ import annotations

import numpy as np

from conicshield.experimental.domains.cbf_2d import (
    AgentState2D,
    CBF2DDomain,
    CBFBaseline,
    CBFStage,
    CircularObstacle,
    apply_cbf_filter,
    apply_cbf_filter_batched,
    barrier_value,
    compute_cbf_metrics,
    demo_stage1_scenario,
    demo_stage2_batch,
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
    # Desired control points into obstacle neighborhood; filter should often intervene
    assert result.canonical_status.value in {"optimal", "optimal_inaccurate", "unknown"} or result.intervened


def test_no_filter_baseline() -> None:
    r = apply_cbf_filter(
        AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0])),
        CircularObstacle(np.array([1.0, 0.0]), 0.5),
        baseline=CBFBaseline.NO_FILTER,
    )
    assert r.intervened is False
    assert np.allclose(r.u_safe, r.u_desired)


def test_moreau_and_exact_baselines_fail_closed() -> None:
    agent = AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]))
    obs = CircularObstacle(np.array([1.0, 0.0]), 0.5)
    m = apply_cbf_filter(agent, obs, baseline=CBFBaseline.MOREAU_FILTER)
    e = apply_cbf_filter(agent, obs, baseline=CBFBaseline.EXACT_VS_SMOOTHED)
    assert m.fallback and e.fallback


def test_stage2_batch_and_metrics() -> None:
    results = demo_stage2_batch()
    assert len(results) == 2
    assert all(r.stage == CBFStage.STAGE2_BATCHED.value for r in results)
    metrics = compute_cbf_metrics(results)
    assert 0.0 <= metrics.intervention_frequency <= 1.0
    assert metrics.task_completion >= 0.0
    domain = CBF2DDomain()
    assert domain.stage4.status == "experimental_rh_available"
    assert domain.stage3.implemented is True
    assert demo_stage1_scenario().agent_id == "a0"


def test_batched_pair_length() -> None:
    try:
        apply_cbf_filter_batched(
            [AgentState2D(np.zeros(2), np.ones(2))],
            [],
        )
        ok = False
    except ValueError:
        ok = True
    assert ok
