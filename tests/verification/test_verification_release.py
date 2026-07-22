"""Unit and integration tests for S2 verification / release / fallback."""

from __future__ import annotations

import json

import numpy as np
import pytest

from conicshield.backends.status import CanonicalSolverStatus, normalize_solver_status
from conicshield.core.result import ProjectionResult, sanitize_metadata
from conicshield.specs.schema import BoxConstraint, FailSafePolicy, SafetySpec, SimplexConstraint
from conicshield.specs.shield_qp import parse_safety_spec_for_shield
from conicshield.verification.fallback import (
    FallbackConfig,
    SolveAttemptResult,
    build_fail_safe_action,
    run_verified_release_pipeline,
)
from conicshield.verification.feasibility import (
    VerificationReleaseError,
    verify_candidate_before_release,
)
from conicshield.verification.release_policy import ReleaseDecision, ReleasePolicy, intervention_threshold
from conicshield.verification.residuals import ResidualTolerances, evaluate_residuals


def _data() -> tuple[SafetySpec, object]:
    spec = SafetySpec(
        spec_id="verification/unit",
        action_dim=3,
        constraints=[
            SimplexConstraint(total=1.0),
            BoxConstraint(lower=[0.0, 0.0, 0.0], upper=[1.0, 1.0, 1.0]),
        ],
        fail_safe_policy=FailSafePolicy.UNIFORM_ADMISSIBLE,
    )
    return spec, parse_safety_spec_for_shield(spec)


def test_unknown_status_does_not_pass() -> None:
    _, data = _data()
    x = np.array([0.5, 0.5, 0.0], dtype=np.float64)
    report = verify_candidate_before_release(
        x,
        data,
        raw_status="completely_unrecognized_token",
        proposed_action=x,
    )
    assert not report.passed
    assert report.canonical_status is CanonicalSolverStatus.UNKNOWN
    assert report.classification.decision is ReleaseDecision.REJECTED_STATUS


def test_nonfinite_candidate_rejected() -> None:
    _, data = _data()
    x = np.array([np.nan, 0.5, 0.5], dtype=np.float64)
    report = verify_candidate_before_release(
        x,
        data,
        raw_status="optimal",
        proposed_action=np.array([1 / 3, 1 / 3, 1 / 3]),
    )
    assert not report.passed
    assert report.classification.decision is ReleaseDecision.REJECTED_NONFINITE


def test_residual_rejection_path() -> None:
    _, data = _data()
    # Violates simplex and box.
    x = np.array([2.0, 2.0, 2.0], dtype=np.float64)
    report = verify_candidate_before_release(
        x,
        data,
        raw_status="optimal",
        proposed_action=np.array([1 / 3, 1 / 3, 1 / 3]),
        policy=ReleasePolicy(tolerances=ResidualTolerances(abs_tol=1e-6, rel_tol=1e-6)),
    )
    assert not report.passed
    assert report.classification.decision is ReleaseDecision.REJECTED_RESIDUAL


def test_optimal_feasible_candidate_accepted() -> None:
    _, data = _data()
    x = np.array([0.2, 0.3, 0.5], dtype=np.float64)
    report = verify_candidate_before_release(
        x,
        data,
        raw_status="optimal",
        proposed_action=x,
    )
    assert report.passed
    assert report.classification.decision is ReleaseDecision.ACCEPTED_PRIMARY
    assert "simplex.total" in report.active_constraints


def test_status_normalization_aliases() -> None:
    assert normalize_solver_status("solved") is CanonicalSolverStatus.OPTIMAL
    assert normalize_solver_status("optimal_inaccurate") is CanonicalSolverStatus.OPTIMAL_INACCURATE
    assert normalize_solver_status("max_iters_reached") is CanonicalSolverStatus.ITERATION_LIMIT
    assert normalize_solver_status(None) is CanonicalSolverStatus.UNKNOWN


def test_injected_numerical_corruption_detected() -> None:
    _, data = _data()
    clean = np.array([0.25, 0.25, 0.5], dtype=np.float64)
    corrupted = clean.copy()
    corrupted[0] = np.inf
    report = verify_candidate_before_release(
        corrupted,
        data,
        raw_status="optimal",
        proposed_action=clean,
    )
    assert report.classification.decision is ReleaseDecision.REJECTED_NONFINITE


