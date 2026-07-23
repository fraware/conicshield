"""Fixed constraint topology for the shield QP family.

Topology captures equality / inequality row identities and cone counts. Numeric
bounds, rates, previous actions, weights, and proposals are **not** part of
topology — they fill buffers on a compiled template.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np

from conicshield.specs.shield_qp import ShieldQPData


def _digest(payload: object) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True, slots=True)
class ConstraintTopology:
    """Immutable row/cone topology shared by all rows of a compiled batch."""

    action_dim: int
    equality_ids: tuple[str, ...]
    inequality_ids: tuple[str, ...]
    prohibited_indices: tuple[int, ...]
    include_rate_rows: bool
    rate_indices: tuple[int, ...]
    num_zero_cones: int
    num_nonneg_cones: int
    structural_fingerprint: str

    @property
    def m(self) -> int:
        return int(self.num_zero_cones + self.num_nonneg_cones)

    @property
    def n(self) -> int:
        return int(self.action_dim)


def topology_from_shield_qp(
    data: ShieldQPData,
    *,
    include_rate_rows: bool | None = None,
) -> ConstraintTopology:
    """Derive topology from canonical ``ShieldQPData``.

    Rate inequality rows are included when any ``max_delta`` is finite, unless
    ``include_rate_rows`` forces the choice. Changing prohibited indices or
    rate-row presence changes the fingerprint and requires recompilation.
    """
    n = int(data.n)
    allowed = np.asarray(data.allowed_mask, dtype=bool).reshape(-1)
    if allowed.shape[0] != n:
        raise ValueError("allowed_mask length mismatch against action_dim")

    prohibited = tuple(int(i) for i in range(n) if not bool(allowed[i]))
    eq_ids: list[str] = ["simplex"]
    eq_ids.extend(f"prohibit:{i}" for i in prohibited)

    ineq_ids: list[str] = []
    for i in range(n):
        ineq_ids.append(f"box_lower:{i}")
        ineq_ids.append(f"box_upper:{i}")

    max_delta = np.asarray(data.max_delta, dtype=np.float64).reshape(-1)
    if max_delta.shape[0] != n:
        raise ValueError("max_delta length mismatch against action_dim")
    rate_indices = tuple(int(i) for i in range(n) if np.isfinite(max_delta[i]) and float(max_delta[i]) >= 0.0)
    has_finite_rate = len(rate_indices) > 0
    use_rates = has_finite_rate if include_rate_rows is None else bool(include_rate_rows)
    if use_rates and not rate_indices:
        # Forced include with no finite rates: treat all coords as rate-constrained.
        rate_indices = tuple(range(n))
    if use_rates:
        for i in rate_indices:
            ineq_ids.append(f"rate_pos:{i}")
            ineq_ids.append(f"rate_neg:{i}")

    num_zero = len(eq_ids)
    num_nonneg = len(ineq_ids)
    payload = (
        n,
        tuple(eq_ids),
        tuple(ineq_ids),
        prohibited,
        use_rates,
        rate_indices,
        num_zero,
        num_nonneg,
    )
    return ConstraintTopology(
        action_dim=n,
        equality_ids=tuple(eq_ids),
        inequality_ids=tuple(ineq_ids),
        prohibited_indices=prohibited,
        include_rate_rows=use_rates,
        rate_indices=rate_indices,
        num_zero_cones=num_zero,
        num_nonneg_cones=num_nonneg,
        structural_fingerprint=_digest(payload),
    )


def assert_data_matches_topology(data: ShieldQPData, topology: ConstraintTopology) -> None:
    """Raise ``ValueError`` when ``data`` would imply a different CSR topology."""
    other = topology_from_shield_qp(data, include_rate_rows=topology.include_rate_rows)
    if other.structural_fingerprint != topology.structural_fingerprint:
        raise ValueError(
            "ShieldQPData structural mismatch against compiled topology "
            f"(got {other.structural_fingerprint}, expected {topology.structural_fingerprint})"
        )
