"""Construct AssuranceBundle from real experiment outputs (R9 / assurance_bundle v1)."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import numpy as np

from conicshield.experimental.adapters.projection import ResearchProjectionResult
from conicshield.experimental.adapters.track1_protocols import (
    CanonicalSolverStatus,
    ReleaseDecision,
    ResearchVerificationReport,
    SolverProvenance,
)
from conicshield.experimental.assurance.bundle import AssuranceBundle
from conicshield.experimental.assurance.evidence import (
    ActiveSetEvidence,
    DeclaredAssumption,
    DualEvidence,
    FallbackAttempt,
    PlatformProvenance,
    PrimalEvidence,
    SensitivityEvidence,
    ShadowEvidence,
    array_digest,
    evidence_bundle_digest,
    forward_solution_digest,
    problem_digest,
    topology_digest,
)
from conicshield.experimental.assurance.levels import EvidenceKind, EvidenceLevel, VerificationStatus
from conicshield.experimental.assurance.migration import CURRENT_SCHEMA_ID
from conicshield.experimental.provenance import detect_platform_info

if TYPE_CHECKING:
    from conicshield.experimental.solver_assurance.disagreement import SolverDisagreement


def classify_verification_status(
    *,
    equality_residual: float | None,
    inequality_residual: float | None,
    residual_tolerance: float,
    canonical_status: CanonicalSolverStatus,
    action_present: bool,
    specification_present: bool,
) -> VerificationStatus:
    """Three-valued verification. Missing required evidence → UNVERIFIED."""

    if not action_present or not specification_present:
        return VerificationStatus.UNVERIFIED
    if equality_residual is None or inequality_residual is None:
        return VerificationStatus.UNVERIFIED
    if not math.isfinite(equality_residual) or not math.isfinite(inequality_residual):
        return VerificationStatus.UNVERIFIED

    if canonical_status in {
        CanonicalSolverStatus.INFEASIBLE,
        CanonicalSolverStatus.NUMERICAL_FAILURE,
        CanonicalSolverStatus.UNAVAILABLE,
    }:
        return VerificationStatus.VERIFIED_INFEASIBLE

    if equality_residual <= residual_tolerance and inequality_residual <= residual_tolerance:
        return VerificationStatus.VERIFIED_FEASIBLE
    return VerificationStatus.VERIFIED_INFEASIBLE


def sensitivity_qualifies_for_l3(sensitivity: SensitivityEvidence | None, *, forward_digest: str) -> bool:
    if sensitivity is None:
        return False
    if not sensitivity.is_live_validated():
        return False
    return sensitivity.forward_solution_digest == forward_digest


def shadow_qualifies_for_l2(shadow: ShadowEvidence | None, *, expected_problem_digest: str) -> bool:
    if shadow is None or not shadow.is_independent():
        return False
    return shadow.problem_digest == expected_problem_digest


def infer_evidence_level(
    *,
    verification_status: VerificationStatus,
    shadow: ShadowEvidence | None = None,
    sensitivity: SensitivityEvidence | None = None,
    problem_digest_value: str | None = None,
    forward_digest: str | None = None,
    replayed: bool = False,
    governed_hashes_ok: bool = False,
    governed_manifest_attested: bool = False,
    multi_host_qualified: bool = False,
    clean_worktree: bool = False,
    no_synthetic_host: bool = True,
    no_synthetic_sensitivity: bool = True,
    # Legacy kwargs kept for call-site compatibility (ignored for level gates).
    primal_feasible: bool | None = None,
) -> EvidenceLevel:
    """Infer highest honest evidence level under v1 predicates.

    ``primal_feasible`` is accepted only for backward-compatible call sites;
    level gating uses ``verification_status`` exclusively.
    """

    _ = primal_feasible  # intentionally unused — three-valued status is authoritative

    if verification_status != VerificationStatus.VERIFIED_FEASIBLE:
        return EvidenceLevel.L0_RECORDED

    fwd = forward_digest or ""
    prob = problem_digest_value or ""
    sens_ok = sensitivity_qualifies_for_l3(sensitivity, forward_digest=fwd)
    shadow_ok = shadow_qualifies_for_l2(shadow, expected_problem_digest=prob)

    l4 = (
        replayed
        and governed_hashes_ok
        and governed_manifest_attested
        and multi_host_qualified
        and clean_worktree
        and no_synthetic_host
        and no_synthetic_sensitivity
        and sens_ok
        and shadow_ok
    )
    if l4:
        return EvidenceLevel.L4_REPLAYED_AND_GOVERNED
    if sens_ok:
        return EvidenceLevel.L3_SENSITIVITY_VALIDATED
    if shadow_ok:
        return EvidenceLevel.L2_SHADOW_COMPARED
    return EvidenceLevel.L1_FEASIBILITY_VERIFIED


def _spec_present(specification: Any) -> bool:
    if specification is None:
        return False
    if isinstance(specification, str) and not specification.strip():
        return False
    return True


def build_assurance_bundle(
    *,
    primary: ResearchProjectionResult,
    specification: Any,
    shadow: ResearchProjectionResult | None = None,
    disagreement: SolverDisagreement | None = None,
    shadow_backend: str | None = None,
    sensitivity_mode: str | None = None,
    jacobian_norm: float | None = None,
    agreement_metric: float | None = None,
    sensitivity_live: bool = False,
    fd_comparison_passed: bool | None = None,
    active_set_stable: bool | None = None,
    sensitivity_synthetic: bool | None = None,
    dual_values: tuple[float, ...] | None = None,
    dual_constraint_ids: tuple[str, ...] | None = None,
    fallback_history: tuple[FallbackAttempt, ...] = (),
    assumptions: tuple[DeclaredAssumption, ...] = (),
    limitations: tuple[str, ...] = ("research-only; not a universal safety guarantee",),
    release_decision: ReleaseDecision = ReleaseDecision.EXPERIMENTAL_ONLY,
    residual_tolerance: float = 1e-8,
    replayed: bool = False,
    governed_hashes_ok: bool = False,
    governed_manifest: dict[str, Any] | None = None,
    multi_host_qualified: bool = False,
    clean_worktree: bool = False,
    equality_ids: tuple[str, ...] = (),
    inequality_ids: tuple[str, ...] = (),
    structural_flags: dict[str, Any] | None = None,
    previous_action: np.ndarray | None = None,
    reference_action: np.ndarray | None = None,
    policy_weight: float | None = None,
    reference_weight: float | None = None,
    bounds: Any = None,
    extras: dict[str, Any] | None = None,
) -> AssuranceBundle:
    """Build an AssuranceBundle v1 from research projection / observatory outputs.

    Manual ``jacobian_norm`` injection without ``sensitivity_live=True`` and a
    passing FD comparison does **not** qualify for L3.
    Missing residuals are never coerced to zero — status becomes UNVERIFIED (≤ L0).
    """

    action = np.asarray(primary.corrected_action, dtype=np.float64)
    eq_raw = primary.equality_residual
    ineq_raw = primary.inequality_residual
    residuals_present = eq_raw is not None and ineq_raw is not None
    eq: float | None = float(eq_raw) if eq_raw is not None else None
    ineq: float | None = float(ineq_raw) if ineq_raw is not None else None

    verification_status = classify_verification_status(
        equality_residual=eq,
        inequality_residual=ineq,
        residual_tolerance=residual_tolerance,
        canonical_status=primary.canonical_status,
        action_present=action.size > 0 and np.all(np.isfinite(action)),
        specification_present=_spec_present(specification),
    )
    feasible = verification_status == VerificationStatus.VERIFIED_FEASIBLE

    topo = topology_digest(
        action_dim=int(action.size),
        equality_ids=equality_ids,
        inequality_ids=inequality_ids,
        structural_flags=structural_flags,
    )
    prob = problem_digest(
        topology=topo,
        specification=specification,
        proposed_action=np.asarray(primary.proposed_action, dtype=np.float64),
        previous_action=previous_action,
        reference_action=reference_action,
        policy_weight=policy_weight,
        reference_weight=reference_weight,
        bounds=bounds,
        tolerances={"residual": residual_tolerance},
    )

    plat = detect_platform_info()
    provenance = primary.provenance or SolverProvenance(
        backend_id="unknown",
        solver_name="unknown",
        solver_version=None,
        package_distribution=None,
        package_version=None,
    )

    dual_ev: DualEvidence | None = None
    if dual_values is not None:
        dual_ev = DualEvidence(
            dual_values=tuple(float(x) for x in dual_values),
            constraint_ids=dual_constraint_ids or tuple(f"c{i}" for i in range(len(dual_values))),
            kind=EvidenceKind.SOLVER_CLAIMS,
        )

    forward = forward_solution_digest(
        problem=prob,
        corrected_action=action,
        equality_residual=eq,
        inequality_residual=ineq,
        dual_values=None if dual_ev is None else dual_ev.dual_values,
        canonical_status=str(primary.canonical_status),
        verification_status=str(verification_status),
        residual_tolerance=residual_tolerance,
    )

    # Sensitivity: mark synthetic unless explicitly live-validated.
    synthetic_flag = True if sensitivity_synthetic is None else bool(sensitivity_synthetic)
    if sensitivity_live:
        synthetic_flag = False if sensitivity_synthetic is None else bool(sensitivity_synthetic)

    sens: SensitivityEvidence | None = None
    if sensitivity_mode is not None and jacobian_norm is not None:
        finite_j = math.isfinite(float(jacobian_norm))
        fd_ok = fd_comparison_passed
        if sensitivity_live and fd_ok is None and agreement_metric is not None:
            fd_ok = True
        sens = SensitivityEvidence(
            mode=sensitivity_mode,
            jacobian_norm=float(jacobian_norm),
            agreement_metric=agreement_metric,
            forward_solution_digest=forward,
            kind=EvidenceKind.EMPIRICAL_GRADIENT_VALIDATION,
            finite_jacobian=finite_j,
            fd_comparison_passed=fd_ok,
            active_set_stable=active_set_stable,
            synthetic=synthetic_flag or not sensitivity_live,
            backend_id=provenance.backend_id,
            backend_version=provenance.solver_version,
        )

    shadow_ev: ShadowEvidence | None = None
    if shadow is not None and disagreement is not None:
        shadow_backend_id = shadow_backend or (
            shadow.provenance.backend_id if shadow.provenance else "unknown"
        )
        primary_arr = np.asarray(primary.corrected_action, dtype=np.float64)
        shadow_arr = np.asarray(shadow.corrected_action, dtype=np.float64)
        copied = bool(
            shadow_backend_id == provenance.backend_id
            and primary_arr.shape == shadow_arr.shape
            and np.allclose(primary_arr, shadow_arr)
            and str(primary.canonical_status) == str(shadow.canonical_status)
        )
        shadow_status = classify_verification_status(
            equality_residual=None if shadow.equality_residual is None else float(shadow.equality_residual),
            inequality_residual=(
                None if shadow.inequality_residual is None else float(shadow.inequality_residual)
            ),
            residual_tolerance=residual_tolerance,
            canonical_status=shadow.canonical_status,
            action_present=shadow_arr.size > 0 and np.all(np.isfinite(shadow_arr)),
            specification_present=_spec_present(specification),
        )
        shadow_ev = ShadowEvidence(
            primary_backend=provenance.backend_id,
            shadow_backend=shadow_backend_id,
            corrected_action_l2=float(disagreement.corrected_action_l2)
            if np.isfinite(disagreement.corrected_action_l2)
            else float("nan"),
            status_disagreement=bool(disagreement.status_disagreement),
            problem_digest=prob,
            kind=EvidenceKind.CROSS_SOLVER_AGREEMENT,
            independently_verified=shadow_status != VerificationStatus.UNVERIFIED and not copied,
            copied_from_primary=copied,
            shadow_verification_status=str(shadow_status),
        )

    no_synth_sens = sens is None or not sens.synthetic
    level = infer_evidence_level(
        verification_status=verification_status,
        shadow=shadow_ev,
        sensitivity=sens,
        problem_digest_value=prob,
        forward_digest=forward,
        replayed=replayed,
        governed_hashes_ok=governed_hashes_ok and governed_manifest is not None,
        governed_manifest_attested=governed_manifest is not None and governed_hashes_ok,
        multi_host_qualified=multi_host_qualified,
        clean_worktree=clean_worktree,
        no_synthetic_sensitivity=no_synth_sens,
    )

    active = tuple(primary.active_constraints)
    # structural_fingerprint is topology-linked and must never include active-set membership
    struct_fp = topology_digest(
        action_dim=int(action.size),
        equality_ids=equality_ids,
        inequality_ids=inequality_ids,
        structural_flags={"legacy_structural_fingerprint": True, **(structural_flags or {})},
    )

    verification = ResearchVerificationReport(
        equality_residual=float("nan") if eq is None else eq,
        inequality_residual=float("nan") if ineq is None else ineq,
        primal_feasible=feasible,
        dual_available=dual_ev is not None,
        residual_tolerance=residual_tolerance,
        checks={
            "eq_ok": bool(eq is not None and eq <= residual_tolerance),
            "ineq_ok": bool(ineq is not None and ineq <= residual_tolerance),
            "residuals_present": residuals_present,
        },
        notes=("constructed_from_research_outputs", f"verification_status={verification_status}"),
    )

    sens_dict = None
    if sens is not None:
        sens_dict = {
            "mode": sens.mode,
            "jacobian_norm": sens.jacobian_norm,
            "agreement_metric": sens.agreement_metric,
            "forward_solution_digest": sens.forward_solution_digest,
            "synthetic": sens.synthetic,
            "fd_comparison_passed": sens.fd_comparison_passed,
        }
    shadow_dict = None
    if shadow_ev is not None:
        shadow_dict = {
            "primary_backend": shadow_ev.primary_backend,
            "shadow_backend": shadow_ev.shadow_backend,
            "problem_digest": shadow_ev.problem_digest,
            "copied_from_primary": shadow_ev.copied_from_primary,
        }
    provenance_dict = {
        "solver": provenance.as_dict(),
        "platform": {
            "operating_system": str(plat["operating_system"]),
            "python_version": str(plat["python_version"]),
        },
    }
    bundle_digest = evidence_bundle_digest(
        forward=forward,
        shadow=shadow_dict,
        sensitivity=sens_dict,
        provenance=provenance_dict,
        replay={"replayed": replayed},
        governed_manifest=governed_manifest,
    )

    extra = dict(extras or {})
    extra.setdefault("promotion_eligible", False)
    if sens is not None and sens.synthetic:
        extra["sensitivity_fields_synthetic"] = True

    return AssuranceBundle(
        corrected_action=action,
        specification_digest=sha256_of_spec(specification),
        structural_fingerprint=struct_fp,
        topology_digest=topo,
        problem_digest=prob,
        forward_solution_digest=forward,
        evidence_bundle_digest=bundle_digest,
        verification=verification,
        verification_status=verification_status,
        canonical_status=primary.canonical_status,
        release_decision=release_decision,
        primal_evidence=PrimalEvidence(
            equality_residual=eq,
            inequality_residual=ineq,
            feasible=feasible,
            residuals_present=residuals_present,
            kind=EvidenceKind.NUMERICAL_RESIDUALS,
        ),
        dual_evidence=dual_ev,
        active_set_evidence=ActiveSetEvidence(active_constraints=active, kind=EvidenceKind.SOLVER_CLAIMS),
        sensitivity_evidence=sens,
        shadow_evidence=shadow_ev,
        solver_provenance=provenance,
        platform_provenance=PlatformProvenance(
            operating_system=str(plat["operating_system"]),
            python_version=str(plat["python_version"]),
            cpu_info=plat["cpu_info"],
            gpu_info=plat["gpu_info"],
        ),
        fallback_history=fallback_history,
        assumptions=assumptions
        or (
            DeclaredAssumption(
                assumption_id="research_adapter",
                statement="Bundle constructed via research adapters; not a production governed claim.",
                verified=False,
            ),
        ),
        limitations=limitations,
        evidence_level=level,
        schema_id=CURRENT_SCHEMA_ID,
        promotion_eligible=False,
        extras=extra,
    )


def sha256_of_spec(specification: Any) -> str:
    from conicshield.experimental.assurance.evidence import canonical_json_bytes, sha256_hex

    return sha256_hex(canonical_json_bytes(specification))