def test_fallback_to_fail_safe() -> None:
    _, data = _data()
    proposed = np.array([0.9, 0.05, 0.05], dtype=np.float64)

    def _primary(*, warm_start: bool) -> SolveAttemptResult:
        del warm_start
        return SolveAttemptResult(
            candidate=np.array([np.nan, 0.0, 0.0]),
            raw_status="optimal",
            warm_started=False,
            kind="primary",
        )

    outcome = run_verified_release_pipeline(
        data=data,
        proposed_action=proposed,
        previous_action=None,
        reference_action=None,
        policy_weight=1.0,
        reference_weight=0.0,
        primary_solve=_primary,
        config=FallbackConfig(
            enable_cold_retry=False,
            max_attempts=3,
            release_policy=ReleasePolicy(),
            fail_safe_policy=FailSafePolicy.UNIFORM_ADMISSIBLE,
        ),
    )
    assert outcome.release_decision is ReleaseDecision.ACCEPTED_FAIL_SAFE
    assert np.all(np.isfinite(outcome.candidate))
    assert abs(float(np.sum(outcome.candidate)) - 1.0) <= 1e-6


def test_fail_safe_reject_raises() -> None:
    _, data = _data()
    with pytest.raises(VerificationReleaseError):
        build_fail_safe_action(data, policy=FailSafePolicy.REJECT)


def test_pipeline_never_infinite_loops() -> None:
    _, data = _data()

    calls = {"n": 0}

    def _primary(*, warm_start: bool) -> SolveAttemptResult:
        del warm_start
        calls["n"] += 1
        return SolveAttemptResult(
            candidate=np.array([2.0, 2.0, 2.0]),
            raw_status="optimal",
            warm_started=False,
        )

    with pytest.raises(VerificationReleaseError) as excinfo:
        run_verified_release_pipeline(
            data=data,
            proposed_action=np.ones(3) / 3.0,
            previous_action=None,
            reference_action=None,
            policy_weight=1.0,
            reference_weight=0.0,
            primary_solve=_primary,
            config=FallbackConfig(
                enable_cold_retry=False,
                max_attempts=2,
                public_fallback=None,
                fail_safe_policy=FailSafePolicy.REJECT,
            ),
        )
    assert calls["n"] == 1
    assert "fallback_history" in excinfo.value.evidence


def test_projection_result_serialization_backward_compatible() -> None:
    result = ProjectionResult(
        proposed_action=np.array([0.5, 0.5]),
        corrected_action=np.array([0.5, 0.5]),
        intervened=False,
        intervention_norm=0.0,
        solver_status="optimal",
    )
    payload = result.as_dict()
    # Legacy keys always present.
    for key in (
        "proposed_action",
        "corrected_action",
        "intervened",
        "intervention_norm",
        "solver_status",
        "metadata",
    ):
        assert key in payload
    # Extended keys omitted when unset.
    assert "canonical_status" not in payload
    assert "verification" not in payload
    # Round-trip JSON.
    json.dumps(payload)


def test_metadata_cannot_overwrite_protected_evidence() -> None:
    cleaned = sanitize_metadata(
        {
            "canonical_status": "optimal",
            "user_tag": "ok",
            "verification": {"passed": True},
        }
    )
    assert cleaned == {"user_tag": "ok"}


def test_intervention_tolerance_scale_aware() -> None:
    thr_small = intervention_threshold(np.array([0.0, 0.0]), abs_tol=1e-8, rel_tol=1e-3)
    thr_large = intervention_threshold(np.array([100.0, 0.0]), abs_tol=1e-8, rel_tol=1e-3)
    assert thr_small == pytest.approx(1e-8)
    assert thr_large == pytest.approx(0.1)


def test_evaluate_residuals_rate_and_prohibited() -> None:
    from conicshield.specs.schema import RateConstraint, TurnFeasibilityConstraint

    spec = SafetySpec(
        spec_id="residuals/rate",
        action_dim=3,
        constraints=[
            SimplexConstraint(total=1.0),
            BoxConstraint(lower=[0.0, 0.0, 0.0], upper=[1.0, 1.0, 1.0]),
            TurnFeasibilityConstraint(allowed_actions=[0, 1]),
            RateConstraint(max_delta=[0.1, 0.1, 0.1]),
        ],
    )
    data = parse_safety_spec_for_shield(spec)
    prev = np.array([0.5, 0.5, 0.0])
    # Violates prohibited action 2 and rate on coord 0.
    x = np.array([0.8, 0.1, 0.1])
    report = evaluate_residuals(x, data, previous_action=prev)
    assert report.prohibited_residuals[2] > 0
    assert report.rate_residuals is not None
    assert report.rate_residuals[0] > 0
