"""Evidence sub-records for AssuranceBundle."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.experimental.assurance.levels import EvidenceKind, EvidenceLevel


@dataclass(frozen=True, slots=True)
class PrimalEvidence:
    equality_residual: float
    inequality_residual: float
    feasible: bool
    kind: EvidenceKind = EvidenceKind.NUMERICAL_RESIDUALS


@dataclass(frozen=True, slots=True)
class DualEvidence:
    dual_values: tuple[float, ...]
    constraint_ids: tuple[str, ...]
    kind: EvidenceKind = EvidenceKind.SOLVER_CLAIMS


@dataclass(frozen=True, slots=True)
class ActiveSetEvidence:
    active_constraints: tuple[str, ...]
    kind: EvidenceKind = EvidenceKind.SOLVER_CLAIMS


@dataclass(frozen=True, slots=True)
class SensitivityEvidence:
    mode: str
    jacobian_norm: float
    agreement_metric: float | None
    forward_solution_digest: str
    kind: EvidenceKind = EvidenceKind.EMPIRICAL_GRADIENT_VALIDATION


@dataclass(frozen=True, slots=True)
class ShadowEvidence:
    primary_backend: str
    shadow_backend: str
    corrected_action_l2: float
    status_disagreement: bool
    problem_digest: str
    kind: EvidenceKind = EvidenceKind.CROSS_SOLVER_AGREEMENT


@dataclass(frozen=True, slots=True)
class FallbackAttempt:
    backend_id: str
    status: str
    reason: str


@dataclass(frozen=True, slots=True)
class DeclaredAssumption:
    assumption_id: str
    statement: str
    verified: bool = False
    kind: EvidenceKind = EvidenceKind.UNVERIFIED_ASSUMPTIONS


@dataclass(frozen=True, slots=True)
class PlatformProvenance:
    operating_system: str
    python_version: str
    cpu_info: str | None = None
    gpu_info: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceSummary:
    level: EvidenceLevel
    kinds_present: tuple[EvidenceKind, ...] = ()
    notes: str = ""
    extras: dict[str, Any] = field(default_factory=dict)


def array_digest(arr: np.ndarray) -> str:
    import hashlib

    data = np.asarray(arr, dtype=np.float64).tobytes()
    return hashlib.sha256(data).hexdigest()[:16]
