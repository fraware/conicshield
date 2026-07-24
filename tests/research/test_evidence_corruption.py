"""Evidence corruption and missing-evidence tests for AssuranceBundle v1."""

from __future__ import annotations

import numpy as np

from conicshield.experimental.adapters.projection import ResearchProjectionResult
from conicshield.experimental.adapters.track1_protocols import CanonicalSolverStatus, SolverProvenance
from conicshield.experimental.assurance.bundle import AssuranceBundle
from conicshield.experimental.assurance.builder import build_assurance_bundle, infer_evidence_level
from conicshield.experimental.assurance.checks import (
    corrupt_bundle_action,
    corrupt_forward_digest_link,
    corrupt_shadow_problem_digest,
    run_machine_checks,
    strip_evidence,
)
from conicshield.experimental.assurance.evidence import (
    SensitivityEvidence,
    ShadowEvidence,
    array_digest,
    is_full_sha256_hex,
)
from conicshield.experimental.assurance.levels import EvidenceKind, EvidenceLevel, VerificationStatus
from conicshield.experimental.solver_assurance.disagreement import compare_projections


def _proj(
    action: list[float],
    *,
    backend: str = "cvxpy_clarabel",
    eq: float | None = 0.0,
    ineq: float | None = 0.0,
) -> ResearchProjectionResult:
    a = np.asarray(action, dtype=np.float64)
    return ResearchProjectionResult(
        proposed_action=a,
        corrected_action=a,
        intervened=False,
        intervention_norm=0.0,
        solver_status="optimal",
        canonical_status=CanonicalSolverStatus.OPTIMAL,
        equality_residual=eq,
        inequality_residual=ineq,
        active_constraints=["simplex"],
        provenance=SolverProvenance(
            backend_id=backend,
            solver_name="CLARABEL",
            solver_version="0",
            package_distribution="cvxpy",
            package_version="0",
        ),
    )


def test_machine_checks_pass_on_valid_bundle(sample_assurance_bundle: AssuranceBundle) -> None:
    checks = run_machine_checks(
        sample_assurance_bundle,
        expected_spec_digest=sample_assurance_bundle.specification_digest,
    )
    assert checks["specification_digest_matches"] is True
    assert checks["corrected_action_digest_matches"] is True
    assert checks["residual_report_recomputes"] is True
    assert checks["backend_provenance_complete"] is True
    assert checks["governed_bundle_hashes_verify"] is True
    assert is_full_sha256_hex(sample_assurance_bundle.corrected_action_digest())


def test_corrupted_action_digest_still_self_consistent(sample_assurance_bundle: AssuranceBundle) -> None:
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
                forward_solution_digest="0" * 64,
                kind=EvidenceKind.EMPIRICAL_GRADIENT_VALIDATION,
                fd_comparison_passed=True,
                synthetic=False,
            ),
            "evidence_level": EvidenceLevel.L3_SENSITIVITY_VALIDATED,
        }
    )
    checks = run_machine_checks(bad)
    assert checks["sensitivity_references_forward"] is False
    assert checks["evidence_level_consistent"] is False


def test_strip_shadow_evidence(sample_assurance_bundle: AssuranceBundle) -> None:
    stripped = strip_evidence(sample_assurance_bundle, "shadow_evidence")
    assert stripped.shadow_evidence is None
    checks = run_machine_checks(stripped)
    assert checks["shadow_references_problem"] is True


def test_nonempty_digest_does_not_pass_governed_verify(sample_assurance_bundle: AssuranceBundle) -> None:
    """Nonempty structural/spec digests alone must not satisfy governed-hash verify at L4."""

    bad = AssuranceBundle(
        **{
            **{k: getattr(sample_assurance_bundle, k) for k in sample_assurance_bundle.__dataclass_fields__},
            "evidence_level": EvidenceLevel.L4_REPLAYED_AND_GOVERNED,
            "shadow_evidence": ShadowEvidence(
                primary_backend="a",
                shadow_backend="b",
                corrected_action_l2=0.0,
                status_disagreement=False,
                problem_digest=sample_assurance_bundle.problem_digest,
                kind=EvidenceKind.CROSS_SOLVER_AGREEMENT,
            ),
            "sensitivity_evidence": SensitivityEvidence(
                mode="central_finite_difference",
                jacobian_norm=1.0,
                agreement_metric=0.01,
                forward_solution_digest=sample_assurance_bundle.forward_solution_digest,
                kind=EvidenceKind.EMPIRICAL_GRADIENT_VALIDATION,
                fd_comparison_passed=True,
                synthetic=False,
            ),
            "extras": {},
        }
    )
    checks = run_machine_checks(bad)
    assert checks["governed_bundle_hashes_verify"] is False


