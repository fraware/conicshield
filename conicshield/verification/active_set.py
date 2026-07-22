"""Active-set extraction from verified residuals."""

from __future__ import annotations

import numpy as np

from conicshield.specs.shield_qp import ShieldQPData
from conicshield.verification.residuals import ResidualReport, ResidualTolerances


def active_constraints_from_residuals(
    report: ResidualReport,
    data: ShieldQPData,
    *,
    previous_action: np.ndarray | None = None,
    candidate: np.ndarray,
    active_tol: float | None = None,
    tolerances: ResidualTolerances | None = None,
) -> list[str]:
    """Return stable active-constraint IDs from residuals at ``candidate``.

    Activity requires the candidate to lie within ``active_tol`` of the constraint
    surface. Constraint *presence* alone never implies activity.
    """
    if not report.finite or not report.action_dim_ok:
        return []

    tol = float(active_tol) if active_tol is not None else float(
        (tolerances or ResidualTolerances()).active_tol
    )
    x = np.asarray(candidate, dtype=np.float64).reshape(-1)
    n = int(data.n)
    if x.shape[0] != n:
        return []

    active: list[str] = []
    if abs(float(np.sum(x)) - float(data.simplex_total)) <= tol:
        active.append("simplex.total")

    for i in range(n):
        if abs(float(x[i]) - float(data.lower[i])) <= tol:
            active.append(f"box.lower[{i}]")
        if abs(float(x[i]) - float(data.upper[i])) <= tol:
            active.append(f"box.upper[{i}]")
        if not bool(data.allowed_mask[i]) and abs(float(x[i])) <= tol:
            active.append(f"turn_feasibility[{i}]")

    if previous_action is not None:
        prev = np.asarray(previous_action, dtype=np.float64).reshape(-1)
        if prev.shape[0] != n:
            raise ValueError("previous_action length mismatch in active-set extraction")
        delta = np.asarray(data.max_delta, dtype=np.float64).reshape(-1)
        for i in range(n):
            if not np.isfinite(delta[i]):
                continue
            diff = float(x[i] - prev[i])
            if abs(diff - float(delta[i])) <= tol:
                active.append(f"rate.positive[{i}]")
            if abs(diff + float(delta[i])) <= tol:
                active.append(f"rate.negative[{i}]")

    return active
