"""Assurance bundle builder, replay, migration, corruption tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from conicshield.experimental.adapters.projection import ResearchProjectionResult
from conicshield.experimental.adapters.track1_protocols import CanonicalSolverStatus, SolverProvenance
from conicshield.experimental.assurance.builder import build_assurance_bundle, infer_evidence_level
from conicshield.experimental.assurance.checks import corrupt_bundle_action, run_machine_checks, strip_evidence
from conicshield.experimental.assurance.evidence import SensitivityEvidence, ShadowEvidence
from conicshield.experimental.assurance.levels import EvidenceKind, EvidenceLevel, VerificationStatus
from conicshield.experimental.assurance.migration import (
    CURRENT_SCHEMA_ID,
    AssuranceMigrationError,
    migration_doc,
    normalize_bundle_dict,
)
from conicshield.experimental.assurance.replay import bundle_to_json, load_bundle, replay_bundle
from conicshield.experimental.solver_assurance.disagreement import compare_projections


def _proj(action: list[float], *, backend: str = "cvxpy_clarabel") -> ResearchProjectionResult:
    a = np.asarray(action, dtype=np.float64)
    return ResearchProjectionResult(
        proposed_action=a,
        corrected_action=a,
        intervened=False,
        intervention_norm=0.0,
        solver_status="optimal",
        canonical_status=CanonicalSolverStatus.OPTIMAL,
        equality_residual=0.0,
        inequality_residual=0.0,
        active_constraints=["simplex"],
        provenance=SolverProvenance(
            backend_id=backend,
            solver_name="CLARABEL",
            solver_version="0",
            package_distribution="cvxpy",
            package_version="0",
        ),
    )


def test_build_bundle_levels_and_replay(tmp_path: Path) -> None:
    primary = _proj([0.25] * 4)
    shadow = _proj([0.3, 0.2, 0.25, 0.25], backend="cvxpy_scs")
    d = compare_projections(primary, shadow)
    bundle = build_assurance_bundle(
        primary=primary,
        specification={"spec_id": "test", "action_dim": 4},
        shadow=shadow,
        disagreement=d,
        shadow_backend="cvxpy_scs",
        sensitivity_mode="central_finite_difference",
        jacobian_norm=1.2,
        agreement_metric=0.01,
        sensitivity_live=True,
        fd_comparison_passed=True,
    )
    assert bundle.evidence_level == EvidenceLevel.L3_SENSITIVITY_VALIDATED
    assert bundle.schema_id == CURRENT_SCHEMA_ID
    path = tmp_path / "bundle.json"
    bundle_to_json(bundle, path)
    replay = replay_bundle(path, expected_spec_digest=bundle.specification_digest)
    assert replay["all_passed"] is True
    loaded = load_bundle(path)
    assert loaded.specification_digest == bundle.specification_digest


def test_missing_evidence_and_corruption(sample_assurance_bundle) -> None:
    stripped = strip_evidence(sample_assurance_bundle, "shadow_evidence")
    checks = run_machine_checks(stripped)
    assert checks["shadow_references_problem"] is True
    corrupted = corrupt_bundle_action(sample_assurance_bundle)
    assert run_machine_checks(corrupted)["corrected_action_digest_matches"] is True


def test_infer_levels() -> None:
    assert (
        infer_evidence_level(verification_status=VerificationStatus.UNVERIFIED, shadow=None, sensitivity=None)
        == EvidenceLevel.L0_RECORDED
    )
    shadow = ShadowEvidence(
        primary_backend="a",
        shadow_backend="b",
        corrected_action_l2=0.0,
        status_disagreement=False,
        problem_digest="b" * 64,
        kind=EvidenceKind.CROSS_SOLVER_AGREEMENT,
    )
    assert (
        infer_evidence_level(
            verification_status=VerificationStatus.VERIFIED_FEASIBLE,
            shadow=shadow,
            sensitivity=None,
            problem_digest_value="b" * 64,
        )
        == EvidenceLevel.L2_SHADOW_COMPARED
    )
    sens = SensitivityEvidence(
        mode="central_finite_difference",
        jacobian_norm=1.0,
        agreement_metric=0.0,
        forward_solution_digest="a" * 64,
        kind=EvidenceKind.EMPIRICAL_GRADIENT_VALIDATION,
        fd_comparison_passed=True,
        synthetic=False,
    )
    assert (
        infer_evidence_level(
            verification_status=VerificationStatus.VERIFIED_FEASIBLE,
            shadow=shadow,
            sensitivity=sens,
            problem_digest_value="b" * 64,
            forward_digest="a" * 64,
        )
        == EvidenceLevel.L3_SENSITIVITY_VALIDATED
    )


def test_migration_rules() -> None:
    assert CURRENT_SCHEMA_ID in migration_doc()
    assert "research.assurance_bundle.v1" in migration_doc()
    normalized = normalize_bundle_dict({"corrected_action": [0.0]})
    assert normalized["schema_id"] == CURRENT_SCHEMA_ID
    assert normalized["promotion_eligible"] is False
    try:
        normalize_bundle_dict({"schema_id": "research.assurance_bundle.v999"})
        raised = False
    except AssuranceMigrationError:
        raised = True
    assert raised


def test_archival_v0_loadable() -> None:
    archival = normalize_bundle_dict(
        {
            "schema_id": "research.assurance_bundle.v0",
            "corrected_action": [0.25, 0.25, 0.25, 0.25],
            "specification_digest": "abcd",
            "structural_fingerprint": "ef01",
            "verification": {
                "equality_residual": 0.0,
                "inequality_residual": 0.0,
                "primal_feasible": True,
                "dual_available": False,
                "residual_tolerance": 1e-8,
            },
            "canonical_status": "optimal",
            "release_decision": "experimental_only",
            "primal_evidence": {
                "equality_residual": 0.0,
                "inequality_residual": 0.0,
                "feasible": True,
            },
            "active_set_evidence": {"active_constraints": ["simplex"]},
            "solver_provenance": {
                "backend_id": "cvxpy_clarabel",
                "solver_name": "CLARABEL",
                "solver_version": "0",
                "package_distribution": "cvxpy",
                "package_version": "0",
            },
            "platform_provenance": {"operating_system": "test", "python_version": "3.11"},
            "evidence_level": "L1_FEASIBILITY_VERIFIED",
        },
        archival=True,
    )
    assert archival["schema_id"] == "research.assurance_bundle.v0"
    assert archival["promotion_eligible"] is False
    assert archival["invalidation_reason"]
