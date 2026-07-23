"""Native smoothed backend gradient via softplus inequality softening on Moreau QP.

Mode: ``smoothed_backend_gradient`` — distinct from ``smoothed_research_projection``.

Mechanism (declared):
  Softplus / Moreau-Yosida-style softening of inequality residuals on the same
  shield QP that Moreau solves, with smoothing parameter ``ε > 0``:

      min_x  ½ x' P x + q' x + Σ_i ε · softplus( (A_I x − b_I)_i / ε )
      s.t.   A_E x = b_E

  Equalities (zero cones) stay hard. As ε → 0, ε·softplus(r/ε) → max(r, 0).

  The smooth KKT system is solved by Newton (warm-started from a live Moreau
  hard solve) and differentiated via the implicit-function theorem to obtain
  ``dx/dq``, then ``dx/du = −2 pw · dx/dq``.

  No vendor envelope API exists on Moreau 0.3.3; ``moreau.torch`` provides
  exact autograd through the hard solve only — not a smoothed surface. This
  module therefore implements explicit backend smoothing.

Fail-closed on native Windows (Moreau unsupported) and when Moreau is not
importable. Status is ``AVAILABLE`` or ``UNAVAILABLE`` only.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.experimental.gradients.capability import CapabilityStatus
from conicshield.experimental.gradients.exact_backend import (
    _probe_vendor_compiled_backward,
    build_moreau_shield_qp,
    solve_moreau_compiled,
)
from conicshield.experimental.gradients.modes import GradientMode
from conicshield.specs.schema import SafetySpec

_FD_AGREE_FAIL = 5e-2
_NEWTON_MAX_ITER = 40
_NEWTON_TOL = 1e-10
_COND_LIMIT = 1e14


def _sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.asarray(z, dtype=np.float64)
    out = np.empty_like(z)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def _softplus(z: np.ndarray) -> np.ndarray:
    """Numerically stable softplus(z) = log(1+exp(z))."""

    z = np.asarray(z, dtype=np.float64)
    out = np.empty_like(z)
    pos = z > 20.0
    neg = z < -20.0
    mid = ~pos & ~neg
    out[pos] = z[pos]
    out[neg] = np.exp(z[neg])
    out[mid] = np.log1p(np.exp(z[mid]))
    return out


def _softplus_penalty(residual: np.ndarray, epsilon: float) -> np.ndarray:
    """ε · softplus(r/ε) → max(r, 0) as ε → 0."""

    return float(epsilon) * _softplus(residual / float(epsilon))


def _softplus_grad_hess_diag(
    residual: np.ndarray, epsilon: float
) -> tuple[np.ndarray, np.ndarray]:
    """Gradient and Hessian diagonal of Σ ε softplus(r_i/ε) w.r.t. residual."""

    eps = float(epsilon)
    s = _sigmoid(residual / eps)
    grad = s  # d/dr [ε softplus(r/ε)] = sigmoid(r/ε)
    hess = s * (1.0 - s) / eps
    return grad, hess


@dataclass(slots=True)
class SmoothedBackendGradientResult:
    mode: GradientMode = GradientMode.SMOOTHED_BACKEND_GRADIENT
    available: bool = False
    status: CapabilityStatus = CapabilityStatus.UNAVAILABLE
    reason: str = ""
    jacobian: np.ndarray | None = None
    smoothing_parameter: float | None = None
    smoothed_action: np.ndarray | None = None
    agreement_vs_smoothed_central_fd: float | None = None
    agreement_vs_exact_backend: float | None = None
    runtime_sec: float | None = None
    assumptions: tuple[str, ...] = (
        "Softplus inequality softening on the Moreau shield QP; equalities hard.",
        "Jacobian via IFT on the smooth equality-constrained KKT (Newton).",
        "Warm-started from live Moreau CompiledSolver hard projection.",
        "Not smoothed_research_projection; not exact_backend_gradient.",
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
            "smoothed_action": None
            if self.smoothed_action is None
            else self.smoothed_action.tolist(),
            "agreement_vs_smoothed_central_fd": self.agreement_vs_smoothed_central_fd,
            "agreement_vs_exact_backend": self.agreement_vs_exact_backend,
            "runtime_sec": self.runtime_sec,
            "assumptions": list(self.assumptions),
            "extras": dict(self.extras),
            "not_research_smoothed": True,
            "mechanism": "softplus_inequality_softening_moreau_qp",
            "accuracy_cost_note": (
                "Smaller ε approaches the hard Moreau projection but worsens "
                "conditioning of the softplus Hessian; larger ε is stabler but "
                "biases the map away from exact_backend_gradient."
            ),
        }


def _fail(
    reason: str,
    *,
    epsilon: float | None,
    extras: dict[str, Any] | None = None,
    runtime_sec: float | None = None,
) -> SmoothedBackendGradientResult:
    return SmoothedBackendGradientResult(
        available=False,
        status=CapabilityStatus.UNAVAILABLE,
        reason=reason,
        smoothing_parameter=epsilon,
        runtime_sec=runtime_sec,
        extras=dict(extras or {}),
    )


def _nullspace_basis(a_eq: np.ndarray, n: int) -> np.ndarray:
    """Orthonormal basis for null(A_E); empty (n,0) if full rank equalities cover R^n."""

    if a_eq.size == 0:
        return np.eye(n, dtype=np.float64)
    # SVD: nullspace from V^T rows with small singular values
    _u, s, vt = np.linalg.svd(a_eq, full_matrices=True)
    tol = float(np.max(s)) * max(a_eq.shape) * np.finfo(float).eps if s.size else 0.0
    rank = int(np.sum(s > tol)) if s.size else 0
    return vt[rank:].T.copy()


def _particular_equality_solution(a_eq: np.ndarray, b_eq: np.ndarray, n: int) -> np.ndarray:
    if a_eq.size == 0:
        return np.zeros(n, dtype=np.float64)
    x0, *_ = np.linalg.lstsq(a_eq, b_eq, rcond=None)
    return np.asarray(x0, dtype=np.float64).reshape(-1)


def _solve_softplus_smoothed(
    *,
    p_diag: np.ndarray,
    q: np.ndarray,
    a_eq: np.ndarray,
    b_eq: np.ndarray,
    a_ineq: np.ndarray,
    b_ineq: np.ndarray,
    epsilon: float,
    x_warm: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Equality-constrained softplus-smoothed QP via reduced-space Newton."""

    n = int(p_diag.size)
    z = _particular_equality_solution(a_eq, b_eq, n)
    nbasis = _nullspace_basis(a_eq, n)
    # Project warm start into affine subspace: x = z + N y
    if nbasis.shape[1] == 0:
        x = z.copy()
        meta = {"newton_iters": 0, "reduced_dim": 0, "final_kkt_norm": 0.0}
        return x, meta

    # y0 from warm start
    y = nbasis.T @ (np.asarray(x_warm, dtype=np.float64).reshape(-1) - z)
    p = np.asarray(p_diag, dtype=np.float64).reshape(-1)
    qq = np.asarray(q, dtype=np.float64).reshape(-1)
    a_i = np.asarray(a_ineq, dtype=np.float64)
    b_i = np.asarray(b_ineq, dtype=np.float64).reshape(-1)
    eps = float(epsilon)

    final_grad_norm = float("inf")
    newton_iters = 0
    for step_i in range(1, _NEWTON_MAX_ITER + 1):
        newton_iters = step_i
        x = z + nbasis @ y
        resid = a_i @ x - b_i if a_i.size else np.zeros(0, dtype=np.float64)
        sig, hess_diag = _softplus_grad_hess_diag(resid, eps)
        # full gradient of smooth objective
        g = p * x + qq
        if a_i.size:
            g = g + a_i.T @ sig
        # reduced gradient
        g_red = nbasis.T @ g
        final_grad_norm = float(np.linalg.norm(g_red, ord=2))
        if final_grad_norm < _NEWTON_TOL:
            break
        # reduced Hessian
        h = np.diag(p)
        if a_i.size:
            h = h + (a_i.T * hess_diag) @ a_i
        h_red = nbasis.T @ h @ nbasis
        try:
            dy = -np.linalg.solve(h_red, g_red)
        except np.linalg.LinAlgError:
            dy = -np.linalg.lstsq(h_red, g_red, rcond=None)[0]
        # backtracking
        step = 1.0
        obj0 = 0.5 * float(np.dot(p * x, x)) + float(np.dot(qq, x))
        if a_i.size:
            obj0 += float(np.sum(_softplus_penalty(resid, eps)))
        accepted = False
        for _ in range(12):
            y_trial = y + step * dy
            x_trial = z + nbasis @ y_trial
            resid_t = a_i @ x_trial - b_i if a_i.size else np.zeros(0, dtype=np.float64)
            obj_t = 0.5 * float(np.dot(p * x_trial, x_trial)) + float(np.dot(qq, x_trial))
            if a_i.size:
                obj_t += float(np.sum(_softplus_penalty(resid_t, eps)))
            if obj_t <= obj0 + 1e-4 * step * float(np.dot(g_red, dy)):
                y = y_trial
                accepted = True
                break
            step *= 0.5
        if not accepted:
            y = y + step * dy
    x = z + nbasis @ y
    meta = {
        "newton_iters": newton_iters,
        "reduced_dim": int(nbasis.shape[1]),
        "final_kkt_norm": final_grad_norm,
    }
    return x, meta


