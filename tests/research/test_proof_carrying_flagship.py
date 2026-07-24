"""R14 proof-carrying flagship candidate tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from conicshield.experimental.adapters.projection import ResearchProjectionResult
from conicshield.experimental.adapters.track1_protocols import CanonicalSolverStatus, SolverProvenance
from conicshield.experimental.assurance.evidence import SensitivityEvidence, ShadowEvidence
from conicshield.experimental.assurance.levels import EvidenceKind, EvidenceLevel, VerificationStatus
from conicshield.experimental.assurance.proof_carrying import (
    DEFAULT_LIMITATIONS,
    PUBLIC_CLAIM,
    PUBLIC_CLAIM_NONCLAIM,
    REQUIRED_SIDECAR_PROTOCOL_VERSION,
    FlagshipStageResult,
    GovernedManifest,
    ReplayEvidence,
    assemble_proof_carrying_projection,
    build_problem_manifest,
    build_verified_projection,
    docs_state_limitations,
    evaluate_flagship_promotion_gate,
    run_flagship_demo,
)
from conicshield.platform.sidecar_protocol import PROTOCOL_VERSION


def _primary() -> ResearchProjectionResult:
    a = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64)
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
            backend_id="cvxpy_clarabel",
            solver_name="CLARABEL",
            solver_version="0",
            package_distribution="cvxpy",
            package_version="0",
        ),
    )


def test_public_claim_language_fixed() -> None:
    assert "independently checkable numerical evidence" in PUBLIC_CLAIM
    assert "qualification levels" in PUBLIC_CLAIM
    assert "system-level safety proof" in PUBLIC_CLAIM_NONCLAIM
    assert "universal safety" in PUBLIC_CLAIM_NONCLAIM
    assert any("not system-level safety proof" in x or "safety proof" in x for x in DEFAULT_LIMITATIONS)
    assert docs_state_limitations()


def test_assemble_proof_carrying_projection_levels() -> None:
    primary = _primary()
    problem = build_problem_manifest(
        specification={"spec_id": "flagship", "action_dim": 4},
        proposed_action=primary.proposed_action,
        equality_ids=("simplex",),
    )
    forward = build_verified_projection(primary=primary, problem=problem)
    assert forward.verification_status == VerificationStatus.VERIFIED_FEASIBLE

    shadow = ShadowEvidence(
        primary_backend="cvxpy_clarabel",
        shadow_backend="cvxpy_scs",
        corrected_action_l2=0.01,
        status_disagreement=False,
        problem_digest=problem.problem_digest,
        kind=EvidenceKind.CROSS_SOLVER_AGREEMENT,
    )
    sens = SensitivityEvidence(
        mode="exact_research_kkt",
        jacobian_norm=1.0,
        agreement_metric=0.01,
        forward_solution_digest=forward.forward_solution_digest,
        kind=EvidenceKind.EMPIRICAL_GRADIENT_VALIDATION,
        fd_comparison_passed=True,
        synthetic=False,
    )
    proj = assemble_proof_carrying_projection(
        problem_manifest=problem,
        forward_result=forward,
        solver_provenance=primary.provenance,  # type: ignore[arg-type]
        shadow_evidence=shadow,
        sensitivity_evidence=sens,
        replay_evidence=ReplayEvidence(replayed=True, all_checks_passed=True),
        governed_manifest=GovernedManifest(
            attested=True,
            artifact_hashes={"assurance_bundle.json": "a" * 64, "provenance.json": "b" * 64},
            sealed_corrected_action_digest="c" * 64,
        ),
        multi_host_qualified=True,
        clean_worktree=True,
    )
    assert proj.evidence_level == EvidenceLevel.L4_REPLAYED_AND_GOVERNED
    assert proj.promotion_eligible is False
    assert proj.public_claim == PUBLIC_CLAIM
    d = proj.as_dict()
    assert d["schema_id"].startswith("research.proof_carrying")


def test_promotion_gate_sidecar_v2_complete_but_still_fail_closed() -> None:
    """Sidecar PROTOCOL_VERSION >= v2 with features; gate still fails without Moreau/etc."""

    assert PROTOCOL_VERSION >= REQUIRED_SIDECAR_PROTOCOL_VERSION
    gate = evaluate_flagship_promotion_gate(
        None,
        corrupted_artifact_rejected=True,
        incomplete_bundle_rejected=True,
        multi_host_includes_native_moreau=True,
    )
    assert gate.passed is False
    assert gate.production_claim is False
    assert gate.predicates["sidecar_protocol_v2_complete"] is True
    assert gate.predicates["digests_recomputed_ok"] is False
    assert any("missing_proof_carrying" in b or "moreau" in b for b in gate.blockers)


def test_promotion_gate_rejects_digest_tamper() -> None:
    primary = _primary()
    problem = build_problem_manifest(
        specification={"spec_id": "flagship", "action_dim": 4},
        proposed_action=primary.proposed_action,
        equality_ids=("simplex",),
    )
    forward = build_verified_projection(primary=primary, problem=problem)
    shadow = ShadowEvidence(
        primary_backend="cvxpy_clarabel",
        shadow_backend="cvxpy_scs",
        corrected_action_l2=0.01,
        status_disagreement=False,
        problem_digest=problem.problem_digest,
        kind=EvidenceKind.CROSS_SOLVER_AGREEMENT,
    )
    sens = SensitivityEvidence(
        mode="exact_research_kkt",
        jacobian_norm=1.0,
        agreement_metric=0.01,
        forward_solution_digest=forward.forward_solution_digest,
        kind=EvidenceKind.EMPIRICAL_GRADIENT_VALIDATION,
        fd_comparison_passed=True,
        synthetic=False,
    )
    proj = assemble_proof_carrying_projection(
        problem_manifest=problem,
        forward_result=forward,
        solver_provenance=primary.provenance,  # type: ignore[arg-type]
        shadow_evidence=shadow,
        sensitivity_evidence=sens,
        replay_evidence=ReplayEvidence(replayed=True, all_checks_passed=True),
        governed_manifest=GovernedManifest(
            attested=True,
            artifact_hashes={"assurance_bundle.json": "a" * 64, "provenance.json": "b" * 64},
            sealed_corrected_action_digest="c" * 64,
        ),
        multi_host_qualified=True,
        clean_worktree=True,
    )
    # Tamper stored problem digest while leaving other fields unchanged.
    from dataclasses import replace

    bad_manifest = replace(proj.problem_manifest, problem_digest="f" * 64)
    bad = replace(proj, problem_manifest=bad_manifest)
    gate = evaluate_flagship_promotion_gate(
        bad,
        corrupted_artifact_rejected=True,
        incomplete_bundle_rejected=True,
        multi_host_includes_native_moreau=True,
        stages=(
            FlagshipStageResult(
                stage_id="robust_cbf",
                status="ok",
                detail="ok",
                extras={"independently_verified": True},
            ),
        ),
    )
    assert gate.predicates["digests_recomputed_ok"] is False
    assert gate.passed is False
    assert any("problem_digest_recompute_mismatch" in b for b in gate.blockers)


def test_promotion_gate_rejects_incomplete_and_uncorrupted() -> None:
    gate = evaluate_flagship_promotion_gate(
        None,
        stages=(
            FlagshipStageResult(
                stage_id="robust_cbf",
                status="ok",
                detail="ok",
                extras={"independently_verified": True},
            ),
        ),
        corrupted_artifact_rejected=False,
        incomplete_bundle_rejected=False,
        multi_host_includes_native_moreau=False,
    )
    assert gate.predicates["corrupted_bundles_fail"] is False
    assert gate.predicates["incomplete_bundles_fail"] is False
    assert gate.predicates["cbf_independently_verified"] is True
    assert gate.passed is False


def test_flagship_demo_end_to_end(tmp_path: Path) -> None:
    report = run_flagship_demo(output_dir=tmp_path)
    assert report.schema_id.startswith("research.flagship_demo")
    assert report.public_claim == PUBLIC_CLAIM
    assert report.production_claim is False
    stage_ids = [s.stage_id for s in report.stages]
    for required in (
        "windows_policy_client",
        "wsl_moreau_sidecar",
        "hetero_agent_batch",
        "robust_cbf",
        "verified_release",
        "public_shadow",
        "exact_smoothed_sensitivity",
        "cross_host_replay",
        "signed_manifest",
        "corrupted_artifact_rejection",
    ):
        assert required in stage_ids

    # Core public/path stages that must not soft-pass on corruption.
    by_id = {s.stage_id: s for s in report.stages}
    assert by_id["corrupted_artifact_rejection"].status == "ok"
    assert report.corrupted_artifact_rejected is True

    # Projection assembled when public solvers available.
    if report.projection is not None:
        assert report.projection.problem_manifest.problem_digest
        assert report.projection.forward_result.forward_solution_digest
        assert "safety proof" in " ".join(report.projection.limitations).lower() or any(
            "safety" in x.lower() for x in report.projection.limitations
        )
        assert report.projection.promotion_eligible is False

    gate = report.promotion_gate
    assert gate["passed"] is False  # Moreau multi-host / live sidecar still incomplete
    assert gate["production_claim"] is False
    assert gate["predicates"]["sidecar_protocol_v2_complete"] is True
    assert gate["predicates"]["docs_state_limitations"] is True
    assert gate["predicates"]["corrupted_bundles_fail"] is True
    assert (tmp_path / "flagship_demo_report.json").is_file()
