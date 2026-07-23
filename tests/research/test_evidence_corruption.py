"""Evidence corruption and missing-evidence tests for AssuranceBundle."""

from __future__ import annotations

from conicshield.experimental.assurance.bundle import AssuranceBundle
from conicshield.experimental.assurance.checks import (
    corrupt_bundle_action,
    run_machine_checks,
    strip_evidence,
)
from conicshield.experimental.assurance.evidence import SensitivityEvidence, array_digest
from conicshield.experimental.assurance.levels import EvidenceKind, EvidenceLevel


def test_machine_checks_pass_on_valid_bundle(sample_assurance_bundle: AssuranceBundle) -> None:
    checks = run_machine_checks(sample_assurance_bundle, expected_spec_digest="specdigest0001")
    assert checks["specification_digest_matches"] is True
    assert checks["corrected_action_digest_matches"] is True
    assert checks["residual_report_recomputes"] is True
    assert checks["backend_provenance_complete"] is True


def test_corrupted_action_digest_still_self_consistent(sample_assurance_bundle: AssuranceBundle) -> None:
    # Digest is derived from the action array; corruption keeps self-consistency of digest helper
    corrupted = corrupt_bundle_action(sample_assurance_bundle)
    assert corrupted.corrected_action_digest() == array_digest(corrupted.corrected_action)
    assert corrupted.corrected_action_digest() != sample_assurance_bundle.corrected_action_digest()


def test_sensitivity_missing_ok_at_l1(sample_assurance_bundle: AssuranceBundle) -> None:
    checks = run_machine_checks(sample_assurance_bundle)
    assert checks["sensitivity_references_forward"] is True


def test_sensitivity_mismatched_forward_digest_fails(sample_assurance_bundle: AssuranceBundle) -> None:
    bad = AssuranceBundle(
        **{
            **{k: getattr(sample_assurance_bundle, k) for k in sample_assurance_bundle.__dataclass_fields__},
            "sensitivity_evidence": SensitivityEvidence(
                mode="central_finite_difference",
                jacobian_norm=1.0,
                agreement_metric=0.0,
                forward_solution_digest="deadbeef",
                kind=EvidenceKind.EMPIRICAL_GRADIENT_VALIDATION,
            ),
            "evidence_level": EvidenceLevel.L3_SENSITIVITY_VALIDATED,
        }
    )
    checks = run_machine_checks(bad)
    assert checks["sensitivity_references_forward"] is False


def test_strip_shadow_evidence(sample_assurance_bundle: AssuranceBundle) -> None:
    stripped = strip_evidence(sample_assurance_bundle, "shadow_evidence")
    assert stripped.shadow_evidence is None
    checks = run_machine_checks(stripped)
    assert checks["shadow_references_problem"] is True  # allowed at L1