def _jacobian_softplus_ift(
    *,
    p_diag: np.ndarray,
    x: np.ndarray,
    a_eq: np.ndarray,
    a_ineq: np.ndarray,
    b_ineq: np.ndarray,
    epsilon: float,
    pw: float,
) -> np.ndarray:
    """dx/du via IFT on the smooth KKT (reduced space)."""

    n = int(p_diag.size)
    nbasis = _nullspace_basis(a_eq, n)
    if nbasis.shape[1] == 0:
        return np.zeros((n, n), dtype=np.float64)

    a_i = np.asarray(a_ineq, dtype=np.float64)
    resid = a_i @ x - np.asarray(b_ineq, dtype=np.float64).reshape(-1) if a_i.size else np.zeros(0)
    _sig, hess_diag = _softplus_grad_hess_diag(resid, float(epsilon))
    h = np.diag(np.asarray(p_diag, dtype=np.float64))
    if a_i.size:
        h = h + (a_i.T * hess_diag) @ a_i
    h_red = nbasis.T @ h @ nbasis
    cond = float(np.linalg.cond(h_red)) if h_red.size else 0.0
    if not np.isfinite(cond) or cond > _COND_LIMIT:
        raise RuntimeError(f"ill_conditioned_reduced_hessian:{cond}")

    # d(grad)/dq = I  =>  H_red dy/dq = -N' I  => dy/dq = -H_red^{-1} N'
    # dx/dq = N dy/dq
    rhs = -nbasis.T  # (k, n)
    try:
        dy_dq = np.linalg.solve(h_red, rhs)
    except np.linalg.LinAlgError as exc:
        raise RuntimeError(f"reduced_hessian_solve_failed:{exc}") from exc
    dx_dq = nbasis @ dy_dq
    # q = -2 pw u - ...  => dx/du = dx/dq * dq/du = -2 pw dx/dq
    return (-2.0 * float(pw)) * dx_dq


