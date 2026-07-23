"""Feasibility verification and candidate release gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from conicshield.backends.status import CanonicalSolverStatus, normalize_solver_status
from conicshield.specs.shield_qp import ShieldQPData
from conicshield.verification.active_set import active_constraints_from_residuals
from conicshield.verification.release_policy import (
    ReleaseClassification,
    ReleasePolicy,
    classify_release,
    is_accepted,
)
from conicshield.verification.residuals import (
    ResidualReport,
    evaluate_residuals,
)


@dataclass(frozen=True, slots=True)
class VerificationReport:
    """Independent verification evidence for a candidate action."""

    passed: bool
    canonical_status: CanonicalSolverStatus
    residual_report: ResidualReport
    classification: ReleaseClassification
    active_constraints: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "canonical_status": str(self.canonical_status),
            "residual_report": self.residual_report.as_dict(),
            "classification": self.classification.as_dict(),
            "active_constraints": list(self.active_constraints),
            "notes": list(self.notes),
        }


class VerificationReleaseError(RuntimeError):
    """Raised when no verified candidate may be released."""

    def __init__(
        self,
        message: str,
        *,
        report: VerificationReport | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.report = report
        self.evidence = dict(evidence or {})


def verify_candidate_before_release(
    candidate: np.ndarray,
    data: ShieldQPData,
    *,
    raw_status: Any,
    previous_action: np.ndarray | None = None,
    proposed_action: np.ndarray | None = None,
    reference_action: np.ndarray | None = None,
    policy_weight: float = 1.0,
    reference_weight: float = 0.0,
    reported_objective: float | None = None,
    policy: ReleasePolicy | None = None,
    attempt_kind: str = "primary",
    status_normalizer: Any | None = None,
) -> VerificationReport:
    """Backend-independent gate: status + residuals must both pass.

    Never treats import success, non-null ``x``, or a success-looking string alone
    as admissibility.
    """
    release_policy = policy or ReleasePolicy()
    normalizer = status_normalizer or normalize_solver_status
    canonical = normalizer(raw_status)

    residual_report = evaluate_residuals(
        candidate,
        data,
        previous_action=previous_action,
        proposed_action=proposed_action,
        reference_action=reference_action,
        policy_weight=policy_weight,
        reference_weight=reference_weight,
        reported_objective=reported_objective,
        tolerances=release_policy.tolerances,
    )

    scale = 1.0
    if proposed_action is not None:
        p = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
        if p.size:
            scale = max(1.0, float(np.linalg.norm(p)))

    classification = classify_release(
        canonical_status=canonical,
        residual_report=residual_report,
        policy=release_policy,
        residual_scale=scale,
        attempt_kind=attempt_kind,
    )
    passed = is_accepted(classification.decision)
    active: list[str] = []
    if residual_report.finite and residual_report.action_dim_ok:
        active = active_constraints_from_residuals(
            residual_report,
            data,
            previous_action=previous_action,
            candidate=np.asarray(candidate, dtype=np.float64),
            tolerances=release_policy.tolerances,
        )

    notes: list[str] = []
    if canonical is CanonicalSolverStatus.UNKNOWN:
        notes.append("unknown_status_mapped_fail_closed")
    if not residual_report.finite:
        notes.append("nonfinite_candidate")

    return VerificationReport(
        passed=passed,
        canonical_status=canonical,
        residual_report=residual_report,
        classification=classification,
        active_constraints=tuple(active),
        notes=tuple(notes),
    )


def require_verified_release(
    candidate: np.ndarray,
    data: ShieldQPData,
    **kwargs: Any,
) -> VerificationReport:
    """Verify and raise ``VerificationReleaseError`` when the candidate fails."""
    report = verify_candidate_before_release(candidate, data, **kwargs)
    if not report.passed:
        decision = report.classification.decision
        raise VerificationReleaseError(
            f"candidate rejected by release policy: {decision.value} ({', '.join(report.classification.reasons)})",
            report=report,
            evidence={"verification": report.as_dict()},
        )
    return report
