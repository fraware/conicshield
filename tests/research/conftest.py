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
)
from conicshield.experimental.assurance.levels import EvidenceLevel


@pytest.fixture
def sample_assurance_bundle() -> AssuranceBundle:
    action = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64)
    return AssuranceBundle(
        corrected_action=action,
        specification_digest="specdigest0001",
        structural_fingerprint="structfp0001",
        verification=ResearchVerificationReport(
            equality_residual=0.0,
            inequality_residual=0.0,
            primal_feasible=True,
            dual_available=False,
            residual_tolerance=1e-8,
            checks={"eq": True},
        ),
        canonical_status=CanonicalSolverStatus.OPTIMAL,
        release_decision=ReleaseDecision.EXPERIMENTAL_ONLY,
        primal_evidence=PrimalEvidence(
            equality_residual=0.0,
            inequality_residual=0.0,
            feasible=True,
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
    )