def smoothed_backend_gradient(
    *args: Any,
    spec: SafetySpec | None = None,
    proposed_action: np.ndarray | None = None,
    previous_action: np.ndarray | None = None,
    reference_action: np.ndarray | None = None,
    policy_weight: float = 1.0,
    reference_weight: float = 0.0,
    smoothing_parameter: float | None = 1e-2,
    compare_central_fd: bool = True,
    compare_exact_backend: bool = True,
    fd_h: float = 1e-5,
    max_iter: int = 200,
    **kwargs: Any,
) -> SmoothedBackendGradientResult:
    """Live smoothed backend jacobian, or fail closed (AVAILABLE / UNAVAILABLE)."""

    del args, kwargs
    eps = 1e-2 if smoothing_parameter is None else float(smoothing_parameter)
    caps = _probe_vendor_compiled_backward()
    caps = {
        **caps,
        "smoothed_mechanism": "softplus_inequality_softening_moreau_qp",
        "smoothed_native_api": True,  # experimental implementation (not vendor envelope)
        "vendor_envelope_api": False,
    }

    if caps.get("windows_native_unsupported"):
        return _fail(
            "Moreau unsupported on native Windows; use WSL/Linux for "
            "smoothed_backend_gradient.",
            epsilon=eps,
            extras={
                **caps,
                "gap_vs_smoothed_research_projection": (
                    "Research smoothed_research_projection uses Clarabel/SCS; "
                    "smoothed_backend_gradient requires live Moreau on Linux/WSL."
                ),
            },
        )

    if not caps.get("package_importable") or not caps.get("vendor_compiled_backward_api"):
        return _fail(
            "Moreau CompiledSolver.backward unavailable; cannot warm-start / attest "
            "smoothed_backend_gradient on this host.",
            epsilon=eps,
            extras={
                **caps,
                "gap_vs_smoothed_research_projection": (
                    "Research smoothed_research_projection ≠ native smoothed_backend_gradient."
                ),
                "missing_evidence": list(caps.get("missing_evidence") or [])
                + ["live Moreau hard solve for smoothed warm-start"],
            },
        )

    if spec is None or proposed_action is None:
        return _fail(
            "smoothed_backend_gradient requires SafetySpec + proposed_action; "
            "capability present but no live jacobian without problem data.",
            epsilon=eps,
            extras={
                **caps,
                "gap_vs_smoothed_research_projection": (
                    "Research smoothed_research_projection is a public-solver adapter; "
                    "native smoothed_backend_gradient softens the Moreau shield QP."
                ),
                "missing_evidence": [
                    "live smoothed jacobian sample with SafetySpec + actions"
                ],
            },
        )

    if not np.isfinite(eps) or eps <= 0.0:
        return _fail("smoothing_parameter ε must be finite and > 0", epsilon=eps, extras=caps)

    t0 = time.perf_counter()
    try:
        qp = build_moreau_shield_qp(
            spec=spec,
            proposed_action=proposed_action,
            previous_action=previous_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
        )
        pw = float(qp["pw"])
        if pw <= 0.0:
            return _fail(
                "policy_weight must be > 0",
                epsilon=eps,
                extras={**caps, "policy_weight": pw},
                runtime_sec=time.perf_counter() - t0,
            )

        _moreau, _solver, x_hard = solve_moreau_compiled(
            qp, enable_grad=False, max_iter=max_iter
        )
        if not np.all(np.isfinite(x_hard)):
            return _fail(
                "moreau_hard_warmstart_non_finite",
                epsilon=eps,
                extras=caps,
                runtime_sec=time.perf_counter() - t0,
            )

        x_soft, newton_meta = _solve_softplus_smoothed(
            p_diag=qp["p_diag"],
            q=qp["q"],
            a_eq=qp["a_eq"],
            b_eq=qp["b_eq"],
            a_ineq=qp["a_ineq"],
            b_ineq=qp["b_ineq"],
            epsilon=eps,
            x_warm=x_hard,
        )
        if not np.all(np.isfinite(x_soft)):
            return _fail(
                "softplus_newton_non_finite",
                epsilon=eps,
                extras={**caps, **newton_meta},
                runtime_sec=time.perf_counter() - t0,
            )
        if newton_meta["final_kkt_norm"] > 1e-4:
            return _fail(
                f"softplus_newton_not_converged:{newton_meta['final_kkt_norm']}",
                epsilon=eps,
                extras={**caps, **newton_meta},
                runtime_sec=time.perf_counter() - t0,
            )

        jac = _jacobian_softplus_ift(
            p_diag=qp["p_diag"],
            x=x_soft,
            a_eq=qp["a_eq"],
            a_ineq=qp["a_ineq"],
            b_ineq=qp["b_ineq"],
            epsilon=eps,
            pw=pw,
        )
        if not np.all(np.isfinite(jac)):
            return _fail(
                "smoothed_jacobian_non_finite",
                epsilon=eps,
                extras={**caps, **newton_meta},
                runtime_sec=time.perf_counter() - t0,
            )

        agree_sm: float | None = None
        agree_ex: float | None = None
        fd_extras: dict[str, Any] = {}
        if compare_central_fd:
            from conicshield.experimental.gradients.finite_difference import (
                central_finite_difference_jacobian,
                fd_agreement_metric,
            )

            tmpl = qp["tmpl"]
            data = qp["data"]
            prev = qp["prev"]
            ref = qp["ref"]
            rw = float(qp["rw"])
            u = qp["u"]

            def smoothed_forward(pp: np.ndarray) -> np.ndarray:
                qp2 = build_moreau_shield_qp(
                    spec=spec,
                    proposed_action=pp,
                    previous_action=prev,
                    reference_action=ref,
                    policy_weight=pw,
                    reference_weight=rw,
                )
                # cheap warm-start: previous soft solution shifted / hard solve
                try:
                    _m, _s, xh = solve_moreau_compiled(
                        qp2, enable_grad=False, max_iter=max_iter
                    )
                except Exception:  # noqa: BLE001
                    xh = x_soft
                xs, _meta = _solve_softplus_smoothed(
                    p_diag=qp2["p_diag"],
                    q=qp2["q"],
                    a_eq=qp2["a_eq"],
                    b_eq=qp2["b_eq"],
                    a_ineq=qp2["a_ineq"],
                    b_ineq=qp2["b_ineq"],
                    epsilon=eps,
                    x_warm=xh,
                )
                return xs

            # silence unused in closure type checkers
            del tmpl, data

            fd = central_finite_difference_jacobian(
                smoothed_forward, u, h=float(fd_h), parameter_name="proposed_action"
            )
            fd_extras = {
                "fd_failure_status": fd.failure_status,
                "fd_active_set_changed": fd.active_set_changed,
            }
            if fd.failure_status is not None:
                return _fail(
                    f"smoothed_fd_comparison_failed:{fd.failure_status}",
                    epsilon=eps,
                    extras={**caps, **newton_meta, **fd_extras},
                    runtime_sec=time.perf_counter() - t0,
                )
            if fd.jacobian.shape != jac.shape:
                return _fail(
                    "smoothed_fd_jacobian_shape_mismatch",
                    epsilon=eps,
                    extras={**caps, **newton_meta, **fd_extras},
                    runtime_sec=time.perf_counter() - t0,
                )
            agree_sm = fd_agreement_metric(jac, fd.jacobian)
            if not np.isfinite(agree_sm) or agree_sm > _FD_AGREE_FAIL:
                return _fail(
                    f"smoothed_fd_agreement_exceeded:{agree_sm}",
                    epsilon=eps,
                    extras={
                        **caps,
                        **newton_meta,
                        **fd_extras,
                        "agreement_vs_smoothed_central_fd": agree_sm,
                        "threshold": _FD_AGREE_FAIL,
                    },
                    runtime_sec=time.perf_counter() - t0,
                )

        if compare_exact_backend:
            from conicshield.experimental.gradients.exact_backend import (
                exact_backend_gradient,
            )
            from conicshield.experimental.gradients.finite_difference import (
                fd_agreement_metric,
            )

            ex = exact_backend_gradient(
                spec=spec,
                proposed_action=proposed_action,
                previous_action=previous_action,
                reference_action=reference_action,
                policy_weight=pw,
                reference_weight=float(qp["rw"]),
                compare_central_fd=False,
                max_iter=max_iter,
            )
            fd_extras["exact_backend_status"] = str(ex.status)
            fd_extras["exact_backend_available"] = bool(ex.available)
            if ex.available and ex.jacobian is not None and ex.jacobian.shape == jac.shape:
                agree_ex = fd_agreement_metric(jac, ex.jacobian)
                fd_extras["accuracy_cost_vs_exact_rel_fro"] = agree_ex

        hard_bias = float(np.linalg.norm(x_soft - x_hard))
        return SmoothedBackendGradientResult(
            available=True,
            status=CapabilityStatus.AVAILABLE,
            reason=(
                f"Softplus-smoothed Moreau shield map (ε={eps}); IFT jacobian; "
                "experimental (production differentiation_api unchanged)."
            ),
            jacobian=jac,
            smoothing_parameter=eps,
            smoothed_action=x_soft,
            agreement_vs_smoothed_central_fd=agree_sm,
            agreement_vs_exact_backend=agree_ex,
            runtime_sec=time.perf_counter() - t0,
            extras={
                **caps,
                **newton_meta,
                **fd_extras,
                "hard_moreau_action": x_hard.tolist(),
                "soft_vs_hard_l2": hard_bias,
                "policy_weight": pw,
                "reference_weight": float(qp["rw"]),
            },
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(
            f"smoothed_backend_failure:{type(exc).__name__}:{exc}",
            epsilon=eps,
            extras=caps,
            runtime_sec=time.perf_counter() - t0,
        )

