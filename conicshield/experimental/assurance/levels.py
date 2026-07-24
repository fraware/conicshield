"""Evidence levels and taxonomy for proof-carrying projection research."""

from __future__ import annotations

from enum import StrEnum


class EvidenceLevel(StrEnum):
    """Assurance tiers (numerical evidence), not system safety proofs.

    L0 Recorded — complete normalized problem manifest, corrected action,
    provenance, evidence-bundle digest (no feasibility claim).
    L1 Independently verified — L0 + recomputed residuals + verified status
    policy + VERIFIED_FEASIBLE + no required field missing.
    L2 Shadow-compared — L1 + independent second backend on the same
    problem_digest + independently verified second result + disagreement
    metrics (copied primary-as-shadow rejected).
    L3 Sensitivity validated — L1 + live sensitivity linked to exact
    forward_solution_digest + declared mode + finite Jacobian + FD
    comparison + active-set stability + thresholds + backend provenance.
    L4 Governed/reproduced — required lower evidence + attested governed
    manifest + exact commit + immutable artifact index + ≥2 independent
    qualification envs + matching problem digests + replay + no synthetic
    host/sensitivity + clean worktree + schema migration checks.
    """

    L0_RECORDED = "L0_RECORDED"
    L1_FEASIBILITY_VERIFIED = "L1_FEASIBILITY_VERIFIED"
    L2_SHADOW_COMPARED = "L2_SHADOW_COMPARED"
    L3_SENSITIVITY_VALIDATED = "L3_SENSITIVITY_VALIDATED"
    L4_REPLAYED_AND_GOVERNED = "L4_REPLAYED_AND_GOVERNED"


class EvidenceKind(StrEnum):
    """Evidence taxonomy — keep these distinct in all records."""

    ANALYTICALLY_CHECKED = "analytically_checked"
    NUMERICAL_RESIDUALS = "numerical_residuals"
    SOLVER_CLAIMS = "solver_claims"
    CROSS_SOLVER_AGREEMENT = "cross_solver_agreement"
    EMPIRICAL_GRADIENT_VALIDATION = "empirical_gradient_validation"
    UNVERIFIED_ASSUMPTIONS = "unverified_assumptions"


class VerificationStatus(StrEnum):
    """Three-valued verification — never coerce missing evidence to feasible."""

    VERIFIED_FEASIBLE = "VERIFIED_FEASIBLE"
    VERIFIED_INFEASIBLE = "VERIFIED_INFEASIBLE"
    UNVERIFIED = "UNVERIFIED"
