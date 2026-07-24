"""Machine checks for AssuranceBundle v1 (recomputing predicates + corruption helpers)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from conicshield.experimental.assurance.bundle import AssuranceBundle
from conicshield.experimental.assurance.evidence import (
    array_digest,
    is_full_sha256_hex,
)
from conicshield.experimental.assurance.levels import EvidenceLevel, VerificationStatus


def run_machine_checks(
    bundle: AssuranceBundle,
    *,
    expected_spec_digest: str | None = None,
    sealed_corrected_action_digest: str | None = None,
    expected_topology_digest: str | None = None,
    expected_problem_digest: str | None = None,
    expected_forward_digest: str | None = None,
) -> dict[str, bool]:
    """Required machine checks — recompute digests/residuals; fail closed on promotion."""

    checks: dict[str, bool] = {}
    checks["specification_digest_present"] = is_full_sha256_hex(bundle.specification_digest)
    if expected_spec_digest is not None:
        checks["specification_digest_matches"] = bundle.specification_digest == expected_spec_digest

    recomputed_action = array_digest(bundle.corrected_action) or ""
    checks["corrected_action_digest_matches"] = bundle.corrected_action_digest() == recomputed_action
    if sealed_corrected_action_digest is not None:
        checks["sealed_corrected_action_digest_matches"] = recomputed_action == sealed_corrected_action_digest

    checks["topology_digest_well_formed"] = is_full_sha256_hex(bundle.topology_digest)
    if expected_topology_digest is not None:
        checks["topology_digest_matches"] = bundle.topology_digest == expected_topology_digest

    checks["problem_digest_well_formed"] = is_full_sha256_hex(bundle.problem_digest)
    if expected_problem_digest is not None:
        checks["problem_digest_matches"] = bundle.problem_digest == expected_problem_digest

    checks["forward_solution_digest_well_formed"] = is_full_sha256_hex(bundle.forward_solution_digest)
    if expected_forward_digest is not None:
        checks["forward_solution_digest_matches"] = bundle.forward_solution_digest == expected_forward_digest

    checks["evidence_bundle_digest_well_formed"] = is_full_sha256_hex(bundle.evidence_bundle_digest)

    checks["residual_report_recomputes"] = _residuals_recompute(bundle)
    checks["verification_status_consistent"] = _verification_status_consistent(bundle)
    checks["backend_provenance_complete"] = bool(
        bundle.solver_provenance.backend_id and bundle.solver_provenance.solver_name
    )
    checks["fallback_chain_consistent"] = _fallback_consistent(bundle)
    checks["sensitivity_references_forward"] = _sensitivity_ok(bundle)
    checks["shadow_references_problem"] = _shadow_ok(bundle)
    checks["shadow_not_copied_primary"] = _shadow_not_copied(bundle)
    checks["governed_bundle_hashes_verify"] = _governed_hashes_verify(bundle)
    checks["evidence_level_consistent"] = _evidence_level_consistent(bundle)
    checks["promotion_fail_closed_for_deprecated"] = _promotion_fail_closed(bundle)
    note_l = bundle.naming_note.lower()
    checks["naming_does_not_overclaim"] = ("universal safety" not in note_l) or ("not" in note_l)
    return checks


def corrupt_sealed_digest_mismatch(bundle: AssuranceBundle) -> tuple[AssuranceBundle, str]:
    """Return (corrupted_bundle, original_sealed_digest) for sealed-digest checks."""

    sealed = bundle.corrected_action_digest()
    return corrupt_bundle_action(bundle), sealed


def _residuals_recompute(bundle: AssuranceBundle) -> bool:
    if not bundle.primal_evidence.residuals_present:
        return (
            bundle.verification_status == VerificationStatus.UNVERIFIED
            and bundle.evidence_level == EvidenceLevel.L0_RECORDED
        )
    eq = bundle.primal_evidence.equality_residual
    ineq = bundle.primal_evidence.inequality_residual
    if eq is None or ineq is None:
        return False
    v_eq = bundle.verification.equality_residual
    v_ineq = bundle.verification.inequality_residual
    if math.isnan(v_eq) or math.isnan(v_ineq):
        return False
    return abs(v_eq - eq) < 1e-12 and abs(v_ineq - ineq) < 1e-12


def _verification_status_consistent(bundle: AssuranceBundle) -> bool:
    status = bundle.verification_status
    if status == VerificationStatus.UNVERIFIED:
        return bundle.evidence_level == EvidenceLevel.L0_RECORDED
    if status == VerificationStatus.VERIFIED_FEASIBLE:
        return bundle.primal_evidence.feasible is True and bundle.verification.primal_feasible is True
    if status == VerificationStatus.VERIFIED_INFEASIBLE:
        return bundle.primal_evidence.feasible is False
    return False


def _evidence_level_consistent(bundle: AssuranceBundle) -> bool:
    level = bundle.evidence_level
    if level == EvidenceLevel.L4_REPLAYED_AND_GOVERNED:
        return (
            bundle.shadow_evidence is not None
            and bundle.shadow_evidence.is_independent()
            and bundle.sensitivity_evidence is not None
            and bundle.sensitivity_evidence.is_live_validated()
            and bundle.verification_status == VerificationStatus.VERIFIED_FEASIBLE
            and _governed_hashes_verify(bundle)
        )
    if level == EvidenceLevel.L3_SENSITIVITY_VALIDATED:
        return (
            bundle.sensitivity_evidence is not None
            and bundle.sensitivity_evidence.is_live_validated()
            and bundle.sensitivity_evidence.forward_solution_digest == bundle.forward_solution_digest
            and bundle.verification_status == VerificationStatus.VERIFIED_FEASIBLE
        )
    if level == EvidenceLevel.L2_SHADOW_COMPARED:
        return (
            bundle.shadow_evidence is not None
            and bundle.shadow_evidence.is_independent()
            and bundle.shadow_evidence.problem_digest == bundle.problem_digest
            and bundle.verification_status == VerificationStatus.VERIFIED_FEASIBLE
        )
    if level == EvidenceLevel.L1_FEASIBILITY_VERIFIED:
        return bundle.verification_status == VerificationStatus.VERIFIED_FEASIBLE
    return True


def _fallback_consistent(bundle: AssuranceBundle) -> bool:
    seen: set[str] = set()
    for attempt in bundle.fallback_history:
        key = f"{attempt.backend_id}:{attempt.status}:{attempt.reason}"
        if key in seen:
            return False
        seen.add(key)
    return True


def _sensitivity_ok(bundle: AssuranceBundle) -> bool:
    if bundle.sensitivity_evidence is None:
        return bundle.evidence_level in {
            EvidenceLevel.L0_RECORDED,
            EvidenceLevel.L1_FEASIBILITY_VERIFIED,
            EvidenceLevel.L2_SHADOW_COMPARED,
        }
    sens = bundle.sensitivity_evidence
    linked = sens.forward_solution_digest == bundle.forward_solution_digest
    if bundle.evidence_level in {
        EvidenceLevel.L3_SENSITIVITY_VALIDATED,
        EvidenceLevel.L4_REPLAYED_AND_GOVERNED,
    }:
        return linked and sens.is_live_validated()
    return linked


def _shadow_ok(bundle: AssuranceBundle) -> bool:
    """Shadow must bind the bundle problem_digest — nonempty string alone is insufficient."""

    if bundle.shadow_evidence is None:
        return bundle.evidence_level in {EvidenceLevel.L0_RECORDED, EvidenceLevel.L1_FEASIBILITY_VERIFIED}
    shadow = bundle.shadow_evidence
    if not is_full_sha256_hex(shadow.problem_digest):
        return False
    if not bundle.problem_digest or shadow.problem_digest != bundle.problem_digest:
        return False
    return True


def _shadow_not_copied(bundle: AssuranceBundle) -> bool:
    """Copied primary-as-shadow is allowed only when level does not claim L2+."""

    if bundle.shadow_evidence is None:
        return True
    if bundle.shadow_evidence.copied_from_primary or not bundle.shadow_evidence.is_independent():
        return bundle.evidence_level in {
            EvidenceLevel.L0_RECORDED,
            EvidenceLevel.L1_FEASIBILITY_VERIFIED,
        }
    return True


def _governed_hashes_verify(bundle: AssuranceBundle) -> bool:
    """Verify governed artifact hashes when a manifest is present; never pass on nonempty digests alone."""

    manifest = bundle.extras.get("governed_manifest")
    if not isinstance(manifest, dict) or not manifest:
        # No governed claim — check passes only when level does not require governance.
        return bundle.evidence_level != EvidenceLevel.L4_REPLAYED_AND_GOVERNED

    artifact_hashes = manifest.get("artifact_hashes")
    if not isinstance(artifact_hashes, dict) or not artifact_hashes:
        return False
    attested = bool(manifest.get("attested"))
    if not attested:
        return False
    for key, digest in artifact_hashes.items():
        if not is_full_sha256_hex(str(digest)):
            return False
        expected = (manifest.get("expected_hashes") or {}).get(key)
        if expected is not None and str(expected) != str(digest):
            return False
    sealed = manifest.get("sealed_corrected_action_digest")
    if sealed is not None and sealed != bundle.corrected_action_digest():
        return False
    return True


def _promotion_fail_closed(bundle: AssuranceBundle) -> bool:
    """Deprecated/invalidated schemas and watermarks must not be promotion-eligible."""

    from conicshield.experimental.assurance.migration import CURRENT_SCHEMA_ID, DEPRECATED_SCHEMA_IDS

    if bundle.promotion_eligible:
        if bundle.schema_id in DEPRECATED_SCHEMA_IDS:
            return False
        if bundle.invalidation_reason:
            return False
        if bundle.schema_id != CURRENT_SCHEMA_ID:
            return False
        return False  # research default: never promotion-eligible in this phase
    return True


def _bundle_kwargs(bundle: AssuranceBundle) -> dict[str, Any]:
    return {name: getattr(bundle, name) for name in bundle.__dataclass_fields__}


def corrupt_bundle_action(bundle: AssuranceBundle) -> AssuranceBundle:
    """Test helper: corrupt corrected action (digest checks should fail if re-linked)."""

    kwargs = _bundle_kwargs(bundle)
    kwargs["corrected_action"] = np.asarray(bundle.corrected_action, dtype=np.float64) + 1.0
    return AssuranceBundle(**kwargs)


def corrupt_forward_digest_link(bundle: AssuranceBundle) -> AssuranceBundle:
    """Break sensitivity↔forward linkage."""

    if bundle.sensitivity_evidence is None:
        raise ValueError("bundle has no sensitivity_evidence")
    kwargs = _bundle_kwargs(bundle)
    sens = bundle.sensitivity_evidence
    from conicshield.experimental.assurance.evidence import SensitivityEvidence

    kwargs["sensitivity_evidence"] = SensitivityEvidence(
        mode=sens.mode,
        jacobian_norm=sens.jacobian_norm,
        agreement_metric=sens.agreement_metric,
        forward_solution_digest="0" * 64,
        kind=sens.kind,
        finite_jacobian=sens.finite_jacobian,
        fd_comparison_passed=sens.fd_comparison_passed,
        active_set_stable=sens.active_set_stable,
        synthetic=sens.synthetic,
        backend_id=sens.backend_id,
        backend_version=sens.backend_version,
    )
    return AssuranceBundle(**kwargs)


def corrupt_shadow_problem_digest(bundle: AssuranceBundle) -> AssuranceBundle:
    """Break shadow↔problem digest equality."""

    if bundle.shadow_evidence is None:
        raise ValueError("bundle has no shadow_evidence")
    kwargs = _bundle_kwargs(bundle)
    sh = bundle.shadow_evidence
    from conicshield.experimental.assurance.evidence import ShadowEvidence

    kwargs["shadow_evidence"] = ShadowEvidence(
        primary_backend=sh.primary_backend,
        shadow_backend=sh.shadow_backend,
        corrected_action_l2=sh.corrected_action_l2,
        status_disagreement=sh.status_disagreement,
        problem_digest="f" * 64,
        kind=sh.kind,
        independently_verified=sh.independently_verified,
        copied_from_primary=sh.copied_from_primary,
        shadow_verification_status=sh.shadow_verification_status,
    )
    return AssuranceBundle(**kwargs)


def strip_evidence(bundle: AssuranceBundle, field_name: str) -> AssuranceBundle:
    """Test helper: remove an optional evidence field for missing-evidence tests."""

    if field_name == "primal_evidence":
        raise ValueError("primal_evidence is required; use a partial dict for schema tests")
    kwargs = _bundle_kwargs(bundle)
    if field_name not in kwargs:
        raise KeyError(field_name)
    kwargs[field_name] = None
    return AssuranceBundle(**kwargs)


def checks_as_dict(bundle: AssuranceBundle) -> dict[str, Any]:
    return {"checks": run_machine_checks(bundle), "evidence_level": str(bundle.evidence_level)}