def test_missing_residuals_cap_at_l0() -> None:
    primary = _proj([0.25] * 4, eq=None, ineq=None)
    bundle = build_assurance_bundle(primary=primary, specification={"spec_id": "x", "action_dim": 4})
    assert bundle.verification_status == VerificationStatus.UNVERIFIED
    assert bundle.evidence_level == EvidenceLevel.L0_RECORDED
    assert bundle.primal_evidence.residuals_present is False


def test_manual_gradient_does_not_reach_l3() -> None:
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
        jacobian_norm=1.0,
        agreement_metric=0.01,
        sensitivity_live=False,
    )
    assert bundle.sensitivity_evidence is not None
    assert bundle.sensitivity_evidence.synthetic is True
    assert bundle.evidence_level == EvidenceLevel.L2_SHADOW_COMPARED


def test_live_sensitivity_reaches_l3() -> None:
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
        active_set_stable=True,
    )
    assert bundle.evidence_level == EvidenceLevel.L3_SENSITIVITY_VALIDATED
    assert run_machine_checks(bundle)["sensitivity_references_forward"] is True


def test_copied_shadow_does_not_reach_l2() -> None:
    primary = _proj([0.25] * 4, backend="cvxpy_clarabel")
    shadow = _proj([0.25] * 4, backend="cvxpy_clarabel")
    d = compare_projections(primary, shadow)
    bundle = build_assurance_bundle(
        primary=primary,
        specification={"spec_id": "test", "action_dim": 4},
        shadow=shadow,
        disagreement=d,
        shadow_backend="cvxpy_clarabel",
    )
    assert bundle.shadow_evidence is not None
    assert bundle.shadow_evidence.copied_from_primary is True
    assert bundle.evidence_level == EvidenceLevel.L1_FEASIBILITY_VERIFIED
    checks = run_machine_checks(bundle)
    assert checks["shadow_not_copied_primary"] is True


def test_corrupt_forward_link_predicate(sample_assurance_bundle: AssuranceBundle) -> None:
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
    corrupted = corrupt_forward_digest_link(with_sens)
    assert run_machine_checks(corrupted)["sensitivity_references_forward"] is False


def test_corrupt_shadow_problem_predicate(sample_assurance_bundle: AssuranceBundle) -> None:
    with_shadow = AssuranceBundle(
        **{
            **{k: getattr(sample_assurance_bundle, k) for k in sample_assurance_bundle.__dataclass_fields__},
            "shadow_evidence": ShadowEvidence(
                primary_backend="a",
                shadow_backend="b",
                corrected_action_l2=0.1,
                status_disagreement=False,
                problem_digest=sample_assurance_bundle.problem_digest,
                kind=EvidenceKind.CROSS_SOLVER_AGREEMENT,
            ),
            "evidence_level": EvidenceLevel.L2_SHADOW_COMPARED,
        }
    )
    corrupted = corrupt_shadow_problem_digest(with_shadow)
    assert run_machine_checks(corrupted)["shadow_references_problem"] is False


def test_infer_rejects_manual_sensitivity() -> None:
    sens = SensitivityEvidence(
        mode="central_finite_difference",
        jacobian_norm=1.0,
        agreement_metric=0.0,
        forward_solution_digest="a" * 64,
        kind=EvidenceKind.EMPIRICAL_GRADIENT_VALIDATION,
        synthetic=True,
    )
    level = infer_evidence_level(
        verification_status=VerificationStatus.VERIFIED_FEASIBLE,
        sensitivity=sens,
        forward_digest="a" * 64,
        problem_digest_value="b" * 64,
    )
    assert level == EvidenceLevel.L1_FEASIBILITY_VERIFIED
