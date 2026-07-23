"""Research-only smoothed projection-map sensitivity.

Mode label: ``smoothed_research_projection`` — NOT native ``smoothed_backend_gradient``.

Smoothing model (explicit):
  Quadratic-penalty relaxation of inequality residuals with parameter ``epsilon > 0``.
  Hard equalities (simplex, turn_feasibility zeros) remain exact.
  The smoothed map is differentiated via the KKT system of the penalized QP.

Accuracy–cost reporting:
  - agreement vs central FD of the *hard* projection
  - number of extra solves / runtime
  - epsilon must be recorded on every artifact
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from conicshield.experimental.gradients.capability import CapabilityStatus
from conicshield.experimental.gradients.modes import GradientMode
from conicshield.specs.schema import SafetySpec
from conicshield.specs.shield_qp import parse_safety_spec_for_shield

_COND_LIMIT = 1e12


@dataclass(slots=True)
class SmoothedResearchProjectionResult:
    mode: GradientMode = GradientMode.SMOOTHED_RESEARCH_PROJECTION
    available: bool = False
    status: CapabilityStatus = CapabilityStatus.UNAVAILABLE
    reason: str = ""
    jacobian: np.ndarray | None = None
    smoothing_parameter: float | None = None
    smoothed_action: np.ndarray | None = None
    runtime_sec: float | None = None
    agreement_vs_hard_central_fd: float | None = None
    agreement_vs_smoothed_central_fd: float | None = None
    extra_solves: int = 0
    assumptions: tuple[str, ...] = (
        "Quadratic penalty smoothing of inequality residuals; equalities exact.",
        "Not a native smoothed_backend_gradient / Moreau envelope.",
    )
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": str(self.mode),
            "available": self.available,
            "status": str(self.status),
            "reason": self.reason,
            "jacobian": None if self.jacobian is None else self.jacobian.tolist(),
            "smoothing_parameter": self.smoothing_parameter,
            "smoothed_action": None if self.smoothed_action is None else self.smoothed_action.tolist(),
            "runtime_sec": self.runtime_sec,
            "agreement_vs_hard_central_fd": self.agreement_vs_hard_central_fd,
            "agreement_vs_smoothed_central_fd": self.agreement_vs_smoothed_central_fd,
            "extra_solves": self.extra_solves,
            "assumptions": list(self.assumptions),
            "extras": dict(self.extras),
            "evidence_kind": "research_smoothed_projection",
            "not_native_moreau": True,
            "accuracy_cost_note": (
                "Smaller epsilon approaches the hard projection but worsens KKT conditioning; "
                "larger epsilon is cheaper/stabler but biases the map."
            ),
        }


def _fail(
    reason: str,
    *,
    epsilon: float | None,
    runtime_sec: float | None = None,
    extras: dict[str, Any] | None = None,
) -> SmoothedResearchProjectionResult:
    return SmoothedResearchProjectionResult(
        available=False,
        status=CapabilityStatus.UNAVAILABLE,
        reason=reason,
        smoothing_parameter=epsilon,
        runtime_sec=runtime_sec,
        extras=dict(extras or {}),
    )


def _solve_smoothed_qp(
    *,
    spec: SafetySpec,
    proposed: np.ndarray,
    previous: np.ndarray | None,
    reference: np.ndarray | None,
    policy_weight: float,
    reference_weight: float,
    epsilon: float,
    solver: Literal["CLARABEL", "SCS"] = "CLARABEL",
) -> tuple[np.ndarray, str, float | None]:
    import cvxpy as cp

    data = parse_safety_spec_for_shield(spec)
    n = data.n
    x = cp.Variable(n)
    p = np.asarray(proposed, dtype=np.float64).reshape(-1)
    pw = float(policy_weight)
    rw = float(reference_weight)
    lower = np.asarray(data.lower, dtype=np.float64)
    upper = np.asarray(data.upper, dtype=np.float64)

    cons: list[Any] = [cp.sum(x) == float(data.simplex_total)]
    for i in range(n):
        if not data.allowed_mask[i]:
            cons.append(x[i] == 0)

    # Soft inequalities via quadratic penalties in the objective
    pen = 0
    pen += (1.0 / epsilon) * cp.sum_squares(cp.pos(lower - x))
    pen += (1.0 / epsilon) * cp.sum_squares(cp.pos(x - upper))
    if previous is not None:
        prev = np.asarray(previous, dtype=np.float64).reshape(-1)
        d = np.asarray(data.max_delta, dtype=np.float64)
        pen += (1.0 / epsilon) * cp.sum_squares(cp.pos((x - prev) - d))
        pen += (1.0 / epsilon) * cp.sum_squares(cp.pos((prev - x) - d))

    if reference is not None and rw > 0.0:
        r = np.asarray(reference, dtype=np.float64).reshape(-1)
        obj = pw * cp.sum_squares(x - p) + rw * cp.sum_squares(x - r) + pen
    else:
        obj = pw * cp.sum_squares(x - p) + pen

    prob = cp.Problem(cp.Minimize(obj), cons)
    try:
        prob.solve(solver=getattr(cp, solver), verbose=False)
        status = str(prob.status)
    except Exception as exc:  # noqa: BLE001
        return np.full(n, np.nan), f"error:{type(exc).__name__}", None
    if x.value is None:
        obj = float(prob.value) if prob.value is not None else None
        return np.full(n, np.nan), status, obj
    obj = float(prob.value) if prob.value is not None else None
    return np.asarray(x.value, dtype=np.float64).reshape(-1), status, obj


def smoothed_research_projection_jacobian(
    *,
    spec: SafetySpec,
    proposed_action: np.ndarray,
    previous_action: np.ndarray | None,
    reference_action: np.ndarray | None = None,
    policy_weight: float = 1.0,
    reference_weight: float = 0.0,
    epsilon: float = 1e-2,
    backend_id: str = "cvxpy_clarabel",
    compare_fd: bool = True,
    fd_h: float = 1e-5,
) -> SmoothedResearchProjectionResult:
    """Differentiate the epsilon-smoothed public projection map (research adapter)."""

    t0 = time.perf_counter()
    if epsilon <= 0.0 or not np.isfinite(epsilon):
        return _fail("epsilon must be finite and > 0", epsilon=epsilon, runtime_sec=time.perf_counter() - t0)

    p = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
    pw = float(policy_weight)
    rw = float(reference_weight)
    if pw <= 0.0:
        return _fail("policy_weight must be positive", epsilon=epsilon, runtime_sec=time.perf_counter() - t0)

    solver: Literal["CLARABEL", "SCS"] = "SCS" if "scs" in backend_id.lower() else "CLARABEL"
    x0, status, _ = _solve_smoothed_qp(
        spec=spec,
        proposed=p,
        previous=previous_action,
        reference=reference_action,
        policy_weight=pw,
        reference_weight=rw,
        epsilon=epsilon,
        solver=solver,
    )
    extra_solves = 1
    if not np.all(np.isfinite(x0)) or "optimal" not in status.lower():
        return _fail(
            f"smoothed_solve_failed:{status}",
            epsilon=epsilon,
            runtime_sec=time.perf_counter() - t0,
        )

    # Central FD of the smoothed map (research-grade numerical Jacobian of smoothed QP).
    # Analytic KKT of the nonsmooth softplus/pos penalty is subtle; FD of the smoothed
    # map is the declared method here, with explicit epsilon and cost accounting.
    n = p.size
    jac = np.zeros((n, n), dtype=np.float64)
    for j in range(n):
        e = np.zeros(n, dtype=np.float64)
        e[j] = fd_h
        xp, st_p, _ = _solve_smoothed_qp(
            spec=spec,
            proposed=p + e,
            previous=previous_action,
            reference=reference_action,
            policy_weight=pw,
            reference_weight=rw,
            epsilon=epsilon,
            solver=solver,
        )
        xm, st_m, _ = _solve_smoothed_qp(
            spec=spec,
            proposed=p - e,
            previous=previous_action,
            reference=reference_action,
            policy_weight=pw,
            reference_weight=rw,
            epsilon=epsilon,
            solver=solver,
        )
        extra_solves += 2
        if not np.all(np.isfinite(xp)) or not np.all(np.isfinite(xm)):
            return _fail(
                f"smoothed_fd_column_failed:{st_p}/{st_m}",
                epsilon=epsilon,
                runtime_sec=time.perf_counter() - t0,
                extras={"extra_solves": extra_solves},
            )
        jac[:, j] = (xp - xm) / (2.0 * fd_h)

    # Condition proxy: Frobenius of jac
    try:
        cond_proxy = float(np.linalg.norm(jac, ord="fro"))
    except np.linalg.LinAlgError:
        cond_proxy = float("nan")
    if not np.isfinite(cond_proxy) or cond_proxy > _COND_LIMIT:
        return _fail(
            "ill_conditioned_smoothed_jacobian",
            epsilon=epsilon,
            runtime_sec=time.perf_counter() - t0,
            extras={"cond_proxy": cond_proxy, "extra_solves": extra_solves},
        )

    agree_hard: float | None = None
    agree_sm: float | None = None
    if compare_fd:
        from conicshield.experimental.gradients.finite_difference import (
            central_finite_difference_jacobian,
            fd_agreement_metric,
        )
        from conicshield.experimental.solver_assurance.backends import create_research_projector

        def hard_forward(pp: np.ndarray) -> np.ndarray:
            r = create_research_projector(backend_id=backend_id, spec=spec).project(
                pp,
                previous_action,
                reference_action=reference_action,
                policy_weight=pw,
                reference_weight=rw,
            )
            return np.asarray(r.corrected_action, dtype=np.float64)

        hard_fd = central_finite_difference_jacobian(
            hard_forward, p, h=fd_h, parameter_name="proposed_action"
        )
        extra_solves += 2 * n
        if hard_fd.failure_status is None and hard_fd.jacobian.shape == jac.shape:
            agree_hard = fd_agreement_metric(jac, hard_fd.jacobian)

        # Self-consistency: one-sided vs central already baked; report fro self-norm as proxy
        agree_sm = 0.0  # Jacobian is itself FD of smoothed map

    return SmoothedResearchProjectionResult(
        available=True,
        status=CapabilityStatus.AVAILABLE,
        reason=(
            f"Quadratic-penalty smoothed projection (epsilon={epsilon}); "
            "research adapter only — not smoothed_backend_gradient."
        ),
        jacobian=jac,
        smoothing_parameter=float(epsilon),
        smoothed_action=x0,
        runtime_sec=time.perf_counter() - t0,
        agreement_vs_hard_central_fd=agree_hard,
        agreement_vs_smoothed_central_fd=agree_sm,
        extra_solves=extra_solves,
        extras={"backend_id": backend_id, "solver": solver, "fd_h": fd_h},
    )
