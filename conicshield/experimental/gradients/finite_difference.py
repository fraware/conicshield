"""Finite-difference sensitivity infrastructure (R2 depth)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

from conicshield.experimental.gradients.modes import GradientMode

ArrayFn = Callable[[np.ndarray], np.ndarray]
ActiveSetFn = Callable[[np.ndarray], tuple[str, ...]]
ResidualFn = Callable[[np.ndarray], tuple[float, float]]


@dataclass(slots=True)
class FiniteDifferenceResult:
    mode: GradientMode
    jacobian: np.ndarray
    parameter_name: str
    perturbation_radius: float
    forward_at_base: np.ndarray
    active_set_at_base: tuple[str, ...] = ()
    active_set_changed: bool = False
    primal_residual_before: float = 0.0
    primal_residual_after: float = 0.0
    runtime_sec: float | None = None
    failure_status: str | None = None
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": str(self.mode),
            "parameter_name": self.parameter_name,
            "perturbation_radius": self.perturbation_radius,
            "jacobian": self.jacobian.tolist(),
            "forward_at_base": self.forward_at_base.tolist(),
            "active_set_at_base": list(self.active_set_at_base),
            "active_set_changed": self.active_set_changed,
            "primal_residual_before": self.primal_residual_before,
            "primal_residual_after": self.primal_residual_after,
            "runtime_sec": self.runtime_sec,
            "failure_status": self.failure_status,
            "notes": self.notes,
        }


def _safe_call(f: ArrayFn, x: np.ndarray) -> tuple[np.ndarray | None, str | None]:
    try:
        y = np.asarray(f(x.copy()), dtype=np.float64).reshape(-1)
        if not np.all(np.isfinite(y)):
            return None, "non_finite_output"
        return y, None
    except Exception as exc:  # noqa: BLE001 — research records failures
        return None, f"{type(exc).__name__}:{exc}"


def central_finite_difference_jacobian(
    f: ArrayFn,
    x: np.ndarray,
    *,
    h: float,
    parameter_name: str = "x",
    active_set_fn: ActiveSetFn | None = None,
    residual_fn: ResidualFn | None = None,
) -> FiniteDifferenceResult:
    """Central FD Jacobian of vector-valued f at x."""

    t0 = time.perf_counter()
    x0 = np.asarray(x, dtype=np.float64).reshape(-1)
    y0, fail = _safe_call(f, x0)
    if y0 is None:
        return FiniteDifferenceResult(
            mode=GradientMode.CENTRAL_FINITE_DIFFERENCE,
            jacobian=np.zeros((0, x0.size), dtype=np.float64),
            parameter_name=parameter_name,
            perturbation_radius=float(h),
            forward_at_base=np.array([], dtype=np.float64),
            runtime_sec=time.perf_counter() - t0,
            failure_status=fail,
        )

    m, n = y0.size, x0.size
    jac = np.zeros((m, n), dtype=np.float64)
    active_changed = False
    base_active = active_set_fn(x0) if active_set_fn is not None else ()
    eq0, ineq0 = residual_fn(x0) if residual_fn is not None else (0.0, 0.0)
    eq_after, ineq_after = eq0, ineq0
    failure: str | None = None

    for j in range(n):
        xp = x0.copy()
        xm = x0.copy()
        xp[j] += h
        xm[j] -= h
        yp, fp = _safe_call(f, xp)
        ym, fm = _safe_call(f, xm)
        if yp is None or ym is None:
            failure = fp or fm or "fd_column_failure"
            jac[:, j] = np.nan
            continue
        jac[:, j] = (yp - ym) / (2.0 * h)
        if active_set_fn is not None:
            ap = active_set_fn(xp)
            am = active_set_fn(xm)
            if set(ap) != set(base_active) or set(am) != set(base_active):
                active_changed = True
        if residual_fn is not None:
            ep, ip = residual_fn(xp)
            em, im = residual_fn(xm)
            eq_after = max(eq_after, ep, em)
            ineq_after = max(ineq_after, ip, im)

    return FiniteDifferenceResult(
        mode=GradientMode.CENTRAL_FINITE_DIFFERENCE,
        jacobian=jac,
        parameter_name=parameter_name,
        perturbation_radius=float(h),
        forward_at_base=y0,
        active_set_at_base=tuple(base_active),
        active_set_changed=active_changed,
        primal_residual_before=float(abs(eq0) + abs(ineq0)),
        primal_residual_after=float(abs(eq_after) + abs(ineq_after)),
        runtime_sec=time.perf_counter() - t0,
        failure_status=failure,
    )


def one_sided_finite_difference_jacobian(
    f: ArrayFn,
    x: np.ndarray,
    *,
    h: float,
    parameter_name: str = "x",
    forward: bool = True,
    active_set_fn: ActiveSetFn | None = None,
    residual_fn: ResidualFn | None = None,
) -> FiniteDifferenceResult:
    """One-sided FD Jacobian of vector-valued f at x."""

    t0 = time.perf_counter()
    x0 = np.asarray(x, dtype=np.float64).reshape(-1)
    y0, fail = _safe_call(f, x0)
    if y0 is None:
        return FiniteDifferenceResult(
            mode=GradientMode.ONE_SIDED_FINITE_DIFFERENCE,
            jacobian=np.zeros((0, x0.size), dtype=np.float64),
            parameter_name=parameter_name,
            perturbation_radius=float(h),
            forward_at_base=np.array([], dtype=np.float64),
            runtime_sec=time.perf_counter() - t0,
            failure_status=fail,
            notes="forward" if forward else "backward",
        )

    m, n = y0.size, x0.size
    jac = np.zeros((m, n), dtype=np.float64)
    active_changed = False
    base_active = active_set_fn(x0) if active_set_fn is not None else ()
    eq0, ineq0 = residual_fn(x0) if residual_fn is not None else (0.0, 0.0)
    eq_after, ineq_after = eq0, ineq0
    failure: str | None = None

    for j in range(n):
        xh = x0.copy()
        xh[j] += h if forward else -h
        yh, fh = _safe_call(f, xh)
        if yh is None:
            failure = fh or "fd_column_failure"
            jac[:, j] = np.nan
            continue
        jac[:, j] = (yh - y0) / h if forward else (y0 - yh) / h
        if active_set_fn is not None and set(active_set_fn(xh)) != set(base_active):
            active_changed = True
        if residual_fn is not None:
            eh, ih = residual_fn(xh)
            eq_after = max(eq_after, eh)
            ineq_after = max(ineq_after, ih)

    return FiniteDifferenceResult(
        mode=GradientMode.ONE_SIDED_FINITE_DIFFERENCE,
        jacobian=jac,
        parameter_name=parameter_name,
        perturbation_radius=float(h),
        forward_at_base=y0,
        active_set_at_base=tuple(base_active),
        active_set_changed=active_changed,
        primal_residual_before=float(abs(eq0) + abs(ineq0)),
        primal_residual_after=float(abs(eq_after) + abs(ineq_after)),
        runtime_sec=time.perf_counter() - t0,
        failure_status=failure,
        notes="forward" if forward else "backward",
    )


def fd_agreement_metric(a: np.ndarray, b: np.ndarray) -> float:
    """Relative Frobenius disagreement between two Jacobians (lower is better)."""

    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    if aa.shape != bb.shape:
        return float("nan")
    if not (np.all(np.isfinite(aa)) and np.all(np.isfinite(bb))):
        return float("nan")
    denom = max(float(np.linalg.norm(aa, ord="fro")), 1e-16)
    return float(np.linalg.norm(aa - bb, ord="fro") / denom)


def directional_derivative(jacobian: np.ndarray, direction: np.ndarray) -> np.ndarray:
    jac = np.asarray(jacobian, dtype=np.float64)
    d = np.asarray(direction, dtype=np.float64).reshape(-1)
    if jac.ndim != 2 or jac.shape[1] != d.size:
        raise ValueError(f"direction shape {d.shape} incompatible with jacobian {jac.shape}")
    return jac @ d
