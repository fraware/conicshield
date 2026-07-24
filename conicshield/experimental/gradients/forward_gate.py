"""Forward-first gate for gradient observatory (R11).

Every gradient requires a verified forward: canonical status, independent
residuals, ``problem_digest`` binding, and finite values. Unverified forward
→ gradient unavailable. Does not claim production differentiation_api.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.experimental.adapters.projection import ResearchProjectionResult
from conicshield.experimental.adapters.track1_protocols import CanonicalSolverStatus
from conicshield.experimental.assurance.builder import classify_verification_status
from conicshield.experimental.assurance.evidence import (
    forward_solution_digest,
    problem_digest,
    topology_digest,
)
from conicshield.experimental.assurance.levels import VerificationStatus
from conicshield.specs.schema import SafetySpec

DEFAULT_RESIDUAL_TOLERANCE = 1e-6


@dataclass(slots=True)
class VerifiedForward:
    """Gated forward record required before any gradient adapter runs."""

    verified: bool
    verification_status: VerificationStatus
    problem_digest: str
    forward_solution_digest: str
    topology_digest: str
    canonical_status: str
    equality_residual: float | None
    inequality_residual: float | None
    corrected_action: np.ndarray
    proposed_action: np.ndarray
    active_set: tuple[str, ...]
    residual_tolerance: float
    reason: str = ""
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "verification_status": str(self.verification_status),
            "problem_digest": self.problem_digest,
            "forward_solution_digest": self.forward_solution_digest,
            "topology_digest": self.topology_digest,
            "canonical_status": self.canonical_status,
            "equality_residual": self.equality_residual,
            "inequality_residual": self.inequality_residual,
            "corrected_action": self.corrected_action.tolist(),
            "proposed_action": self.proposed_action.tolist(),
            "active_set": list(self.active_set),
            "residual_tolerance": self.residual_tolerance,
            "reason": self.reason,
            "extras": dict(self.extras),
            "gradient_gate": "forward_first_r11",
        }


def _spec_payload(spec: SafetySpec) -> dict[str, Any]:
    if hasattr(spec, "model_dump"):
        return dict(spec.model_dump(mode="json"))
    return {"spec_id": getattr(spec, "spec_id", None), "action_dim": getattr(spec, "action_dim", None)}


def verify_forward_projection(
    *,
    primary: ResearchProjectionResult,
    spec: SafetySpec,
    previous_action: np.ndarray | None = None,
    reference_action: np.ndarray | None = None,
    policy_weight: float = 1.0,
    reference_weight: float = 0.0,
    residual_tolerance: float = DEFAULT_RESIDUAL_TOLERANCE,
    require_feasible: bool = True,
) -> VerifiedForward:
    """Classify and digest a forward projection; gate gradients on verification."""

    proposed = np.asarray(primary.proposed_action, dtype=np.float64).reshape(-1)
    corrected = np.asarray(primary.corrected_action, dtype=np.float64).reshape(-1)
    eq = primary.equality_residual
    ineq = primary.inequality_residual
    eq_f = float(eq) if eq is not None else None
    ineq_f = float(ineq) if ineq is not None else None
    action_ok = corrected.size > 0 and bool(np.all(np.isfinite(corrected)))
    proposed_ok = proposed.size > 0 and bool(np.all(np.isfinite(proposed)))
    canon = primary.canonical_status or CanonicalSolverStatus.UNKNOWN

    verification = classify_verification_status(
        equality_residual=eq_f,
        inequality_residual=ineq_f,
        residual_tolerance=float(residual_tolerance),
        canonical_status=canon,
        action_present=action_ok,
        specification_present=True,
    )

    # Topology must never encode active-set membership.
    topo = topology_digest(
        action_dim=int(max(corrected.size, proposed.size, int(getattr(spec, "action_dim", 0) or 0))),
        equality_ids=("simplex",),
        inequality_ids=("box", "rate", "turn_feasibility"),
        structural_flags={"research_forward_gate": True},
    )
    prob = problem_digest(
        topology=topo,
        specification=_spec_payload(spec),
        proposed_action=proposed,
        previous_action=None if previous_action is None else np.asarray(previous_action, dtype=np.float64),
        reference_action=None if reference_action is None else np.asarray(reference_action, dtype=np.float64),
        policy_weight=float(policy_weight),
        reference_weight=float(reference_weight),
        tolerances={"residual": float(residual_tolerance)},
    )
    forward = forward_solution_digest(
        problem=prob,
        corrected_action=corrected if action_ok else None,
        equality_residual=eq_f,
        inequality_residual=ineq_f,
        dual_values=None,
        canonical_status=str(canon),
        verification_status=str(verification),
        residual_tolerance=float(residual_tolerance),
    )

    reasons: list[str] = []
    if not proposed_ok:
        reasons.append("proposed_action_non_finite")
    if not action_ok:
        reasons.append("corrected_action_non_finite_or_empty")
    if eq_f is None or ineq_f is None:
        reasons.append("residuals_missing")
    elif not (math.isfinite(eq_f) and math.isfinite(ineq_f)):
        reasons.append("residuals_non_finite")
    if verification == VerificationStatus.UNVERIFIED:
        reasons.append("verification_status_unverified")
    if require_feasible and verification != VerificationStatus.VERIFIED_FEASIBLE:
        reasons.append(f"require_feasible_got_{verification}")

    verified = (
        proposed_ok
        and action_ok
        and eq_f is not None
        and ineq_f is not None
        and math.isfinite(eq_f)
        and math.isfinite(ineq_f)
        and verification != VerificationStatus.UNVERIFIED
        and (not require_feasible or verification == VerificationStatus.VERIFIED_FEASIBLE)
    )
    reason = "verified_forward_ok" if verified else ("unverified_forward:" + ",".join(reasons or ["unknown"]))

    return VerifiedForward(
        verified=verified,
        verification_status=verification,
        problem_digest=prob,
        forward_solution_digest=forward,
        topology_digest=topo,
        canonical_status=str(canon),
        equality_residual=eq_f,
        inequality_residual=ineq_f,
        corrected_action=corrected,
        proposed_action=proposed,
        active_set=tuple(primary.active_constraints or ()),
        residual_tolerance=float(residual_tolerance),
        reason=reason,
        extras={
            "solver_status": primary.solver_status,
            "intervened": bool(primary.intervened),
            "backend_id": None if primary.provenance is None else primary.provenance.backend_id,
        },
    )
