"""Release policy: classify candidate evaluations into release decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from conicshield.backends.status import CanonicalSolverStatus
from conicshield.verification.residuals import ResidualReport, ResidualTolerances, residuals_within_tolerance


class ReleaseDecision(StrEnum):
    """Explicit release / rejection classification for a candidate."""

    ACCEPTED_PRIMARY = "accepted_primary"
    ACCEPTED_AFTER_RETRY = "accepted_after_retry"
    ACCEPTED_FALLBACK = "accepted_fallback"
    ACCEPTED_FAIL_SAFE = "accepted_fail_safe"
    REJECTED_STATUS = "rejected_status"
    REJECTED_NONFINITE = "rejected_nonfinite"
    REJECTED_RESIDUAL = "rejected_residual"
    REJECTED_BACKEND_ERROR = "rejected_backend_error"


# Statuses that may be released when residuals pass (policy-configurable).
_DEFAULT_ACCEPTABLE_STATUSES: frozenset[CanonicalSolverStatus] = frozenset(
    {
        CanonicalSolverStatus.OPTIMAL,
    }
)


@dataclass(frozen=True, slots=True)
class ReleasePolicy:
    """Configurable gate separating status policy from residual verification."""

    acceptable_statuses: frozenset[CanonicalSolverStatus] = field(
        default_factory=lambda: frozenset(_DEFAULT_ACCEPTABLE_STATUSES)
    )
    accept_optimal_inaccurate: bool = False
    accept_iteration_limit: bool = False
    accept_time_limit: bool = False
    tolerances: ResidualTolerances = field(default_factory=ResidualTolerances)
    intervention_abs_tol: float = 1e-8
    intervention_rel_tol: float = 1e-8

    def resolved_acceptable_statuses(self) -> frozenset[CanonicalSolverStatus]:
        allowed = set(self.acceptable_statuses)
        if self.accept_optimal_inaccurate:
            allowed.add(CanonicalSolverStatus.OPTIMAL_INACCURATE)
        if self.accept_iteration_limit:
            allowed.add(CanonicalSolverStatus.ITERATION_LIMIT)
        if self.accept_time_limit:
            allowed.add(CanonicalSolverStatus.TIME_LIMIT)
        return frozenset(allowed)


@dataclass(frozen=True, slots=True)
class ReleaseClassification:
    decision: ReleaseDecision
    reasons: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"decision": str(self.decision), "reasons": list(self.reasons)}


def intervention_threshold(
    proposed_action: Any,
    *,
    abs_tol: float = 1e-8,
    rel_tol: float = 1e-8,
) -> float:
    """Scale-aware intervention threshold: ``max(abs, rel * ||proposed||)``."""
    import numpy as np

    p = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
    scale = float(np.linalg.norm(p)) if p.size else 0.0
    return max(float(abs_tol), float(rel_tol) * scale)


def classify_release(
    *,
    canonical_status: CanonicalSolverStatus,
    residual_report: ResidualReport,
    policy: ReleasePolicy,
    residual_scale: float = 1.0,
    attempt_kind: str = "primary",
) -> ReleaseClassification:
    """Classify a candidate into an accept/reject release decision.

    ``attempt_kind`` selects the accept label among primary / retry / fallback /
    fail_safe when the candidate otherwise passes.
    """
    reasons: list[str] = []

    if canonical_status is CanonicalSolverStatus.BACKEND_ERROR:
        return ReleaseClassification(
            ReleaseDecision.REJECTED_BACKEND_ERROR,
            ("canonical_status=backend_error",),
        )

    if not residual_report.finite:
        return ReleaseClassification(
            ReleaseDecision.REJECTED_NONFINITE,
            ("candidate_nonfinite",),
        )
    if not residual_report.action_dim_ok:
        return ReleaseClassification(
            ReleaseDecision.REJECTED_RESIDUAL,
            ("action_dim_mismatch",),
        )

    acceptable = policy.resolved_acceptable_statuses()
    if canonical_status not in acceptable:
        reasons.append(f"status_not_acceptable:{canonical_status.value}")
        if canonical_status is CanonicalSolverStatus.UNKNOWN:
            reasons.append("unknown_status_never_success")
        return ReleaseClassification(ReleaseDecision.REJECTED_STATUS, tuple(reasons))

    if not residuals_within_tolerance(
        residual_report, policy.tolerances, scale=residual_scale
    ):
        reasons.append(
            "residual_violation:"
            f"eq={residual_report.max_equality_residual:.3e},"
            f"ineq={residual_report.max_inequality_residual:.3e}"
        )
        if residual_report.objective_residual is not None:
            reasons.append(
                f"objective_residual={residual_report.objective_residual:.3e}"
            )
        return ReleaseClassification(ReleaseDecision.REJECTED_RESIDUAL, tuple(reasons))

    kind = (attempt_kind or "primary").lower()
    if kind in {"retry", "cold_retry", "after_retry"}:
        decision = ReleaseDecision.ACCEPTED_AFTER_RETRY
    elif kind in {"fallback", "public_fallback"}:
        decision = ReleaseDecision.ACCEPTED_FALLBACK
    elif kind in {"fail_safe", "failsafe"}:
        decision = ReleaseDecision.ACCEPTED_FAIL_SAFE
    else:
        decision = ReleaseDecision.ACCEPTED_PRIMARY
    return ReleaseClassification(decision, ("passed_status_and_residuals",))


def is_accepted(decision: ReleaseDecision) -> bool:
    return decision.value.startswith("accepted_")
