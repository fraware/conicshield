"""Research projection result types and projector protocol.

Uses local research types rather than competing with production
``ProjectionResult`` / future ``BatchProjectionResult`` contracts.
Experiments may wrap production ``ProjectionResult`` via adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np

from conicshield.experimental.adapters.track1_protocols import (
    CanonicalSolverStatus,
    SolverProvenance,
)

if TYPE_CHECKING:
    from conicshield.core.result import ProjectionResult


@dataclass(slots=True)
class ResearchProjectionResult:
    """Research-local projection record with assurance-oriented fields."""

    proposed_action: np.ndarray
    corrected_action: np.ndarray
    intervened: bool
    intervention_norm: float
    solver_status: str
    canonical_status: CanonicalSolverStatus = CanonicalSolverStatus.UNKNOWN
    objective_value: float | None = None
    active_constraints: list[str] = field(default_factory=list)
    warm_started: bool = False
    solve_time_sec: float | None = None
    iterations: int | None = None
    equality_residual: float | None = None
    inequality_residual: float | None = None
    device: str | None = None
    provenance: SolverProvenance | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "proposed_action": self.proposed_action.tolist(),
            "corrected_action": self.corrected_action.tolist(),
            "intervened": self.intervened,
            "intervention_norm": float(self.intervention_norm),
            "solver_status": self.solver_status,
            "canonical_status": str(self.canonical_status),
            "objective_value": self.objective_value,
            "active_constraints": list(self.active_constraints),
            "warm_started": self.warm_started,
            "solve_time_sec": self.solve_time_sec,
            "iterations": self.iterations,
            "equality_residual": self.equality_residual,
            "inequality_residual": self.inequality_residual,
            "device": self.device,
            "provenance": None if self.provenance is None else self.provenance.as_dict(),
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class ResearchBatchProjectionResult:
    """Research adapter for heterogeneous batch projection.

    Track 1 S4 ``project_batch`` exists in production code but heterogeneous
    execution may be NOT_RUN without vendor Moreau. Research uses this adapter
    with explicit ``batch_emulation`` provenance until publication-grade Track 1
    batching is attested.
    """

    results: list[ResearchProjectionResult]
    batch_size: int
    heterogeneous: bool = True
    batch_emulation: str = "sequential_adapter"
    notes: str = (
        "Research adapter only. Final reported frontier results must use Track 1 "
        "heterogeneous batch interface when available; do not emulate batching in "
        "publication-grade results without the batch_emulation provenance flag."
    )
    attestation: dict[str, Any] = field(default_factory=dict)
    publication_grade: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "batch_size": self.batch_size,
            "heterogeneous": self.heterogeneous,
            "batch_emulation": self.batch_emulation,
            "publication_grade": self.publication_grade,
            "attestation": dict(self.attestation),
            "notes": self.notes,
            "results": [r.as_dict() for r in self.results],
            "not_publication_grade_watermark": None
            if self.publication_grade
            else ("NOT_PUBLICATION_GRADE: sequential_adapter batching is a research emulation."),
        }


class ResearchProjectorProtocol(Protocol):
    """Protocol expected by research harnesses."""

    backend_id: str

    def project(
        self,
        proposed_action: np.ndarray,
        previous_action: np.ndarray | None = None,
        *,
        reference_action: np.ndarray | None = None,
        policy_weight: float = 1.0,
        reference_weight: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchProjectionResult: ...


def from_production_projection_result(
    result: ProjectionResult,
    *,
    canonical_status: CanonicalSolverStatus | None = None,
    provenance: SolverProvenance | None = None,
    equality_residual: float | None = None,
    inequality_residual: float | None = None,
) -> ResearchProjectionResult:
    """Adapt a production ``ProjectionResult`` into a research record."""

    # Lazy import avoids circular import through conicshield.backends at module load.
    from conicshield.core.result import ProjectionResult as _ProjectionResult

    if not isinstance(result, _ProjectionResult):
        raise TypeError(f"expected ProjectionResult, got {type(result)!r}")

    status = canonical_status
    if status is None:
        raw = (result.solver_status or "").lower()
        if "optimal" in raw:
            status = CanonicalSolverStatus.OPTIMAL
        elif "infeas" in raw:
            status = CanonicalSolverStatus.INFEASIBLE
        elif "iter" in raw:
            status = CanonicalSolverStatus.ITERATION_LIMIT
        elif "time" in raw:
            status = CanonicalSolverStatus.TIME_LIMIT
        else:
            status = CanonicalSolverStatus.UNKNOWN

    return ResearchProjectionResult(
        proposed_action=np.asarray(result.proposed_action, dtype=np.float64),
        corrected_action=np.asarray(result.corrected_action, dtype=np.float64),
        intervened=bool(result.intervened),
        intervention_norm=float(result.intervention_norm),
        solver_status=str(result.solver_status),
        canonical_status=status,
        objective_value=result.objective_value,
        active_constraints=list(result.active_constraints),
        warm_started=bool(result.warm_started),
        solve_time_sec=result.solve_time_sec,
        iterations=result.iterations,
        equality_residual=equality_residual,
        inequality_residual=inequality_residual,
        device=result.device,
        provenance=provenance,
        metadata=dict(result.metadata),
    )
