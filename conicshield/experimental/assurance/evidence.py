"""Evidence sub-records and full SHA-256 digest helpers for AssuranceBundle v1."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.experimental.assurance.levels import EvidenceKind, EvidenceLevel

SHA256_HEX_LEN = 64


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_full_sha256_hex(value: str | None) -> bool:
    if not isinstance(value, str) or len(value) != SHA256_HEX_LEN:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def array_digest(arr: np.ndarray | None) -> str | None:
    """Full SHA-256 of float64 action bytes. ``None`` if array missing."""

    if arr is None:
        return None
    data = np.asarray(arr, dtype=np.float64)
    if data.size == 0:
        return None
    return sha256_hex(data.tobytes())


def topology_digest(
    *,
    action_dim: int,
    equality_ids: tuple[str, ...] | list[str] = (),
    inequality_ids: tuple[str, ...] | list[str] = (),
    sparse_row_indices: tuple[int, ...] | list[int] | None = None,
    sparse_col_indices: tuple[int, ...] | list[int] | None = None,
    cone_topology: Any = None,
    structural_flags: dict[str, Any] | None = None,
) -> str:
    """Digest of topology only — never includes active-set membership."""

    payload = {
        "action_dim": int(action_dim),
        "equality_ids": list(equality_ids),
        "inequality_ids": list(inequality_ids),
        "sparse_row_indices": None if sparse_row_indices is None else list(sparse_row_indices),
        "sparse_col_indices": None if sparse_col_indices is None else list(sparse_col_indices),
        "cone_topology": cone_topology,
        "structural_flags": structural_flags or {},
    }
    return sha256_hex(canonical_json_bytes(payload))


def problem_digest(
    *,
    topology: str,
    specification: Any,
    proposed_action: np.ndarray | None = None,
    previous_action: np.ndarray | None = None,
    reference_action: np.ndarray | None = None,
    policy_weight: float | None = None,
    reference_weight: float | None = None,
    bounds: Any = None,
    tolerances: dict[str, float] | None = None,
) -> str:
    """Problem digest: topology + spec + actions/weights/bounds/tolerances."""

    payload = {
        "topology_digest": topology,
        "specification": specification,
        "proposed_action_digest": array_digest(proposed_action),
        "previous_action_digest": array_digest(previous_action),
        "reference_action_digest": array_digest(reference_action),
        "policy_weight": policy_weight,
        "reference_weight": reference_weight,
        "bounds": bounds,
        "tolerances": tolerances or {},
    }
    return sha256_hex(canonical_json_bytes(payload))


def forward_solution_digest(
    *,
    problem: str,
    corrected_action: np.ndarray | None,
    equality_residual: float | None,
    inequality_residual: float | None,
    dual_values: tuple[float, ...] | None,
    canonical_status: str,
    verification_status: str,
    residual_tolerance: float | None,
) -> str:
    """Forward digest: problem + solution + residuals/duals + status + verification."""

    payload = {
        "problem_digest": problem,
        "corrected_action_digest": array_digest(corrected_action),
        "equality_residual": equality_residual,
        "inequality_residual": inequality_residual,
        "dual_values": None if dual_values is None else list(dual_values),
        "canonical_status": canonical_status,
        "verification_status": verification_status,
        "residual_tolerance": residual_tolerance,
    }
    return sha256_hex(canonical_json_bytes(payload))


def evidence_bundle_digest(
    *,
    forward: str,
    shadow: dict[str, Any] | None,
    sensitivity: dict[str, Any] | None,
    provenance: dict[str, Any] | None,
    replay: dict[str, Any] | None,
    governed_manifest: dict[str, Any] | None,
) -> str:
    """Whole-bundle digest over forward + optional evidence attachments."""

    payload = {
        "forward_solution_digest": forward,
        "shadow": shadow,
        "sensitivity": sensitivity,
        "provenance": provenance,
        "replay": replay,
        "governed_manifest": governed_manifest,
    }
    return sha256_hex(canonical_json_bytes(payload))


@dataclass(frozen=True, slots=True)
class PrimalEvidence:
    equality_residual: float | None
    inequality_residual: float | None
    feasible: bool
    kind: EvidenceKind = EvidenceKind.NUMERICAL_RESIDUALS
    residuals_present: bool = True


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
    finite_jacobian: bool = True
    fd_comparison_passed: bool | None = None
    active_set_stable: bool | None = None
    synthetic: bool = False
    backend_id: str | None = None
    backend_version: str | None = None

    def is_live_validated(self) -> bool:
        """True only for live, non-synthetic sensitivity that passed FD checks."""

        if self.synthetic:
            return False
        if not self.finite_jacobian or not math.isfinite(float(self.jacobian_norm)):
            return False
        if self.agreement_metric is None or not math.isfinite(float(self.agreement_metric)):
            return False
        if self.fd_comparison_passed is not True:
            return False
        if not is_full_sha256_hex(self.forward_solution_digest) and not self.forward_solution_digest:
            return False
        return True


@dataclass(frozen=True, slots=True)
class ShadowEvidence:
    primary_backend: str
    shadow_backend: str
    corrected_action_l2: float
    status_disagreement: bool
    problem_digest: str
    kind: EvidenceKind = EvidenceKind.CROSS_SOLVER_AGREEMENT
    independently_verified: bool = True
    copied_from_primary: bool = False
    shadow_verification_status: str | None = None

    def is_independent(self) -> bool:
        if self.copied_from_primary:
            return False
        if not self.independently_verified:
            return False
        if self.primary_backend == self.shadow_backend:
            return False
        if not self.problem_digest:
            return False
        return True


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
