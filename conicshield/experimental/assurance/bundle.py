"""AssuranceBundle dataclass (Track 2 R4) using research Track 1 adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.experimental.adapters.track1_protocols import (
    CanonicalSolverStatus,
    ReleaseDecision,
    ResearchVerificationReport,
    SolverProvenance,
)
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
from conicshield.experimental.assurance.levels import EvidenceLevel


@dataclass(frozen=True)
class AssuranceBundle:
    """Research assurance object. Naming: 'proof-carrying' only with explicit taxonomy."""

    corrected_action: np.ndarray
    specification_digest: str
    structural_fingerprint: str

    verification: ResearchVerificationReport
    canonical_status: CanonicalSolverStatus
    release_decision: ReleaseDecision

    primal_evidence: PrimalEvidence
    dual_evidence: DualEvidence | None
    active_set_evidence: ActiveSetEvidence

    sensitivity_evidence: SensitivityEvidence | None
    shadow_evidence: ShadowEvidence | None

    solver_provenance: SolverProvenance
    platform_provenance: PlatformProvenance
    fallback_history: tuple[FallbackAttempt, ...]

    assumptions: tuple[DeclaredAssumption, ...]
    limitations: tuple[str, ...]

    evidence_level: EvidenceLevel = EvidenceLevel.L0_RECORDED
    schema_id: str = "research.assurance_bundle.v0"
    naming_note: str = (
        "Use 'proof-carrying' only with an explicit evidence taxonomy. "
        "Evidence levels are not universal safety guarantees."
    )
    extras: dict[str, Any] = field(default_factory=dict)

    def corrected_action_digest(self) -> str:
        return array_digest(self.corrected_action)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "corrected_action": np.asarray(self.corrected_action, dtype=np.float64).tolist(),
            "corrected_action_digest": self.corrected_action_digest(),
            "specification_digest": self.specification_digest,
            "structural_fingerprint": self.structural_fingerprint,
            "verification": {
                "equality_residual": self.verification.equality_residual,
                "inequality_residual": self.verification.inequality_residual,
                "primal_feasible": self.verification.primal_feasible,
                "dual_available": self.verification.dual_available,
                "residual_tolerance": self.verification.residual_tolerance,
                "checks": dict(self.verification.checks),
                "notes": list(self.verification.notes),
            },
            "canonical_status": str(self.canonical_status),
            "release_decision": str(self.release_decision),
            "primal_evidence": {
                "equality_residual": self.primal_evidence.equality_residual,
                "inequality_residual": self.primal_evidence.inequality_residual,
                "feasible": self.primal_evidence.feasible,
                "kind": str(self.primal_evidence.kind),
            },
            "dual_evidence": None
            if self.dual_evidence is None
            else {
                "dual_values": list(self.dual_evidence.dual_values),
                "constraint_ids": list(self.dual_evidence.constraint_ids),
                "kind": str(self.dual_evidence.kind),
            },
            "active_set_evidence": {
                "active_constraints": list(self.active_set_evidence.active_constraints),
                "kind": str(self.active_set_evidence.kind),
            },
            "sensitivity_evidence": None
            if self.sensitivity_evidence is None
            else {
                "mode": self.sensitivity_evidence.mode,
                "jacobian_norm": self.sensitivity_evidence.jacobian_norm,
                "agreement_metric": self.sensitivity_evidence.agreement_metric,
                "forward_solution_digest": self.sensitivity_evidence.forward_solution_digest,
                "kind": str(self.sensitivity_evidence.kind),
            },
            "shadow_evidence": None
            if self.shadow_evidence is None
            else {
                "primary_backend": self.shadow_evidence.primary_backend,
                "shadow_backend": self.shadow_evidence.shadow_backend,
                "corrected_action_l2": self.shadow_evidence.corrected_action_l2,
                "status_disagreement": self.shadow_evidence.status_disagreement,
                "problem_digest": self.shadow_evidence.problem_digest,
                "kind": str(self.shadow_evidence.kind),
            },
            "solver_provenance": {
                "backend_id": self.solver_provenance.backend_id,
                "solver_name": self.solver_provenance.solver_name,
                "solver_version": self.solver_provenance.solver_version,
                "package_distribution": self.solver_provenance.package_distribution,
                "package_version": self.solver_provenance.package_version,
            },
            "platform_provenance": {
                "operating_system": self.platform_provenance.operating_system,
                "python_version": self.platform_provenance.python_version,
                "cpu_info": self.platform_provenance.cpu_info,
                "gpu_info": self.platform_provenance.gpu_info,
            },
            "fallback_history": [
                {"backend_id": f.backend_id, "status": f.status, "reason": f.reason} for f in self.fallback_history
            ],
            "assumptions": [
                {
                    "assumption_id": a.assumption_id,
                    "statement": a.statement,
                    "verified": a.verified,
                    "kind": str(a.kind),
                }
                for a in self.assumptions
            ],
            "limitations": list(self.limitations),
            "evidence_level": str(self.evidence_level),
            "naming_note": self.naming_note,
            "extras": dict(self.extras),
        }
