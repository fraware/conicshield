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
from conicshield.experimental.assurance.migration import normalize_bundle_dict


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
    assert migrated["schema_id"] == "research.assurance_bundle.v0"
    assert "corrected_action" in migrated
    assert "evidence_level" in migrated
    assert "action" not in migrated


def test_sealed_digest_detects_corruption(sample_assurance_bundle: AssuranceBundle) -> None:
    corrupted, sealed = corrupt_sealed_digest_mismatch(sample_assurance_bundle)
    checks = run_machine_checks(corrupted, sealed_corrected_action_digest=sealed)
    assert checks["sealed_corrected_action_digest_matches"] is False
    # Self-digest of corrupted action still matches recomputation
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
                problem_digest="p",
                kind=EvidenceKind.CROSS_SOLVER_AGREEMENT,
            ),
            "evidence_level": EvidenceLevel.L2_SHADOW_COMPARED,
        }
    )
    stripped = strip_evidence(elevated, "shadow_evidence")
    # Keep L2 while removing shadow — inconsistent
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
                forward_solution_digest=sample_assurance_bundle.corrected_action_digest(),
                kind=EvidenceKind.EMPIRICAL_GRADIENT_VALIDATION,
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
