"""Shared constraint extraction for shield projection QPs (reference + native paths).

Supported ``SafetySpec`` constraint kinds for v1: ``simplex``, ``turn_feasibility``,
``box``, ``rate``. Others raise ``NotImplementedError``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from conicshield.specs.schema import SafetySpec


SUPPORTED_KINDS = frozenset({"simplex", "turn_feasibility", "box", "rate"})


@dataclass(frozen=True, slots=True)
class ShieldQPData:
    """Dense QP data for native Moreau and CVXPY (action simplex family)."""

    n: int
    simplex_total: float
    lower: np.ndarray
    upper: np.ndarray
    allowed_mask: np.ndarray  # bool length n — False means x[i] must be 0
    max_delta: np.ndarray


def parse_safety_spec_for_shield(spec: SafetySpec) -> ShieldQPData:
    from conicshield.specs.schema import (
        BoxConstraint,
        ConstraintKind,
        RateConstraint,
        SimplexConstraint,
        TurnFeasibilityConstraint,
    )

    n = spec.action_dim
    simplex_total = 1.0
    lower = np.zeros(n, dtype=np.float64)
    upper = np.ones(n, dtype=np.float64)
    allowed = np.ones(n, dtype=bool)
    max_delta = np.full(n, np.inf, dtype=np.float64)

    for c in spec.constraints:
        kind_v = getattr(c, "kind", None)
        if kind_v is None:
            raise TypeError("constraint missing kind")
        kind = kind_v.value if isinstance(kind_v, ConstraintKind) else str(kind_v)
        if kind not in SUPPORTED_KINDS:
            raise NotImplementedError(
                f"Constraint kind {kind!r} is not implemented for solver-backed projection. "
                f"Supported: {sorted(SUPPORTED_KINDS)}."
            )
        if isinstance(c, SimplexConstraint):
            simplex_total = float(c.total)
        elif isinstance(c, BoxConstraint):
            lower[:] = np.array(c.lower, dtype=np.float64)
            upper[:] = np.array(c.upper, dtype=np.float64)
        elif isinstance(c, TurnFeasibilityConstraint):
            allowed[:] = False
            for idx in c.allowed_actions:
                if idx < 0 or idx >= n:
                    raise ValueError(f"allowed_actions index out of range: {idx}")
                allowed[idx] = True
        elif isinstance(c, RateConstraint):
            max_delta[:] = np.array(c.max_delta, dtype=np.float64)

    if not np.any(allowed):
        allowed[:] = True

    return ShieldQPData(
        n=n,
        simplex_total=simplex_total,
        lower=lower,
        upper=upper,
        allowed_mask=allowed,
        max_delta=max_delta,
    )


def objective_pq(
    proposed: np.ndarray,
    reference: np.ndarray | None,
    *,
    policy_weight: float,
    reference_weight: float,
    n: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(P_dense, q)`` for Moreau standard form ``min 0.5 x'Px + q'x``."""
    pw = float(policy_weight)
    rw = float(reference_weight) if reference is not None else 0.0
    if rw < 0.0:
        rw = 0.0
    p = np.asarray(proposed, dtype=np.float64).reshape(-1)
    if p.shape[0] != n:
        raise ValueError(f"proposed_action length {p.shape[0]} != action_dim {n}")
    scale = pw + rw
    if scale <= 0.0:
        scale = 1e-12
    p_mat = np.eye(n, dtype=np.float64) * (2.0 * scale)
    q = -2.0 * pw * p
    if reference is not None and rw > 0.0:
        r = np.asarray(reference, dtype=np.float64).reshape(-1)
        if r.shape[0] != n:
            raise ValueError(f"reference_action length {r.shape[0]} != action_dim {n}")
        q = q - 2.0 * rw * r
    return p_mat, q
