"""Assurance migration, sealed-digest corruption, missing-evidence gaps."""

from __future__ import annotations

from conicshield.experimental.assurance.bundle import AssuranceBundle
from conicshield.experimental.assurance.checks import (
    corrupt_sealed_digest_mismatch,
    run_machine_checks,
    strip_evidence,
)
from conicshield.experimental.assurance.evidence import SensitivityEvidence, ShadowEvidence
from conicshield.experimental.assurance.levels import EvidenceKind, EvidenceLevel
from conicshield.experimental.assurance.migration import CURRENT_SCHEMA_ID, normalize_bundle_dict


def test_v0_legacy_migration_fixture(sample_assurance_bundle: AssuranceBundle) -> None:
    legacy = {
        "schema_id": "research.assurance_bundle.v0_legacy",
        "action": sample_assurance_bundle.as_dict()["corrected_action"],
        "level": str(sample_assurance_bundle.evidence_level),
        **{
            k: v
            for k, v in sample_assurance_bundle.as_dict().items()
            if k not in {"corrected_action", "evidence_level", "schema_id"}
        },
    }
    migrated = normalize_bundle_dict(legacy)
    assert migrated["schema_id"] == CURRENT_SCHEMA_ID
    assert "corrected_action" in migrated
    assert "evidence_level" in migrated
    assert "action" not in migrated
    assert migrated["promotion_eligible"] is False
    assert migrated.get("invalidation_reason")


def test_sealed_digest_detects_corruption(sample_assurance_bundle: AssuranceBundle) -> None:
    corrupted, sealed = corrupt_sealed_digest_mismatch(sample_assurance_bundle)
    checks = run_machine_checks(corrupted, sealed_corrected_action_digest=sealed)
    assert checks["sealed_corrected_action_digest_matches"] is False
    assert checks["corrected_action_digest_matches"] is True


def test_missing_shadow_at_l2_fails_consistency(sample_assurance_bundle: AssuranceBundle) -> None:
    elevated = AssuranceBundle(
        **{
            **{k: getattr(sample_assurance_bundle, k) for k in sample_assurance_bundle.__dataclass_fields__},
            "shadow_evidence": ShadowEvidence(
                primary_backend="a",
                shadow_backend="b",
                corrected_action_l2=0.0,
                status_disagreement=False,
                problem_digest=sample_assurance_bundle.problem_digest,
                kind=EvidenceKind.CROSS_SOLVER_AGREEMENT,
            ),
            "evidence_level": EvidenceLevel.L2_SHADOW_COMPARED,
        }
    )
    stripped = strip_evidence(elevated, "shadow_evidence")
    bad = AssuranceBundle(
        **{
            **{k: getattr(stripped, k) for k in stripped.__dataclass_fields__},
            "evidence_level": EvidenceLevel.L2_SHADOW_COMPARED,
        }
    )
    checks = run_machine_checks(bad)
    assert checks["evidence_level_consistent"] is False


def test_missing_sensitivity_at_l3_fails(sample_assurance_bundle: AssuranceBundle) -> None:
    with_sens = AssuranceBundle(
        **{
            **{k: getattr(sample_assurance_bundle, k) for k in sample_assurance_bundle.__dataclass_fields__},
            "sensitivity_evidence": SensitivityEvidence(
                mode="central_finite_difference",
                jacobian_norm=1.0,
                agreement_metric=0.0,
                forward_solution_digest=sample_assurance_bundle.forward_solution_digest,
                kind=EvidenceKind.EMPIRICAL_GRADIENT_VALIDATION,
                fd_comparison_passed=True,
                synthetic=False,
            ),
            "evidence_level": EvidenceLevel.L3_SENSITIVITY_VALIDATED,
        }
    )
    stripped = strip_evidence(with_sens, "sensitivity_evidence")
    bad = AssuranceBundle(
        **{
            **{k: getattr(stripped, k) for k in stripped.__dataclass_fields__},
            "evidence_level": EvidenceLevel.L3_SENSITIVITY_VALIDATED,
        }
    )
    checks = run_machine_checks(bad)
    assert checks["evidence_level_consistent"] is False


def test_migrate_downgrades_synthetic_l3() -> None:
    raw = {
        "schema_id": "research.assurance_bundle.v0",
        "corrected_action": [0.25, 0.25, 0.25, 0.25],
        "specification_digest": "specdigest0001",
        "structural_fingerprint": "structfp0001",
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
        "sensitivity_evidence": {
            "mode": "central_finite_difference",
            "jacobian_norm": 1.0,
            "agreement_metric": 0.0,
            "forward_solution_digest": "deadbeef",
        },
        "shadow_evidence": {
            "primary_backend": "a",
            "shadow_backend": "b",
            "corrected_action_l2": 0.1,
            "status_disagreement": False,
            "problem_digest": "p",
        },
        "solver_provenance": {
            "backend_id": "cvxpy_clarabel",
            "solver_name": "CLARABEL",
            "solver_version": "0",
            "package_distribution": "cvxpy",
            "package_version": "0",
        },
        "platform_provenance": {"operating_system": "test", "python_version": "3.11"},
        "evidence_level": "L3_SENSITIVITY_VALIDATED",
    }
    migrated = normalize_bundle_dict(raw)
    assert migrated["schema_id"] == CURRENT_SCHEMA_ID
    assert migrated["evidence_level"] == "L2_SHADOW_COMPARED"
    assert migrated["release_decision"] == "experimental_invalidated"
    assert "synthetic_sensitivity_fields" in str(migrated.get("invalidation_reason"))
