"""Shared fixtures for Track 2 research tests."""

from __future__ import annotations

import numpy as np
import pytest

from conicshield.experimental.adapters.track1_protocols import (
    CanonicalSolverStatus,
    ReleaseDecision,
    ResearchVerificationReport,
    SolverProvenance,
)
from conicshield.experimental.assurance.bundle import AssuranceBundle
from conicshield.experimental.assurance.evidence import (
    ActiveSetEvidence,
    PlatformProvenance,
    PrimalEvidence,
    evidence_bundle_digest,
    forward_solution_digest,
    problem_digest,
    sha256_hex,
    topology_digest,
)
from conicshield.experimental.assurance.levels import EvidenceLevel, VerificationStatus
from conicshield.experimental.assurance.migration import CURRENT_SCHEMA_ID


@pytest.fixture
def sample_assurance_bundle() -> AssuranceBundle:
    action = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64)
    spec_digest = sha256_hex(b"specdigest0001")
    topo = topology_digest(action_dim=4, equality_ids=(), inequality_ids=("simplex",))
    prob = problem_digest(
        topology=topo,
        specification={"spec_id": "sample", "action_dim": 4},
        proposed_action=action,
        tolerances={"residual": 1e-8},
    )
    forward = forward_solution_digest(
        problem=prob,
        corrected_action=action,
        equality_residual=0.0,
        inequality_residual=0.0,
        dual_values=None,
        canonical_status=str(CanonicalSolverStatus.OPTIMAL),
        verification_status=str(VerificationStatus.VERIFIED_FEASIBLE),
        residual_tolerance=1e-8,
    )
    bundle_digest = evidence_bundle_digest(
        forward=forward,
        shadow=None,
        sensitivity=None,
        provenance={"backend_id": "cvxpy_clarabel"},
        replay=None,
        governed_manifest=None,
    )
    return AssuranceBundle(
        corrected_action=action,
        specification_digest=spec_digest,
        structural_fingerprint=topo,
        topology_digest=topo,
        problem_digest=prob,
        forward_solution_digest=forward,
        evidence_bundle_digest=bundle_digest,
        verification=ResearchVerificationReport(
            equality_residual=0.0,
            inequality_residual=0.0,
            primal_feasible=True,
            dual_available=False,
            residual_tolerance=1e-8,
            checks={"eq": True},
        ),
        verification_status=VerificationStatus.VERIFIED_FEASIBLE,
        canonical_status=CanonicalSolverStatus.OPTIMAL,
        release_decision=ReleaseDecision.EXPERIMENTAL_ONLY,
        primal_evidence=PrimalEvidence(
            equality_residual=0.0,
            inequality_residual=0.0,
            feasible=True,
            residuals_present=True,
        ),
        dual_evidence=None,
        active_set_evidence=ActiveSetEvidence(active_constraints=("simplex",)),
        sensitivity_evidence=None,
        shadow_evidence=None,
        solver_provenance=SolverProvenance(
            backend_id="cvxpy_clarabel",
            solver_name="CLARABEL",
            solver_version="0.0.0",
            package_distribution="cvxpy",
            package_version="0.0.0",
        ),
        platform_provenance=PlatformProvenance(
            operating_system="test",
            python_version="3.11",
        ),
        fallback_history=(),
        assumptions=(),
        limitations=("research-only",),
        evidence_level=EvidenceLevel.L1_FEASIBILITY_VERIFIED,
        schema_id=CURRENT_SCHEMA_ID,
        promotion_eligible=False,
    )
