"""Construct AssuranceBundle from real experiment outputs (R4)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

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
)
from conicshield.experimental.assurance.levels import EvidenceKind, EvidenceLevel
from conicshield.experimental.provenance import detect_platform_info
from conicshield.experimental.solver_assurance.disagreement import SolverDisagreement


def infer_evidence_level(
    *,
    primal_feasible: bool,
    shadow: ShadowEvidence | None,
    sensitivity: SensitivityEvidence | None,
    replayed: bool = False,
    governed_hashes_ok: bool = False,
) -> EvidenceLevel:
    if replayed and governed_hashes_ok and sensitivity is not None and shadow is not None and primal_feasible:
        return EvidenceLevel.L4_REPLAYED_AND_GOVERNED
    if sensitivity is not None and primal_feasible:
        return EvidenceLevel.L3_SENSITIVITY_VALIDATED
    if shadow is not None and primal_feasible:
        return EvidenceLevel.L2_SHADOW_COMPARED
    if primal_feasible:
        return EvidenceLevel.L1_FEASIBILITY_VERIFIED
    return EvidenceLevel.L0_RECORDED


def _spec_digest(spec_obj: Any) -> str:
    payload = spec_obj if isinstance(spec_obj, str) else json.dumps(spec_obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _structural_fingerprint(spec_digest: str, action_dim: int, active: tuple[str, ...]) -> str:
    payload = f"{spec_digest}|{action_dim}|{','.join(active)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


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
    dual_values: tuple[float, ...] | None = None,
    dual_constraint_ids: tuple[str, ...] | None = None,
    fallback_history: tuple[FallbackAttempt, ...] = (),
    assumptions: tuple[DeclaredAssumption, ...] = (),
    limitations: tuple[str, ...] = ("research-only; not a universal safety guarantee",),
    release_decision: ReleaseDecision = ReleaseDecision.EXPERIMENTAL_ONLY,
    residual_tolerance: float = 1e-8,
    replayed: bool = False,
    extras: dict[str, Any] | None = None,
) -> AssuranceBundle:
    """Build an AssuranceBundle from research projection / observatory outputs."""

    action = np.asarray(primary.corrected_action, dtype=np.float64)
    eq = float(primary.equality_residual or 0.0)
    ineq = float(primary.inequality_residual or 0.0)
    feasible = bool(np.isfinite(eq) and np.isfinite(ineq) and eq <= residual_tolerance and ineq <= residual_tolerance)
    if primary.canonical_status in {
        CanonicalSolverStatus.INFEASIBLE,
        CanonicalSolverStatus.NUMERICAL_FAILURE,
        CanonicalSolverStatus.UNAVAILABLE,
    }:
        feasible = False

    spec_digest = _spec_digest(specification)
    active = tuple(primary.active_constraints)
    struct_fp = _structural_fingerprint(spec_digest, int(action.size), active)

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

    sens: SensitivityEvidence | None = None
    if sensitivity_mode is not None and jacobian_norm is not None:
        sens = SensitivityEvidence(
            mode=sensitivity_mode,
            jacobian_norm=float(jacobian_norm),
            agreement_metric=agreement_metric,
            forward_solution_digest=array_digest(action),
            kind=EvidenceKind.EMPIRICAL_GRADIENT_VALIDATION,
        )

    shadow_ev: ShadowEvidence | None = None
    if shadow is not None and disagreement is not None:
        problem_digest = hashlib.sha256(
            (spec_digest + array_digest(np.asarray(primary.proposed_action, dtype=np.float64))).encode("utf-8")
        ).hexdigest()[:16]
        shadow_ev = ShadowEvidence(
            primary_backend=provenance.backend_id,
            shadow_backend=shadow_backend or (shadow.provenance.backend_id if shadow.provenance else "unknown"),
            corrected_action_l2=float(disagreement.corrected_action_l2)
            if np.isfinite(disagreement.corrected_action_l2)
            else float("nan"),
            status_disagreement=bool(disagreement.status_disagreement),
            problem_digest=problem_digest,
            kind=EvidenceKind.CROSS_SOLVER_AGREEMENT,
        )

    level = infer_evidence_level(
        primal_feasible=feasible,
        shadow=shadow_ev,
        sensitivity=sens,
        replayed=replayed,
        governed_hashes_ok=bool(spec_digest and struct_fp),
    )

    verification = ResearchVerificationReport(
        equality_residual=eq,
        inequality_residual=ineq,
        primal_feasible=feasible,
        dual_available=dual_ev is not None,
        residual_tolerance=residual_tolerance,
        checks={"eq_ok": eq <= residual_tolerance, "ineq_ok": ineq <= residual_tolerance},
        notes=("constructed_from_research_outputs",),
    )

    return AssuranceBundle(
        corrected_action=action,
        specification_digest=spec_digest,
        structural_fingerprint=struct_fp,
        verification=verification,
        canonical_status=primary.canonical_status,
        release_decision=release_decision,
        primal_evidence=PrimalEvidence(
            equality_residual=eq,
            inequality_residual=ineq,
            feasible=feasible,
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
        extras=dict(extras or {}),
    )
