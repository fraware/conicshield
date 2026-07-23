"""SolverDisagreement record tests."""

from __future__ import annotations

import numpy as np

from conicshield.experimental.adapters.projection import ResearchProjectionResult
from conicshield.experimental.adapters.track1_protocols import CanonicalSolverStatus
from conicshield.experimental.solver_assurance.disagreement import compare_projections
from conicshield.experimental.solver_assurance.sampling import (
    SamplingContext,
    SamplingPolicyId,
    all_sampling_policies,
    select_for_shadow,
)


def _result(
    action: list[float],
    *,
    status: CanonicalSolverStatus = CanonicalSolverStatus.OPTIMAL,
    active: list[str] | None = None,
    eq: float = 0.0,
    ineq: float = 0.0,
    obj: float | None = 1.0,
    iterations: int | None = 10,
) -> ResearchProjectionResult:
    a = np.asarray(action, dtype=np.float64)
    return ResearchProjectionResult(
        proposed_action=a,
        corrected_action=a,
        intervened=False,
        intervention_norm=0.0,
        solver_status=str(status),
        canonical_status=status,
        objective_value=obj,
        active_constraints=active or ["simplex"],
        iterations=iterations,
        equality_residual=eq,
        inequality_residual=ineq,
    )


def test_disagreement_fields() -> None:
    primary = _result([0.25, 0.25, 0.25, 0.25], active=["simplex"])
    shadow = _result([0.5, 0.5, 0.0, 0.0], active=["simplex", "box_upper"], obj=1.5, iterations=20)
    d = compare_projections(primary, shadow)
    assert d.corrected_action_l2 > 0
    assert d.corrected_action_linf > 0
    assert d.objective_gap_abs is not None
    assert "box_upper" in d.active_set_symmetric_difference
    assert d.iteration_ratio == 2.0
    assert set(d.as_dict().keys()) >= {
        "status_disagreement",
        "release_disagreement",
        "corrected_action_l2",
        "corrected_action_linf",
        "objective_gap_abs",
        "objective_gap_rel",
        "equality_residual_gap",
        "inequality_residual_gap",
        "active_set_symmetric_difference",
        "iteration_ratio",
        "timeout_asymmetry",
        "warm_cold_disagreement",
    }


def test_sampling_policies_cover_required_ids() -> None:
    ids = {p.policy_id for p in all_sampling_policies()}
    assert ids == set(SamplingPolicyId)


def test_select_for_shadow_budget() -> None:
    primary = _result([0.25] * 4, eq=0.0, ineq=0.1)
    ctxs = [
        SamplingContext(scenario_id="a", structural_fingerprint="1", primary=primary),
        SamplingContext(
            scenario_id="b",
            structural_fingerprint="2",
            primary=_result([0.25] * 4, eq=1.0, ineq=1.0),
        ),
    ]
    residual = next(p for p in all_sampling_policies() if p.policy_id == SamplingPolicyId.RESIDUAL)
    selected = select_for_shadow(ctxs, residual, budget_fraction=0.5)
    assert selected == ["b"]
