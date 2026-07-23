"""Evidence levels and taxonomy for proof-carrying projection research."""

from __future__ import annotations

from enum import StrEnum


class EvidenceLevel(StrEnum):
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
