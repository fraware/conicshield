"""Independent verification, release policy, and fallback for solver candidates."""

from conicshield.verification.active_set import active_constraints_from_residuals
from conicshield.verification.fallback import (
    FallbackAttempt,
    FallbackConfig,
    FallbackOutcome,
    SolveAttemptResult,
    build_fail_safe_action,
    run_verified_release_pipeline,
)
from conicshield.verification.feasibility import (
    VerificationReleaseError,
    VerificationReport,
    require_verified_release,
    verify_candidate_before_release,
)
from conicshield.verification.provenance import SolverProvenance
from conicshield.verification.release_policy import (
    ReleaseClassification,
    ReleaseDecision,
    ReleasePolicy,
    classify_release,
    intervention_threshold,
    is_accepted,
)
from conicshield.verification.residuals import (
    ResidualReport,
    ResidualTolerances,
    evaluate_residuals,
    residuals_within_tolerance,
)

__all__ = [
    "FallbackAttempt",
    "FallbackConfig",
    "FallbackOutcome",
    "ReleaseClassification",
    "ReleaseDecision",
    "ReleasePolicy",
    "ResidualReport",
    "ResidualTolerances",
    "SolveAttemptResult",
    "SolverProvenance",
    "VerificationReleaseError",
    "VerificationReport",
    "active_constraints_from_residuals",
    "build_fail_safe_action",
    "classify_release",
    "evaluate_residuals",
    "intervention_threshold",
    "is_accepted",
    "require_verified_release",
    "residuals_within_tolerance",
    "run_verified_release_pipeline",
    "verify_candidate_before_release",
]
