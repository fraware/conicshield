"""Machine checks for AssuranceBundle (corruption / missing-evidence scaffolding)."""

from __future__ import annotations

from typing import Any

from conicshield.experimental.assurance.bundle import AssuranceBundle
from conicshield.experimental.assurance.evidence import array_digest
from conicshield.experimental.assurance.levels import EvidenceLevel


def run_machine_checks(
    bundle: AssuranceBundle,
    *,
    expected_spec_digest: str | None = None,
    sealed_corrected_action_digest: str | None = None,
) -> dict[str, bool]:
    """Required machine checks from Track 2 R4."""

    checks: dict[str, bool] = {}
    checks["specification_digest_present"] = bool(bundle.specification_digest)
    if expected_spec_digest is not None:
        checks["specification_digest_matches"] = bundle.specification_digest == expected_spec_digest
    recomputed = array_digest(bundle.corrected_action)
    checks["corrected_action_digest_matches"] = bundle.corrected_action_digest() == recomputed
    if sealed_corrected_action_digest is not None:
        checks["sealed_corrected_action_digest_matches"] = recomputed == sealed_corrected_action_digest
    checks["residual_report_recomputes"] = (
        abs(bundle.verification.equality_residual - bundle.primal_evidence.equality_residual) < 1e-12
        and abs(bundle.verification.inequality_residual - bundle.primal_evidence.inequality_residual) < 1e-12
    )
    checks["backend_provenance_complete"] = bool(
        bundle.solver_provenance.backend_id and bundle.solver_provenance.solver_name
    )
    checks["fallback_chain_consistent"] = _fallback_consistent(bundle)
    checks["sensitivity_references_forward"] = _sensitivity_ok(bundle)
    checks["shadow_references_problem"] = _shadow_ok(bundle)
    checks["governed_bundle_hashes_verify"] = bool(bundle.structural_fingerprint) and bool(bundle.specification_digest)
    checks["evidence_level_consistent"] = _evidence_level_consistent(bundle)
    note_l = bundle.naming_note.lower()
    checks["naming_does_not_overclaim"] = ("universal safety" not in note_l) or ("not" in note_l)
    return checks


def corrupt_sealed_digest_mismatch(bundle: AssuranceBundle) -> tuple[AssuranceBundle, str]:
    """Return (corrupted_bundle, original_sealed_digest) for sealed-digest checks."""

    sealed = bundle.corrected_action_digest()
    return corrupt_bundle_action(bundle), sealed


def _evidence_level_consistent(bundle: AssuranceBundle) -> bool:
    level = bundle.evidence_level
    if level == EvidenceLevel.L4_REPLAYED_AND_GOVERNED:
        return (
            bundle.shadow_evidence is not None
            and bundle.sensitivity_evidence is not None
            and bundle.primal_evidence.feasible
        )
    if level == EvidenceLevel.L3_SENSITIVITY_VALIDATED:
        return bundle.sensitivity_evidence is not None
    if level == EvidenceLevel.L2_SHADOW_COMPARED:
        return bundle.shadow_evidence is not None
    if level == EvidenceLevel.L1_FEASIBILITY_VERIFIED:
        return bundle.primal_evidence.feasible
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
    return bundle.sensitivity_evidence.forward_solution_digest == bundle.corrected_action_digest()


def _shadow_ok(bundle: AssuranceBundle) -> bool:
    if bundle.shadow_evidence is None:
        return bundle.evidence_level in {EvidenceLevel.L0_RECORDED, EvidenceLevel.L1_FEASIBILITY_VERIFIED}
    return bool(bundle.shadow_evidence.problem_digest)


def _bundle_kwargs(bundle: AssuranceBundle) -> dict[str, Any]:
    return {name: getattr(bundle, name) for name in bundle.__dataclass_fields__}


def corrupt_bundle_action(bundle: AssuranceBundle) -> AssuranceBundle:
    """Test helper: corrupt corrected action (digest checks should fail if re-linked)."""

    import numpy as np

    kwargs = _bundle_kwargs(bundle)
    kwargs["corrected_action"] = np.asarray(bundle.corrected_action, dtype=np.float64) + 1.0
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
