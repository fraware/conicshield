"""CS-SOLVER-106 / 107: active-set residuals and fail-closed status normalization."""

from __future__ import annotations

import numpy as np

from conicshield.backends.status import CanonicalSolverStatus, normalize_solver_status
from conicshield.specs.schema import (
    BoxConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)
from conicshield.specs.shield_qp import parse_safety_spec_for_shield
from conicshield.verification.active_set import active_constraints_from_residuals
from conicshield.verification.feasibility import verify_candidate_before_release
from conicshield.verification.residuals import ResidualReport, ResidualTolerances


def test_status_unknown_for_legacy_success_heuristics() -> None:
    for raw in ("1", "true", "ok", "yes", "success_maybe"):
        assert normalize_solver_status(raw) is CanonicalSolverStatus.UNKNOWN


def test_turn_feasibility_active_only_when_residual_near_zero() -> None:
    spec = SafetySpec(
        spec_id="stabilization/cs-solver-106",
        version="0.1.0",
        action_dim=3,
        constraints=[
            SimplexConstraint(total=1.0),
            BoxConstraint(lower=[0.0, 0.0, 0.0], upper=[1.0, 1.0, 1.0]),
            TurnFeasibilityConstraint(allowed_actions=[0, 1]),
        ],
    )
    data = parse_safety_spec_for_shield(spec)
    # Feasible point with prohibited action at 0 → turn_feasibility[2] active.
    x = np.array([0.5, 0.5, 0.0], dtype=np.float64)
    report = verify_candidate_before_release(x, data, raw_status="optimal", proposed_action=x)
    assert "turn_feasibility[2]" in report.active_constraints

    # Presence of prohibition alone must not label activity when x[2] is far from 0.
    residual = ResidualReport(
        finite=True,
        action_dim_ok=True,
        simplex_residual=0.0,
        lower_residuals=np.zeros(3),
        upper_residuals=np.zeros(3),
        prohibited_residuals=np.array([0.0, 0.0, 0.6]),
        rate_residuals=None,
        max_equality_residual=0.0,
        max_inequality_residual=0.6,
        objective_residual=None,
    )
    bad = np.array([0.2, 0.2, 0.6], dtype=np.float64)
    active = active_constraints_from_residuals(
        residual,
        data,
        candidate=bad,
        tolerances=ResidualTolerances(active_tol=1e-6),
    )
    assert "turn_feasibility[2]" not in active
