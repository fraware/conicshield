"""Research-local stand-ins for Track 1 contracts.

Track 1 S0–S2 (and much of S3–S8) have landed in production modules, but research
keeps local adapters for experimental-only statuses (e.g. ``UNAVAILABLE``) and to
avoid competing with production release/verification contracts. When research needs
production types, prefer adapters that wrap production results
(``from_production_projection_result``) rather than reimplementing production APIs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Protocol

import numpy as np


class CanonicalSolverStatus(StrEnum):
    """Research adapter for Track 1 canonical solver status."""

    OPTIMAL = "optimal"
    INFEASIBLE = "infeasible"
    UNBOUNDED = "unbounded"
    ITERATION_LIMIT = "iteration_limit"
    TIME_LIMIT = "time_limit"
    NUMERICAL_FAILURE = "numerical_failure"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class ReleaseDecision(StrEnum):
    """Research adapter for Track 1 release decision."""

    APPROVE = "approve"
    REJECT = "reject"
    FALLBACK = "fallback"
    REVIEW = "review"
    EXPERIMENTAL_ONLY = "experimental_only"


@dataclass(frozen=True, slots=True)
class SolverProvenance:
    """Research adapter for Track 1 solver provenance."""

    backend_id: str
    solver_name: str
    solver_version: str | None
    package_distribution: str | None
    package_version: str | None
    package_source: str | None = None
    package_hash: str | None = None
    device: str | None = None
    algorithm: str | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    warm_start_policy: str | None = None
    platform_note: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ResearchVerificationReport:
    """Research adapter for Track 1 VerificationReport."""

    equality_residual: float
    inequality_residual: float
    primal_feasible: bool
    dual_available: bool
    residual_tolerance: float
    checks: dict[str, bool] = field(default_factory=dict)
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ConstraintTopology:
    """Research adapter placeholder for Track 1 ConstraintTopology."""

    action_dim: int
    equality_ids: tuple[str, ...]
    inequality_ids: tuple[str, ...]
    structural_fingerprint: str


@dataclass(frozen=True, slots=True)
class CompiledShieldTemplate:
    """Research adapter placeholder for Track 1 CompiledShieldTemplate."""

    template_id: str
    topology: ConstraintTopology
    specification_digest: str
    notes: str = "research-local adapter; replace with Track 1 implementation"


class StatefulProjectorProtocol(Protocol):
    """Research adapter for Track 1 stateful projector protocol."""

    def project(
        self,
        proposed_action: np.ndarray,
        previous_action: np.ndarray | None = None,
        *,
        reference_action: np.ndarray | None = None,
        policy_weight: float = 1.0,
        reference_weight: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> Any: ...

    def reset_state(self) -> None: ...
