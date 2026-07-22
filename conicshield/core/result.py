from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.backends.status import CanonicalSolverStatus
from conicshield.verification.fallback import FallbackAttempt
from conicshield.verification.feasibility import VerificationReport
from conicshield.verification.provenance import SolverProvenance
from conicshield.verification.release_policy import ReleaseDecision

# Metadata keys that callers may not overwrite — evidence lives on dedicated fields.
PROTECTED_EVIDENCE_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "canonical_status",
        "release_decision",
        "verification",
        "solver_provenance",
        "fallback_history",
        "equality_residual",
        "inequality_residual",
        "active_constraints",
        "solver_status",
    }
)


def sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Return a copy of ``metadata`` with protected evidence keys removed."""
    if not metadata:
        return {}
    return {k: v for k, v in metadata.items() if k not in PROTECTED_EVIDENCE_METADATA_KEYS}


@dataclass(slots=True)
class ProjectionResult:
    proposed_action: np.ndarray
    corrected_action: np.ndarray
    intervened: bool
    intervention_norm: float
    solver_status: str
    objective_value: float | None = None
    active_constraints: list[str] = field(default_factory=list)
    warm_started: bool = False

    solve_time_sec: float | None = None
    setup_time_sec: float | None = None
    iterations: int | None = None
    construction_time_sec: float | None = None
    device: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    # S2 evidence extensions (optional for backward-compatible construction).
    canonical_status: CanonicalSolverStatus | None = None
    release_decision: ReleaseDecision | None = None
    verification: VerificationReport | None = None
    solver_provenance: SolverProvenance | None = None
    fallback_history: tuple[FallbackAttempt, ...] = ()

    def __post_init__(self) -> None:
        self.metadata = sanitize_metadata(self.metadata)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "proposed_action": self.proposed_action.tolist(),
            "corrected_action": self.corrected_action.tolist(),
            "intervened": self.intervened,
            "intervention_norm": float(self.intervention_norm),
            "solver_status": self.solver_status,
            "objective_value": self.objective_value,
            "active_constraints": list(self.active_constraints),
            "warm_started": self.warm_started,
            "solve_time_sec": self.solve_time_sec,
            "setup_time_sec": self.setup_time_sec,
            "iterations": self.iterations,
            "construction_time_sec": self.construction_time_sec,
            "device": self.device,
            "metadata": sanitize_metadata(self.metadata),
        }
        # Extended fields are omitted when unset to preserve legacy payload shape
        # for older consumers; when set they are included explicitly.
        if self.canonical_status is not None:
            payload["canonical_status"] = str(self.canonical_status)
        if self.release_decision is not None:
            payload["release_decision"] = str(self.release_decision)
        if self.verification is not None:
            payload["verification"] = self.verification.as_dict()
        if self.solver_provenance is not None:
            payload["solver_provenance"] = self.solver_provenance.as_dict()
        if self.fallback_history:
            payload["fallback_history"] = [h.as_dict() for h in self.fallback_history]
        return payload
