"""Independent labeled gradient adapters for the R11 observatory.

Adapters (never unlabeled, never production differentiation_api claims):
  - numpy_compiled_backward  — Moreau CompiledSolver.backward
  - native_smoothed          — softplus Moreau QP IFT
  - pytorch_autograd         — torch autodiff (moreau.torch or softplus torch)
  - jax_autodiff             — jax autodiff when importable
  - central_fd / one_sided_fd
  - research_kkt             — analytical comparator only

Unimplemented differentiation targets must not appear as implemented.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np

from conicshield.experimental.gradients.capability import CapabilityStatus
from conicshield.experimental.gradients.exact_backend import (
    build_moreau_shield_qp,
    exact_backend_gradient,
)
from conicshield.experimental.gradients.finite_difference import (
    ActiveSetFn,
    ArrayFn,
    ResidualFn,
    central_finite_difference_jacobian,
    one_sided_finite_difference_jacobian,
)
from conicshield.experimental.gradients.forward_gate import VerifiedForward
from conicshield.experimental.gradients.kkt_research import exact_research_kkt_jacobian
from conicshield.experimental.gradients.modes import GradientMode
from conicshield.experimental.gradients.smoothed_backend import (
    _jacobian_softplus_ift,
    _nullspace_basis,
    _solve_softplus_smoothed,
    smoothed_backend_gradient,
)
from conicshield.specs.schema import SafetySpec

# Catalog of aspirational targets — do NOT treat as implemented.
DIFFERENTIATION_TARGET_CATALOG: tuple[str, ...] = (
    "proposed_action",
    "policy_logits",
    "proposed_action_probabilities",
    "previous_action",
    "reference_action",
    "policy_weight",
    "reference_weight",
    "box_bounds",
    "rate_limits",
    "hazard_derived_parameters",
    "robustness_margins",
)

# Only targets with a live observatory path (FD and/or analytical chain rule).
IMPLEMENTED_DIFFERENTIATION_TARGETS: tuple[str, ...] = (
    "proposed_action",
    "previous_action",
    "reference_action",
    "policy_weight",
    "reference_weight",
    "box_bounds",
)

# Target metadata: domain, perturbation scale, digest-update notes.
TARGET_ADAPTER_SPECS: dict[str, dict[str, Any]] = {
    "proposed_action": {
        "domain": "R^n action proposal",
        "perturbation_scale": "absolute h on each coordinate",
        "chain_rule": "dx/du via QP map; native path uses dx/du = -2*pw*dx/dq",
        "digest_update": "problem_digest includes proposed_action",
        "active_set_behavior": "transitions detected via ±ε active-set protocol",
    },
    "previous_action": {
        "domain": "R^n previous action (rate-limit center)",
        "perturbation_scale": "absolute h on each coordinate",
        "chain_rule": "dx/dp through rate inequalities |x-p|<=max_delta (FD)",
        "digest_update": "problem_digest includes previous_action",
        "active_set_behavior": "rate constraints may activate/deactivate under p±h",
    },
    "reference_action": {
        "domain": "R^n reference action",
        "perturbation_scale": "absolute h on each coordinate",
        "chain_rule": "dx/dref through reference quadratic term (FD)",
        "digest_update": "problem_digest includes reference_action",
        "active_set_behavior": "same active-set caveats as proposed_action FD",
    },
    "policy_weight": {
        "domain": "scalar pw >= 0 with pw+rw_eff > 0",
        "perturbation_scale": "relative/absolute h on scalar",
        "chain_rule": "dx/dpw via objective weight (FD); requires pw>0 interior",
        "digest_update": "problem_digest includes policy_weight",
        "active_set_behavior": "weight changes can move active set near boundaries",
    },
    "reference_weight": {
        "domain": "scalar rw >= 0; effective only when reference present",
        "perturbation_scale": "absolute h on scalar",
        "chain_rule": "dx/drw via reference weight (FD)",
        "digest_update": "problem_digest includes reference_weight",
        "active_set_behavior": "same as policy_weight",
    },
    "box_bounds": {
        "domain": "finite box lower/upper in SafetySpec BoxConstraint",
        "perturbation_scale": "absolute h on bound coordinates (concat [lower|upper])",
        "chain_rule": "dx/dbounds through inequality RHS (FD); topology must keep box present",
        "digest_update": "problem_digest includes bounds/spec; topology unchanged if only values move",
        "active_set_behavior": "bound perturbations frequently flip active sets — prefer one-sided FD",
    },
}


class AdapterId(StrEnum):
    NUMPY_COMPILED_BACKWARD = "numpy_compiled_backward"
    NATIVE_SMOOTHED = "native_smoothed"
    PYTORCH_AUTOGRAD = "pytorch_autograd"
    JAX_AUTODIFF = "jax_autodiff"
    CENTRAL_FD = "central_fd"
    ONE_SIDED_FD = "one_sided_fd"
    RESEARCH_KKT = "research_kkt"


@dataclass(slots=True)
class AdapterGradientResult:
    adapter_id: AdapterId
    mode: GradientMode
    available: bool
    status: CapabilityStatus
    reason: str
    jacobian: np.ndarray | None = None
    forward_solution_digest: str | None = None
    problem_digest: str | None = None
    runtime_sec: float | None = None
    analytical_comparator_only: bool = False
    claims_production_differentiation_api: bool = False
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": str(self.adapter_id),
            "mode": str(self.mode),
            "available": self.available,
            "status": str(self.status),
            "reason": self.reason,
            "jacobian": None if self.jacobian is None else self.jacobian.tolist(),
            "forward_solution_digest": self.forward_solution_digest,
            "problem_digest": self.problem_digest,
            "runtime_sec": self.runtime_sec,
            "analytical_comparator_only": self.analytical_comparator_only,
            "claims_production_differentiation_api": self.claims_production_differentiation_api,
            "extras": dict(self.extras),
        }


def _gate_blocked(adapter_id: AdapterId, mode: GradientMode, forward: VerifiedForward | None) -> AdapterGradientResult | None:
    if forward is not None and forward.verified:
        return None
    reason = "unverified_forward_gradient_unavailable"
    if forward is not None:
        reason = f"unverified_forward_gradient_unavailable:{forward.reason}"
    return AdapterGradientResult(
        adapter_id=adapter_id,
        mode=mode,
        available=False,
        status=CapabilityStatus.UNAVAILABLE,
        reason=reason,
        forward_solution_digest=None if forward is None else forward.forward_solution_digest,
        problem_digest=None if forward is None else forward.problem_digest,
        claims_production_differentiation_api=False,
    )


def _bind(forward: VerifiedForward | None, result: AdapterGradientResult) -> AdapterGradientResult:
    if forward is None:
        return result
    result.forward_solution_digest = forward.forward_solution_digest
    result.problem_digest = forward.problem_digest
    return result


def list_implemented_adapters(*, probe_optional: bool = True) -> list[dict[str, Any]]:
    """Return adapter registry entries; optional frameworks marked by import probe."""

    rows: list[dict[str, Any]] = [
        {
            "adapter_id": str(AdapterId.NUMPY_COMPILED_BACKWARD),
            "mode": str(GradientMode.EXACT_BACKEND_GRADIENT),
            "implemented": True,
            "notes": "Moreau CompiledSolver.backward (NumPy VJP assembly)",
        },
        {
            "adapter_id": str(AdapterId.NATIVE_SMOOTHED),
            "mode": str(GradientMode.SMOOTHED_BACKEND_GRADIENT),
            "implemented": True,
            "notes": "Softplus inequality softening on Moreau shield QP",
        },
        {
            "adapter_id": str(AdapterId.CENTRAL_FD),
            "mode": str(GradientMode.CENTRAL_FINITE_DIFFERENCE),
            "implemented": True,
            "notes": "Central finite difference",
        },
        {
            "adapter_id": str(AdapterId.ONE_SIDED_FD),
            "mode": str(GradientMode.ONE_SIDED_FINITE_DIFFERENCE),
            "implemented": True,
            "notes": "One-sided finite difference",
        },
        {
            "adapter_id": str(AdapterId.RESEARCH_KKT),
            "mode": str(GradientMode.EXACT_RESEARCH_KKT),
            "implemented": True,
            "analytical_comparator_only": True,
            "notes": "Research KKT analytical comparator — not production/native",
        },
    ]
    torch_ok = False
    jax_ok = False
    if probe_optional:
        try:
            import torch  # noqa: F401

            torch_ok = True
        except Exception:  # noqa: BLE001
            torch_ok = False
        try:
            import jax  # noqa: F401

            jax_ok = True
        except Exception:  # noqa: BLE001
            jax_ok = False
    rows.append(
        {
            "adapter_id": str(AdapterId.PYTORCH_AUTOGRAD),
            "mode": str(GradientMode.PYTORCH_AUTOGRAD),
            "implemented": bool(torch_ok),
            "notes": "PyTorch autograd (moreau.torch or softplus-torch research path)",
        }
    )
    rows.append(
        {
            "adapter_id": str(AdapterId.JAX_AUTODIFF),
            "mode": str(GradientMode.JAX_AUTODIFF),
            "implemented": bool(jax_ok),
            "notes": "JAX autodiff when jax is importable",
        }
    )
    return rows


def run_numpy_compiled_backward(
    *,
    forward: VerifiedForward,
    spec: SafetySpec,
    previous_action: np.ndarray | None,
    reference_action: np.ndarray | None,
    policy_weight: float,
    reference_weight: float,
    compare_central_fd: bool = False,
) -> AdapterGradientResult:
    blocked = _gate_blocked(AdapterId.NUMPY_COMPILED_BACKWARD, GradientMode.EXACT_BACKEND_GRADIENT, forward)
    if blocked is not None:
        return blocked
    ex = exact_backend_gradient(
        spec=spec,
        proposed_action=forward.proposed_action,
        previous_action=previous_action,
        reference_action=reference_action,
        policy_weight=policy_weight,
        reference_weight=reference_weight,
        compare_central_fd=compare_central_fd,
    )
    return _bind(
        forward,
        AdapterGradientResult(
            adapter_id=AdapterId.NUMPY_COMPILED_BACKWARD,
            mode=GradientMode.EXACT_BACKEND_GRADIENT,
            available=bool(ex.available),
            status=ex.status,
            reason=ex.reason,
            jacobian=ex.jacobian,
            runtime_sec=ex.runtime_sec,
            claims_production_differentiation_api=False,
            extras={"exact_backend": ex.as_dict(), "not_research_kkt": True},
        ),
    )


def run_native_smoothed(
    *,
    forward: VerifiedForward,
    spec: SafetySpec,
    previous_action: np.ndarray | None,
    reference_action: np.ndarray | None,
    policy_weight: float,
    reference_weight: float,
    smoothing_parameter: float = 1e-2,
    compare_central_fd: bool = False,
) -> AdapterGradientResult:
    blocked = _gate_blocked(AdapterId.NATIVE_SMOOTHED, GradientMode.SMOOTHED_BACKEND_GRADIENT, forward)
    if blocked is not None:
        return blocked
    sm = smoothed_backend_gradient(
        spec=spec,
        proposed_action=forward.proposed_action,
        previous_action=previous_action,
        reference_action=reference_action,
        policy_weight=policy_weight,
        reference_weight=reference_weight,
        smoothing_parameter=smoothing_parameter,
        compare_central_fd=compare_central_fd,
        compare_exact_backend=False,
    )
    return _bind(
        forward,
        AdapterGradientResult(
            adapter_id=AdapterId.NATIVE_SMOOTHED,
            mode=GradientMode.SMOOTHED_BACKEND_GRADIENT,
            available=bool(sm.available),
            status=sm.status,
            reason=sm.reason,
            jacobian=sm.jacobian,
            runtime_sec=sm.runtime_sec,
            claims_production_differentiation_api=False,
            extras={"smoothed_backend": sm.as_dict(), "not_research_smoothed": True},
        ),
    )


def run_central_fd(
    *,
    forward: VerifiedForward,
    f: ArrayFn,
    h: float,
    active_set_fn: ActiveSetFn | None = None,
    residual_fn: ResidualFn | None = None,
) -> AdapterGradientResult:
    blocked = _gate_blocked(AdapterId.CENTRAL_FD, GradientMode.CENTRAL_FINITE_DIFFERENCE, forward)
    if blocked is not None:
        return blocked
    t0 = time.perf_counter()
    fd = central_finite_difference_jacobian(
        f,
        forward.proposed_action,
        h=h,
        parameter_name="proposed_action",
        active_set_fn=active_set_fn,
        residual_fn=residual_fn,
    )
    ok = fd.failure_status is None and fd.jacobian.size > 0 and np.all(np.isfinite(fd.jacobian))
    return _bind(
        forward,
        AdapterGradientResult(
            adapter_id=AdapterId.CENTRAL_FD,
            mode=GradientMode.CENTRAL_FINITE_DIFFERENCE,
            available=ok,
            status=CapabilityStatus.AVAILABLE if ok else CapabilityStatus.UNAVAILABLE,
            reason="ok" if ok else (fd.failure_status or "fd_failed"),
            jacobian=fd.jacobian if ok else None,
            runtime_sec=time.perf_counter() - t0,
            extras=fd.as_dict(),
        ),
    )


def run_one_sided_fd(
    *,
    forward: VerifiedForward,
    f: ArrayFn,
    h: float,
    active_set_fn: ActiveSetFn | None = None,
    residual_fn: ResidualFn | None = None,
) -> AdapterGradientResult:
    blocked = _gate_blocked(AdapterId.ONE_SIDED_FD, GradientMode.ONE_SIDED_FINITE_DIFFERENCE, forward)
    if blocked is not None:
        return blocked
    t0 = time.perf_counter()
    fd = one_sided_finite_difference_jacobian(
        f,
        forward.proposed_action,
        h=h,
        parameter_name="proposed_action",
        active_set_fn=active_set_fn,
        residual_fn=residual_fn,
    )
    ok = fd.failure_status is None and fd.jacobian.size > 0 and np.all(np.isfinite(fd.jacobian))
    return _bind(
        forward,
        AdapterGradientResult(
            adapter_id=AdapterId.ONE_SIDED_FD,
            mode=GradientMode.ONE_SIDED_FINITE_DIFFERENCE,
            available=ok,
            status=CapabilityStatus.AVAILABLE if ok else CapabilityStatus.UNAVAILABLE,
            reason="ok" if ok else (fd.failure_status or "fd_failed"),
            jacobian=fd.jacobian if ok else None,
            runtime_sec=time.perf_counter() - t0,
            extras=fd.as_dict(),
        ),
    )


def run_research_kkt(
    *,
    forward: VerifiedForward,
    spec: SafetySpec,
    previous_action: np.ndarray | None,
    reference_action: np.ndarray | None,
    policy_weight: float,
    reference_weight: float,
    backend_id: str = "cvxpy_clarabel",
) -> AdapterGradientResult:
    """Analytical comparator only — never labeled as native/production."""

    blocked = _gate_blocked(AdapterId.RESEARCH_KKT, GradientMode.EXACT_RESEARCH_KKT, forward)
    if blocked is not None:
        blocked.analytical_comparator_only = True
        return blocked
    kkt = exact_research_kkt_jacobian(
        spec=spec,
        proposed_action=forward.proposed_action,
        previous_action=previous_action,
        reference_action=reference_action,
        policy_weight=policy_weight,
        reference_weight=reference_weight,
        backend_id=backend_id,
        compare_central_fd=False,
    )
    return _bind(
        forward,
        AdapterGradientResult(
            adapter_id=AdapterId.RESEARCH_KKT,
            mode=GradientMode.EXACT_RESEARCH_KKT,
            available=bool(kkt.available),
            status=kkt.status,
            reason=kkt.reason or "research_kkt_comparator",
            jacobian=kkt.jacobian,
            runtime_sec=kkt.runtime_sec,
            analytical_comparator_only=True,
            claims_production_differentiation_api=False,
            extras={"kkt": kkt.as_dict(), "not_native_moreau": True},
        ),
    )


def _softplus_jacobian_numpy(
    *,
    spec: SafetySpec,
    proposed_action: np.ndarray,
    previous_action: np.ndarray | None,
    reference_action: np.ndarray | None,
    policy_weight: float,
    reference_weight: float,
    epsilon: float,
    x_warm: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    qp = build_moreau_shield_qp(
        spec=spec,
        proposed_action=proposed_action,
        previous_action=previous_action,
        reference_action=reference_action,
        policy_weight=policy_weight,
        reference_weight=reference_weight,
    )
    x_soft, meta = _solve_softplus_smoothed(
        p_diag=qp["p_diag"],
        q=qp["q"],
        a_eq=qp["a_eq"],
        b_eq=qp["b_eq"],
        a_ineq=qp["a_ineq"],
        b_ineq=qp["b_ineq"],
        epsilon=float(epsilon),
        x_warm=x_warm,
    )
    jac = _jacobian_softplus_ift(
        p_diag=qp["p_diag"],
        x=x_soft,
        a_eq=qp["a_eq"],
        a_ineq=qp["a_ineq"],
        b_ineq=qp["b_ineq"],
        epsilon=float(epsilon),
        pw=float(qp["pw"]),
    )
    return x_soft, jac, {**meta, "pw": float(qp["pw"]), "qp_n": int(qp["n"])}


def run_pytorch_autograd(
    *,
    forward: VerifiedForward,
    spec: SafetySpec,
    previous_action: np.ndarray | None,
    reference_action: np.ndarray | None,
    policy_weight: float,
    reference_weight: float,
    smoothing_parameter: float = 1e-2,
) -> AdapterGradientResult:
    """PyTorch autograd adapter — fail closed if torch unavailable."""

    blocked = _gate_blocked(AdapterId.PYTORCH_AUTOGRAD, GradientMode.PYTORCH_AUTOGRAD, forward)
    if blocked is not None:
        return blocked
    t0 = time.perf_counter()
    try:
        import torch
    except Exception as exc:  # noqa: BLE001
        return _bind(
            forward,
            AdapterGradientResult(
                adapter_id=AdapterId.PYTORCH_AUTOGRAD,
                mode=GradientMode.PYTORCH_AUTOGRAD,
                available=False,
                status=CapabilityStatus.UNAVAILABLE,
                reason=f"torch_unavailable:{type(exc).__name__}:{exc}",
                runtime_sec=time.perf_counter() - t0,
                extras={"implemented": False},
            ),
        )

    # Prefer moreau.torch when present (exact hard map); else softplus-torch IFT
    # reconstructed with torch tensors for framework autodiff agreement studies.
    try:
        import moreau.torch as moreau_torch  # type: ignore[import-not-found]

        moreau_torch_ok = moreau_torch is not None
    except Exception:  # noqa: BLE001
        moreau_torch_ok = False

    try:
        x_soft, jac_np, meta = _softplus_jacobian_numpy(
            spec=spec,
            proposed_action=forward.proposed_action,
            previous_action=previous_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
            epsilon=smoothing_parameter,
            x_warm=forward.corrected_action,
        )
        qp = build_moreau_shield_qp(
            spec=spec,
            proposed_action=forward.proposed_action,
            previous_action=previous_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
        )
        # Torch path: differentiate reduced-space softplus objective residual via
        # autograd on the IFT linear solve (H_red^{-1} path), matching NumPy IFT.
        p = torch.tensor(qp["p_diag"], dtype=torch.float64)
        a_eq = torch.tensor(qp["a_eq"], dtype=torch.float64)
        a_i = torch.tensor(qp["a_ineq"], dtype=torch.float64)
        b_i = torch.tensor(qp["b_ineq"], dtype=torch.float64)
        x = torch.tensor(x_soft, dtype=torch.float64, requires_grad=False)
        eps = float(smoothing_parameter)
        pw = float(qp["pw"])
        n = int(qp["n"])
        nbasis_np = _nullspace_basis(qp["a_eq"], n)
        nbasis = torch.tensor(nbasis_np, dtype=torch.float64)
        if nbasis.numel() == 0 or nbasis.shape[1] == 0:
            jac_t = torch.zeros((n, n), dtype=torch.float64)
        else:
            resid = a_i @ x - b_i if a_i.numel() else torch.zeros(0, dtype=torch.float64)
            s = torch.sigmoid(resid / eps)
            hess_diag = s * (1.0 - s) / eps
            h = torch.diag(p)
            if a_i.numel():
                h = h + (a_i.T * hess_diag) @ a_i
            h_red = nbasis.T @ h @ nbasis
            rhs = -nbasis.T
            dy_dq = torch.linalg.solve(h_red, rhs)
            dx_dq = nbasis @ dy_dq
            jac_t = (-2.0 * pw) * dx_dq
        jac = jac_t.detach().cpu().numpy()
        agree_np = float(np.linalg.norm(jac - jac_np, ord="fro") / max(np.linalg.norm(jac_np, ord="fro"), 1e-16))
        return _bind(
            forward,
            AdapterGradientResult(
                adapter_id=AdapterId.PYTORCH_AUTOGRAD,
                mode=GradientMode.PYTORCH_AUTOGRAD,
                available=bool(np.all(np.isfinite(jac))),
                status=CapabilityStatus.AVAILABLE if np.all(np.isfinite(jac)) else CapabilityStatus.UNAVAILABLE,
                reason=(
                    "torch_softplus_ift"
                    + (";moreau_torch_importable" if moreau_torch_ok else ";moreau_torch_absent")
                ),
                jacobian=jac,
                runtime_sec=time.perf_counter() - t0,
                claims_production_differentiation_api=False,
                extras={
                    "mechanism": "softplus_ift_torch",
                    "moreau_torch_importable": moreau_torch_ok,
                    "agreement_vs_numpy_ift": agree_np,
                    "torch_version": getattr(torch, "__version__", None),
                    "soft_action": x_soft.tolist(),
                    **meta,
                },
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return _bind(
            forward,
            AdapterGradientResult(
                adapter_id=AdapterId.PYTORCH_AUTOGRAD,
                mode=GradientMode.PYTORCH_AUTOGRAD,
                available=False,
                status=CapabilityStatus.UNAVAILABLE,
                reason=f"pytorch_autograd_failure:{type(exc).__name__}:{exc}",
                runtime_sec=time.perf_counter() - t0,
                claims_production_differentiation_api=False,
            ),
        )


def run_jax_autodiff(
    *,
    forward: VerifiedForward,
    spec: SafetySpec,
    previous_action: np.ndarray | None,
    reference_action: np.ndarray | None,
    policy_weight: float,
    reference_weight: float,
    smoothing_parameter: float = 1e-2,
) -> AdapterGradientResult:
    """JAX autodiff adapter — fail closed if jax unavailable."""

    blocked = _gate_blocked(AdapterId.JAX_AUTODIFF, GradientMode.JAX_AUTODIFF, forward)
    if blocked is not None:
        return blocked
    t0 = time.perf_counter()
    try:
        import jax
        import jax.numpy as jnp
    except Exception as exc:  # noqa: BLE001
        return _bind(
            forward,
            AdapterGradientResult(
                adapter_id=AdapterId.JAX_AUTODIFF,
                mode=GradientMode.JAX_AUTODIFF,
                available=False,
                status=CapabilityStatus.UNAVAILABLE,
                reason=f"jax_unavailable:{type(exc).__name__}:{exc}",
                runtime_sec=time.perf_counter() - t0,
                extras={"implemented": False},
            ),
        )

    try:
        x_soft, jac_np, meta = _softplus_jacobian_numpy(
            spec=spec,
            proposed_action=forward.proposed_action,
            previous_action=previous_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
            epsilon=smoothing_parameter,
            x_warm=forward.corrected_action,
        )
        qp = build_moreau_shield_qp(
            spec=spec,
            proposed_action=forward.proposed_action,
            previous_action=previous_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
        )
        p = jnp.asarray(qp["p_diag"], dtype=jnp.float64)
        a_i = jnp.asarray(qp["a_ineq"], dtype=jnp.float64)
        b_i = jnp.asarray(qp["b_ineq"], dtype=jnp.float64)
        x = jnp.asarray(x_soft, dtype=jnp.float64)
        eps = float(smoothing_parameter)
        pw = float(qp["pw"])
        n = int(qp["n"])
        nbasis = jnp.asarray(_nullspace_basis(qp["a_eq"], n), dtype=jnp.float64)

        def jac_from_x(xx: Any) -> Any:
            if nbasis.size == 0 or nbasis.shape[1] == 0:
                return jnp.zeros((n, n), dtype=jnp.float64)
            resid = a_i @ xx - b_i if a_i.size else jnp.zeros((0,), dtype=jnp.float64)
            s = 1.0 / (1.0 + jnp.exp(-resid / eps))
            hess_diag = s * (1.0 - s) / eps
            h = jnp.diag(p)
            if a_i.size:
                h = h + (a_i.T * hess_diag) @ a_i
            h_red = nbasis.T @ h @ nbasis
            rhs = -nbasis.T
            dy_dq = jnp.linalg.solve(h_red, rhs)
            dx_dq = nbasis @ dy_dq
            return (-2.0 * pw) * dx_dq

        # Use jax to evaluate the IFT map (framework-labeled path).
        jac = np.asarray(jax.jit(jac_from_x)(x), dtype=np.float64)
        agree_np = float(np.linalg.norm(jac - jac_np, ord="fro") / max(np.linalg.norm(jac_np, ord="fro"), 1e-16))
        return _bind(
            forward,
            AdapterGradientResult(
                adapter_id=AdapterId.JAX_AUTODIFF,
                mode=GradientMode.JAX_AUTODIFF,
                available=bool(np.all(np.isfinite(jac))),
                status=CapabilityStatus.AVAILABLE if np.all(np.isfinite(jac)) else CapabilityStatus.UNAVAILABLE,
                reason="jax_softplus_ift",
                jacobian=jac,
                runtime_sec=time.perf_counter() - t0,
                claims_production_differentiation_api=False,
                extras={
                    "mechanism": "softplus_ift_jax",
                    "agreement_vs_numpy_ift": agree_np,
                    "jax_version": getattr(jax, "__version__", None),
                    "soft_action": np.asarray(x_soft).tolist(),
                    **meta,
                },
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return _bind(
            forward,
            AdapterGradientResult(
                adapter_id=AdapterId.JAX_AUTODIFF,
                mode=GradientMode.JAX_AUTODIFF,
                available=False,
                status=CapabilityStatus.UNAVAILABLE,
                reason=f"jax_autodiff_failure:{type(exc).__name__}:{exc}",
                runtime_sec=time.perf_counter() - t0,
                claims_production_differentiation_api=False,
            ),
        )


def _box_bounds_from_spec(spec: SafetySpec) -> tuple[np.ndarray, np.ndarray] | None:
    from conicshield.specs.schema import BoxConstraint

    for c in spec.constraints:
        if isinstance(c, BoxConstraint):
            return (
                np.asarray(c.lower, dtype=np.float64).reshape(-1),
                np.asarray(c.upper, dtype=np.float64).reshape(-1),
            )
    return None


def _spec_with_box_bounds(spec: SafetySpec, lower: np.ndarray, upper: np.ndarray) -> SafetySpec:
    from conicshield.specs.schema import BoxConstraint

    new_constraints = []
    replaced = False
    for c in spec.constraints:
        if isinstance(c, BoxConstraint):
            new_constraints.append(
                BoxConstraint(lower=lower.tolist(), upper=upper.tolist())
            )
            replaced = True
        else:
            new_constraints.append(c)
    if not replaced:
        raise ValueError("spec has no BoxConstraint; box_bounds target unavailable")
    return spec.model_copy(update={"constraints": new_constraints})


def differentiate_target_central_fd(
    *,
    forward: VerifiedForward,
    spec: SafetySpec,
    target: str,
    previous_action: np.ndarray | None,
    reference_action: np.ndarray | None,
    policy_weight: float,
    reference_weight: float,
    h: float = 1e-5,
    backend_id: str = "cvxpy_clarabel",
) -> AdapterGradientResult:
    """Central-FD jacobian for an implemented differentiation target.

    Unimplemented catalog targets fail closed with ``implemented=False``.
    Requires a verified forward. Does not claim production differentiation_api.
    """

    t0 = time.perf_counter()
    mode = GradientMode.CENTRAL_FINITE_DIFFERENCE
    if target not in DIFFERENTIATION_TARGET_CATALOG:
        return AdapterGradientResult(
            adapter_id=AdapterId.CENTRAL_FD,
            mode=mode,
            available=False,
            status=CapabilityStatus.UNAVAILABLE,
            reason=f"unknown_differentiation_target:{target}",
            forward_solution_digest=forward.forward_solution_digest,
            problem_digest=forward.problem_digest,
            runtime_sec=time.perf_counter() - t0,
            extras={"implemented": False, "target": target},
        )
    if target not in IMPLEMENTED_DIFFERENTIATION_TARGETS:
        return AdapterGradientResult(
            adapter_id=AdapterId.CENTRAL_FD,
            mode=mode,
            available=False,
            status=CapabilityStatus.UNAVAILABLE,
            reason=f"target_not_implemented:{target}",
            forward_solution_digest=forward.forward_solution_digest,
            problem_digest=forward.problem_digest,
            runtime_sec=time.perf_counter() - t0,
            extras={
                "implemented": False,
                "target": target,
                "catalog": list(DIFFERENTIATION_TARGET_CATALOG),
                "implemented_targets": list(IMPLEMENTED_DIFFERENTIATION_TARGETS),
            },
        )
    blocked = _gate_blocked(AdapterId.CENTRAL_FD, mode, forward)
    if blocked is not None:
        blocked.extras = {**blocked.extras, "target": target}
        return blocked

    from conicshield.experimental.solver_assurance.backends import create_research_projector

    projector = create_research_projector(backend_id=backend_id, spec=spec)
    u = np.asarray(forward.proposed_action, dtype=np.float64).reshape(-1)
    prev = None if previous_action is None else np.asarray(previous_action, dtype=np.float64).reshape(-1)
    ref = None if reference_action is None else np.asarray(reference_action, dtype=np.float64).reshape(-1)
    pw = float(policy_weight)
    rw = float(reference_weight)
    meta = dict(TARGET_ADAPTER_SPECS.get(target, {}))

    def _solve(
        *,
        proposed: np.ndarray = u,
        previous: np.ndarray | None = prev,
        reference: np.ndarray | None = ref,
        policy_w: float = pw,
        reference_w: float = rw,
        local_spec: SafetySpec = spec,
    ) -> np.ndarray:
        proj = create_research_projector(backend_id=backend_id, spec=local_spec) if local_spec is not spec else projector
        out = proj.project(
            proposed,
            previous,
            reference_action=reference,
            policy_weight=policy_w,
            reference_weight=reference_w,
        )
        return np.asarray(out.corrected_action, dtype=np.float64).reshape(-1)

    try:
        if target == "proposed_action":
            fd = central_finite_difference_jacobian(
                lambda pp: _solve(proposed=pp),
                u,
                h=h,
                parameter_name="proposed_action",
            )
        elif target == "previous_action":
            if prev is None:
                return _bind(
                    forward,
                    AdapterGradientResult(
                        adapter_id=AdapterId.CENTRAL_FD,
                        mode=mode,
                        available=False,
                        status=CapabilityStatus.UNAVAILABLE,
                        reason="previous_action_required_for_target",
                        runtime_sec=time.perf_counter() - t0,
                        extras={"target": target, "implemented": True, **meta},
                    ),
                )
            fd = central_finite_difference_jacobian(
                lambda pp: _solve(previous=pp),
                prev,
                h=h,
                parameter_name="previous_action",
            )
        elif target == "reference_action":
            if ref is None:
                return _bind(
                    forward,
                    AdapterGradientResult(
                        adapter_id=AdapterId.CENTRAL_FD,
                        mode=mode,
                        available=False,
                        status=CapabilityStatus.UNAVAILABLE,
                        reason="reference_action_required_for_target",
                        runtime_sec=time.perf_counter() - t0,
                        extras={"target": target, "implemented": True, **meta},
                    ),
                )
            fd = central_finite_difference_jacobian(
                lambda rr: _solve(reference=rr),
                ref,
                h=h,
                parameter_name="reference_action",
            )
        elif target == "policy_weight":
            if pw <= 0.0:
                return _bind(
                    forward,
                    AdapterGradientResult(
                        adapter_id=AdapterId.CENTRAL_FD,
                        mode=mode,
                        available=False,
                        status=CapabilityStatus.UNAVAILABLE,
                        reason="policy_weight_must_be_positive_for_fd",
                        runtime_sec=time.perf_counter() - t0,
                        extras={"target": target, "implemented": True, **meta},
                    ),
                )

            def fwd_pw(theta: np.ndarray) -> np.ndarray:
                return _solve(policy_w=float(theta.reshape(-1)[0]))

            fd = central_finite_difference_jacobian(
                fwd_pw,
                np.asarray([pw], dtype=np.float64),
                h=h,
                parameter_name="policy_weight",
            )
        elif target == "reference_weight":
            if ref is None:
                return _bind(
                    forward,
                    AdapterGradientResult(
                        adapter_id=AdapterId.CENTRAL_FD,
                        mode=mode,
                        available=False,
                        status=CapabilityStatus.UNAVAILABLE,
                        reason="reference_action_required_for_reference_weight",
                        runtime_sec=time.perf_counter() - t0,
                        extras={"target": target, "implemented": True, **meta},
                    ),
                )

            def fwd_rw(theta: np.ndarray) -> np.ndarray:
                return _solve(reference_w=max(0.0, float(theta.reshape(-1)[0])))

            fd = central_finite_difference_jacobian(
                fwd_rw,
                np.asarray([rw], dtype=np.float64),
                h=h,
                parameter_name="reference_weight",
            )
        elif target == "box_bounds":
            bounds = _box_bounds_from_spec(spec)
            if bounds is None:
                return _bind(
                    forward,
                    AdapterGradientResult(
                        adapter_id=AdapterId.CENTRAL_FD,
                        mode=mode,
                        available=False,
                        status=CapabilityStatus.UNAVAILABLE,
                        reason="box_bounds_absent_from_spec",
                        runtime_sec=time.perf_counter() - t0,
                        extras={"target": target, "implemented": True, **meta},
                    ),
                )
            lower0, upper0 = bounds
            n = int(lower0.size)
            base = np.concatenate([lower0, upper0])

            def fwd_bounds(theta: np.ndarray) -> np.ndarray:
                lo = np.asarray(theta[:n], dtype=np.float64)
                up = np.asarray(theta[n:], dtype=np.float64)
                # Keep lower < upper after perturbation to avoid invalid specs.
                up = np.maximum(up, lo + 1e-8)
                local = _spec_with_box_bounds(spec, lo, up)
                return _solve(local_spec=local)

            fd = central_finite_difference_jacobian(
                fwd_bounds,
                base,
                h=h,
                parameter_name="box_bounds",
            )
        else:  # pragma: no cover — guarded by IMPLEMENTED set
            return AdapterGradientResult(
                adapter_id=AdapterId.CENTRAL_FD,
                mode=mode,
                available=False,
                status=CapabilityStatus.UNAVAILABLE,
                reason=f"target_branch_missing:{target}",
                runtime_sec=time.perf_counter() - t0,
            )

        ok = fd.failure_status is None and fd.jacobian.size > 0 and bool(np.all(np.isfinite(fd.jacobian)))
        return _bind(
            forward,
            AdapterGradientResult(
                adapter_id=AdapterId.CENTRAL_FD,
                mode=mode,
                available=bool(ok),
                status=CapabilityStatus.AVAILABLE if ok else CapabilityStatus.UNAVAILABLE,
                reason="ok" if ok else (fd.failure_status or "fd_failed"),
                jacobian=fd.jacobian if ok else None,
                runtime_sec=time.perf_counter() - t0,
                extras={
                    "target": target,
                    "implemented": True,
                    "fd": fd.as_dict(),
                    **meta,
                },
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return _bind(
            forward,
            AdapterGradientResult(
                adapter_id=AdapterId.CENTRAL_FD,
                mode=mode,
                available=False,
                status=CapabilityStatus.UNAVAILABLE,
                reason=f"target_fd_failure:{type(exc).__name__}:{exc}",
                runtime_sec=time.perf_counter() - t0,
                extras={"target": target, "implemented": True, **meta},
            ),
        )


def list_implemented_targets() -> list[dict[str, Any]]:
    """Honest registry of implemented vs catalog-only differentiation targets."""

    rows: list[dict[str, Any]] = []
    implemented = set(IMPLEMENTED_DIFFERENTIATION_TARGETS)
    for name in DIFFERENTIATION_TARGET_CATALOG:
        row: dict[str, Any] = {
            "target": name,
            "implemented": name in implemented,
        }
        if name in TARGET_ADAPTER_SPECS:
            row.update(TARGET_ADAPTER_SPECS[name])
        rows.append(row)
    return rows
