"""Compatibility shim: specs.admissibility re-exports the S2 verifier gate."""

from conicshield.verification.feasibility import (
    VerificationReleaseError,
    VerificationReport,
    require_verified_release,
    verify_candidate_before_release,
)

__all__ = [
    "VerificationReleaseError",
    "VerificationReport",
    "require_verified_release",
    "verify_candidate_before_release",
]
