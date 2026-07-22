"""Backend-independent residual evaluation against ``ShieldQPData``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.specs.shield_qp import ShieldQPData


@dataclass(frozen=True, slots=True)
class ResidualTolerances:
    """Absolute / relative tolerances for residual gating."""

    abs_tol: float = 1e-6
    rel_tol: float = 1e-6
    active_tol: float = 1e-6
    objective_abs_tol: float = 1e-4
    objective_rel_tol: float = 1e-4

    def scale_aware(self, scale: float) -> float:
        """Return ``max(abs_tol, rel_tol * scale)`` with non-negative scale."""
        s = abs(float(scale))
        return max(float(self.abs_tol), float(self.rel_tol) * s)


@dataclass(frozen=True, slots=True)
class ResidualReport:
    """Numeric residuals for a candidate action."""

    finite: bool
    action_dim_ok: bool
    simplex_residual: float
    lower_residuals: np.ndarray
    upper_residuals: np.ndarray
    prohibited_residuals: np.ndarray
    rate_residuals: np.ndarray | None
    max_equality_residual: float
    max_inequality_residual: float
    objective_residual: float | None
    details: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "finite": self.finite,
            "action_dim_ok": self.action_dim_ok,
            "simplex_residual": float(self.simplex_residual),
            "lower_residuals": np.asarray(self.lower_residuals, dtype=np.float64).tolist(),
            "upper_residuals": np.asarray(self.upper_residuals, dtype=np.float64).tolist(),
            "prohibited_residuals": np.asarray(self.prohibited_residuals, dtype=np.float64).tolist(),
            "rate_residuals": (
                None
                if self.rate_residuals is None
                else np.asarray(self.rate_residuals, dtype=np.float64).tolist()
            ),
            "max_equality_residual": float(self.max_equality_residual),
            "max_inequality_residual": float(self.max_inequality_residual),
            "objective_residual": (
                None if self.objective_residual is None else float(self.objective_residual)
            ),
            "details": dict(self.details),
        }


def _finite_vector(x: np.ndarray) -> bool:
    return bool(np.all(np.isfinite(x)))


def evaluate_residuals(
    candidate: np.ndarray,
    data: ShieldQPData,
    *,
    previous_action: np.ndarray | None = None,
    proposed_action: np.ndarray | None = None,
    reference_action: np.ndarray | None = None,
    policy_weight: float = 1.0,
    reference_weight: float = 0.0,
    reported_objective: float | None = None,
    tolerances: ResidualTolerances | None = None,
) -> ResidualReport:
    """Evaluate finite-ness, dimension, and constraint residuals for ``candidate``.

    Residuals are non-negative violation magnitudes (0 means satisfied).
    """
    del tolerances  # used by callers for gating; this function only reports magnitudes
    x = np.asarray(candidate, dtype=np.float64).reshape(-1)
    n = int(data.n)
    finite = _finite_vector(x) if x.size else False
    action_dim_ok = x.shape[0] == n

    if not action_dim_ok or not finite:
        z = np.zeros(max(n, 0), dtype=np.float64)
        return ResidualReport(
            finite=finite,
            action_dim_ok=action_dim_ok,
            simplex_residual=float("inf") if not finite or not action_dim_ok else 0.0,
            lower_residuals=z.copy(),
            upper_residuals=z.copy(),
            prohibited_residuals=z.copy(),
            rate_residuals=None,
            max_equality_residual=float("inf"),
            max_inequality_residual=float("inf"),
            objective_residual=None,
            details={"reason": 1.0 if not finite else 2.0},
        )

    simplex_residual = float(abs(float(np.sum(x)) - float(data.simplex_total)))

    lower = np.asarray(data.lower, dtype=np.float64).reshape(-1)
    upper = np.asarray(data.upper, dtype=np.float64).reshape(-1)
    lower_residuals = np.maximum(0.0, lower - x)
    upper_residuals = np.maximum(0.0, x - upper)

    allowed = np.asarray(data.allowed_mask, dtype=bool).reshape(-1)
    prohibited_residuals = np.zeros(n, dtype=np.float64)
    prohibited_residuals[~allowed] = np.abs(x[~allowed])

    rate_residuals: np.ndarray | None = None
    if previous_action is not None:
        prev = np.asarray(previous_action, dtype=np.float64).reshape(-1)
        if prev.shape[0] != n:
            raise ValueError("previous_action length mismatch in residual evaluation")
        delta = np.asarray(data.max_delta, dtype=np.float64).reshape(-1)
        # Infinite delta means unconstrained coordinate.
        finite_delta = np.isfinite(delta)
        rate_residuals = np.zeros(n, dtype=np.float64)
        if np.any(finite_delta):
            excess = np.abs(x - prev) - delta
            rate_residuals[finite_delta] = np.maximum(0.0, excess[finite_delta])

    eq_parts = [simplex_residual]
    for i in range(n):
        if not allowed[i]:
            eq_parts.append(float(prohibited_residuals[i]))
    max_eq = float(max(eq_parts)) if eq_parts else 0.0

    ineq_parts = [
        float(np.max(lower_residuals)) if n else 0.0,
        float(np.max(upper_residuals)) if n else 0.0,
    ]
    if rate_residuals is not None and rate_residuals.size:
        ineq_parts.append(float(np.max(rate_residuals)))
    max_ineq = float(max(ineq_parts)) if ineq_parts else 0.0

    objective_residual: float | None = None
    if reported_objective is not None and proposed_action is not None:
        from conicshield.specs.shield_qp import validate_objective_weights

        p = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
        if p.shape[0] == n and _finite_vector(p) and np.isfinite(reported_objective):
            pw, rw = validate_objective_weights(
                policy_weight,
                reference_weight,
                reference_present=reference_action is not None,
            )
            expected = float(pw * np.sum((x - p) ** 2))
            if reference_action is not None and rw > 0.0:
                r = np.asarray(reference_action, dtype=np.float64).reshape(-1)
                if r.shape[0] == n and _finite_vector(r):
                    expected += float(rw * np.sum((x - r) ** 2))
            objective_residual = abs(float(reported_objective) - expected)

    details = {
        "simplex_residual": simplex_residual,
        "max_lower_residual": float(np.max(lower_residuals)) if n else 0.0,
        "max_upper_residual": float(np.max(upper_residuals)) if n else 0.0,
        "max_prohibited_residual": float(np.max(prohibited_residuals)) if n else 0.0,
    }
    if rate_residuals is not None:
        details["max_rate_residual"] = float(np.max(rate_residuals)) if n else 0.0

    return ResidualReport(
        finite=True,
        action_dim_ok=True,
        simplex_residual=simplex_residual,
        lower_residuals=lower_residuals,
        upper_residuals=upper_residuals,
        prohibited_residuals=prohibited_residuals,
        rate_residuals=rate_residuals,
        max_equality_residual=max_eq,
        max_inequality_residual=max_ineq,
        objective_residual=objective_residual,
        details=details,
    )


def residuals_within_tolerance(
    report: ResidualReport,
    tolerances: ResidualTolerances,
    *,
    scale: float = 1.0,
) -> bool:
    """Return True when residual magnitudes are within scale-aware tolerances."""
    if not report.finite or not report.action_dim_ok:
        return False
    tol = tolerances.scale_aware(scale)
    if report.max_equality_residual > tol:
        return False
    if report.max_inequality_residual > tol:
        return False
    if report.objective_residual is not None:
        obj_tol = max(
            float(tolerances.objective_abs_tol),
            float(tolerances.objective_rel_tol) * abs(float(scale)),
        )
        if report.objective_residual > obj_tol:
            return False
    return True
