"""Native exact backend gradient via Moreau ``CompiledSolver.backward``.

Mode: ``exact_backend_gradient`` — distinct from ``exact_research_kkt``.

Uses vendor ``Settings(enable_grad=True)`` + ``CompiledSolver.backward`` VJP
to assemble ``dx/du`` for the shield projection map. Fail-closed on assumption
violations. Does **not** alter production ``BackendCapabilities.differentiation_api``
(which still probes ``differentiate`` / ``DiffSettings`` / ``cvxpylayers``).

Research attestation treats ``CompiledSolver.backward`` + ``enable_grad`` as the
live differentiation surface even while the production identity flag stays false.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.experimental.gradients.capability import CapabilityStatus
from conicshield.experimental.gradients.modes import GradientMode
from conicshield.specs.schema import SafetySpec

_FD_AGREE_FAIL = 1e-2


@dataclass(slots=True)
class ExactBackendGradientResult:
    mode: GradientMode = GradientMode.EXACT_BACKEND_GRADIENT
    available: bool = False
    status: CapabilityStatus = CapabilityStatus.UNAVAILABLE
    reason: str = ""
    jacobian: np.ndarray | None = None
    agreement_vs_central_fd: float | None = None
    runtime_sec: float | None = None
    assumptions: tuple[str, ...] = (
        "Moreau CompiledSolver.backward with Settings(enable_grad=True).",
        "Shield objective q = -2*pw*u - 2*rw*r; dx/du = -2*pw * dx/dq.",
        "Not exact_research_kkt; not smoothed_backend_gradient.",
    )
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": str(self.mode),
            "available": self.available,
            "status": str(self.status),
            "reason": self.reason,
            "jacobian": None if self.jacobian is None else self.jacobian.tolist(),
            "agreement_vs_central_fd": self.agreement_vs_central_fd,
            "runtime_sec": self.runtime_sec,
            "assumptions": list(self.assumptions),
            "extras": dict(self.extras),
            "not_research_kkt": True,
        }


def _probe_vendor_compiled_backward() -> dict[str, Any]:
    """Experimental probe — does not mutate production capability discovery."""

    import sys

    out: dict[str, Any] = {
        "package_importable": False,
        "native_compiled_api": False,
        "compiled_solver_backward": False,
        "settings_enable_grad": False,
        "identity_differentiation_api": False,
        "vendor_compiled_backward_api": False,
        "research_differentiation_surface": False,
        "windows_native_unsupported": sys.platform == "win32",
        "symbols_searched": [
            "moreau.differentiate",
            "moreau.DiffSettings",
            "moreau.cvxpylayers",
            "moreau.CompiledSolver.backward",
            "moreau.Settings.enable_grad",
            "moreau.torch (optional; requires torch)",
            "moreau.jax (optional; requires jax)",
        ],
    }
    if sys.platform == "win32":
        out["missing_evidence"] = [
            "vendor Moreau executable on native Windows "
            "(use WSL/Linux for CompiledSolver.backward)"
        ]
        return out

    try:
        import moreau
    except Exception as exc:  # noqa: BLE001
        out["probe_error"] = f"{type(exc).__name__}: {exc}"
        out["missing_evidence"] = ["moreau package importable"]
        return out

    out["package_importable"] = True
    out["moreau_version"] = getattr(moreau, "__version__", None)
    out["identity_differentiation_api"] = bool(
        hasattr(moreau, "differentiate")
        or hasattr(moreau, "DiffSettings")
        or hasattr(moreau, "cvxpylayers")
    )
    cs = getattr(moreau, "CompiledSolver", None)
    out["native_compiled_api"] = cs is not None
    out["compiled_solver_backward"] = bool(
        cs is not None and callable(getattr(cs, "backward", None))
    )
    settings_cls = getattr(moreau, "Settings", None)
    enable_grad = False
    if settings_cls is not None:
        try:
            s = settings_cls(enable_grad=True)
            enable_grad = bool(getattr(s, "enable_grad", False))
        except Exception as exc:  # noqa: BLE001
            out["settings_enable_grad_error"] = f"{type(exc).__name__}: {exc}"
    out["settings_enable_grad"] = enable_grad
    out["vendor_compiled_backward_api"] = bool(
        out["compiled_solver_backward"] and out["settings_enable_grad"]
    )
    # Research surface: backward+enable_grad is the live API on Moreau 0.3.x.
    out["research_differentiation_surface"] = bool(out["vendor_compiled_backward_api"])
    # Production identity flag name stays honest and separate.
    out["differentiation_api"] = bool(out["identity_differentiation_api"])
    out["moreau_torch_importable"] = False
    out["moreau_jax_importable"] = False
    try:
        import importlib

        importlib.import_module("moreau.torch")
        out["moreau_torch_importable"] = True
    except Exception as exc:  # noqa: BLE001
        out["moreau_torch_import_error"] = f"{type(exc).__name__}: {exc}"
    try:
        import importlib

        importlib.import_module("moreau.jax")
        out["moreau_jax_importable"] = True
    except Exception as exc:  # noqa: BLE001
        out["moreau_jax_import_error"] = f"{type(exc).__name__}: {exc}"

    missing: list[str] = []
    if not out["vendor_compiled_backward_api"]:
        missing.append("CompiledSolver.backward + Settings(enable_grad=True)")
    if not out["identity_differentiation_api"]:
        missing.append(
            "production identity symbols moreau.differentiate|DiffSettings|cvxpylayers "
            "(still absent; experimental path uses CompiledSolver.backward instead)"
        )
    out["missing_evidence"] = missing
    return out


def _fail(
    reason: str,
    *,
    status: CapabilityStatus,
    extras: dict[str, Any] | None = None,
    runtime_sec: float | None = None,
) -> ExactBackendGradientResult:
    return ExactBackendGradientResult(
        available=False,
        status=status,
        reason=reason,
        runtime_sec=runtime_sec,
        extras=dict(extras or {}),
    )


def _extract_dq(backward_out: Any, *, n: int, batch: int = 1) -> np.ndarray:
    if isinstance(backward_out, dict):
        if "dq" not in backward_out:
            raise RuntimeError("CompiledSolver.backward dict missing 'dq'")
        dq = np.asarray(backward_out["dq"], dtype=np.float64)
    elif hasattr(backward_out, "dq"):
        dq = np.asarray(backward_out.dq, dtype=np.float64)
    else:
        dq = np.asarray(backward_out, dtype=np.float64)
    dq = dq.reshape(batch, n) if dq.size == batch * n else dq.reshape(-1, n)
    if dq.shape[-1] != n:
        raise RuntimeError(f"unexpected dq shape {dq.shape} for n={n}")
    return dq


def _csr_to_dense_rows(
    indptr: np.ndarray,
    indices: np.ndarray,
    values: np.ndarray,
    *,
    m: int,
    n: int,
) -> np.ndarray:
    dense = np.zeros((m, n), dtype=np.float64)
    for r in range(m):
        start = int(indptr[r])
        end = int(indptr[r + 1])
        for k in range(start, end):
            dense[r, int(indices[k])] = float(values[k])
    return dense


def build_moreau_shield_qp(
    *,
    spec: SafetySpec,
    proposed_action: np.ndarray,
    previous_action: np.ndarray | None,
    reference_action: np.ndarray | None,
    policy_weight: float,
    reference_weight: float,
) -> dict[str, Any]:
    """Compile + fill the native Moreau shield QP; shared by exact/smoothed backends."""

    from conicshield.compilation.compiled_template import CompiledShieldTemplate
    from conicshield.specs.shield_qp import (
        parse_safety_spec_for_shield,
        validate_objective_weights,
    )

    data = parse_safety_spec_for_shield(spec)
    tmpl = CompiledShieldTemplate.compile(data)
    buf = tmpl.allocate_buffers()
    pw, rw = validate_objective_weights(
        float(policy_weight),
        float(reference_weight),
        reference_present=reference_action is not None,
    )
    u = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
    prev = None if previous_action is None else np.asarray(previous_action, dtype=np.float64)
    ref = None if reference_action is None else np.asarray(reference_action, dtype=np.float64)
    tmpl.fill(buf, data, u, prev, ref, policy_weight=pw, reference_weight=rw)
    n = int(tmpl.layout.n)
    m = int(tmpl.layout.m)
    n_eq = int(tmpl.topology.num_zero_cones)
    a_dense = _csr_to_dense_rows(
        tmpl.a_indptr, tmpl.a_indices, buf.a_values, m=m, n=n
    )
    return {
        "data": data,
        "tmpl": tmpl,
        "buf": buf,
        "pw": pw,
        "rw": rw,
        "u": u,
        "prev": prev,
        "ref": ref,
        "n": n,
        "m": m,
        "n_eq": n_eq,
        "p_diag": np.asarray(buf.p_values, dtype=np.float64).copy(),
        "q": np.asarray(buf.q, dtype=np.float64).copy(),
        "b": np.asarray(buf.b, dtype=np.float64).copy(),
        "a_dense": a_dense,
        "a_eq": a_dense[:n_eq].copy(),
        "b_eq": np.asarray(buf.b[:n_eq], dtype=np.float64).copy(),
        "a_ineq": a_dense[n_eq:].copy(),
        "b_ineq": np.asarray(buf.b[n_eq:], dtype=np.float64).copy(),
    }


def solve_moreau_compiled(
    qp: dict[str, Any],
    *,
    enable_grad: bool,
    max_iter: int = 200,
) -> tuple[Any, Any, np.ndarray]:
    """Construct Moreau CompiledSolver, solve, return (moreau, solver, x)."""

    import moreau

    tmpl = qp["tmpl"]
    buf = qp["buf"]
    settings = moreau.Settings(
        device="cpu",
        batch_size=1,
        enable_grad=bool(enable_grad),
        max_iter=int(max_iter),
        verbose=False,
        auto_tune=False,
    )
    if enable_grad and not bool(getattr(settings, "enable_grad", False)):
        raise RuntimeError("Settings(enable_grad=True) did not stick")
    solver = moreau.CompiledSolver(
        n=int(tmpl.layout.n),
        m=int(tmpl.layout.m),
        P_row_offsets=np.asarray(tmpl.p_indptr, dtype=np.int32),
        P_col_indices=np.asarray(tmpl.p_indices, dtype=np.int32),
        A_row_offsets=np.asarray(tmpl.a_indptr, dtype=np.int32),
        A_col_indices=np.asarray(tmpl.a_indices, dtype=np.int32),
        cones=tmpl.moreau_cones(moreau),
        settings=settings,
    )
    solver.setup(buf.p_values, buf.a_values)
    sol = solver.solve([buf.q.copy()], [buf.b.copy()])
    x = np.asarray(sol.x, dtype=np.float64).reshape(-1)
    return moreau, solver, x


def exact_backend_gradient(
    *args: Any,
    spec: SafetySpec | None = None,
    proposed_action: np.ndarray | None = None,
    previous_action: np.ndarray | None = None,
    reference_action: np.ndarray | None = None,
    policy_weight: float = 1.0,
    reference_weight: float = 0.0,
    compare_central_fd: bool = True,
    fd_h: float = 1e-6,
    max_iter: int = 200,
    **kwargs: Any,
) -> ExactBackendGradientResult:
    """Native exact jacobian via Moreau ``CompiledSolver.backward``, or fail closed.

    Call with no problem data to probe capability. With ``spec`` + ``proposed_action``,
    attempts a live VJP-assembled jacobian. Never aliases to ``exact_research_kkt``.
    """

    del args, kwargs
    caps = _probe_vendor_compiled_backward()
    if spec is None or proposed_action is None:
        if caps.get("vendor_compiled_backward_api"):
            return ExactBackendGradientResult(
                available=False,
                status=CapabilityStatus.UNAVAILABLE,
                reason=(
                    "vendor CompiledSolver.backward API present, but no problem data "
                    "supplied; fail closed (not a live jacobian)."
                ),
                extras={
                    **caps,
                    "gap_vs_exact_research_kkt": (
                        "Capability alone is not a live native gradient."
                    ),
                    "missing_evidence": [
                        "live native exact jacobian sample with SafetySpec + actions"
                    ],
                },
            )
        return ExactBackendGradientResult(
            available=False,
            status=CapabilityStatus.UNAVAILABLE,
            reason=(
                "exact_backend_gradient requires Moreau CompiledSolver.backward; "
                "unavailable on this host."
            ),
            extras={
                **caps,
                "gap_vs_exact_research_kkt": (
                    "Research KKT linearizes the public QP active-set system; "
                    "native exact_backend_gradient uses Moreau CompiledSolver.backward. "
                    f"vendor_compiled_backward_api={caps.get('vendor_compiled_backward_api')}"
                ),
            },
        )

    if not caps.get("vendor_compiled_backward_api"):
        reason = (
            "Moreau unsupported on native Windows; use WSL/Linux for "
            "CompiledSolver.backward."
            if caps.get("windows_native_unsupported")
            else (
                "vendor CompiledSolver.backward / Settings(enable_grad=True) unavailable "
                "on this host; fail closed."
            )
        )
        return _fail(
            reason,
            status=CapabilityStatus.UNAVAILABLE,
            extras={**caps, "missing_evidence": caps.get("missing_evidence", [])},
        )

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
                "policy_weight must be > 0 for dx/du = -2*pw*dx/dq mapping",
                status=CapabilityStatus.UNAVAILABLE,
                extras={**caps, "policy_weight": pw},
                runtime_sec=time.perf_counter() - t0,
            )

        moreau, solver, x = solve_moreau_compiled(qp, enable_grad=True, max_iter=max_iter)
        n = int(qp["n"])
        if x.size != n or not np.all(np.isfinite(x)):
            return _fail(
                "forward_solve_non_finite_or_shape_mismatch",
                status=CapabilityStatus.UNAVAILABLE,
                extras={**caps, "x": x.tolist()},
                runtime_sec=time.perf_counter() - t0,
            )

        j_xq = np.zeros((n, n), dtype=np.float64)
        for i in range(n):
            dx = np.zeros((1, n), dtype=np.float64)
            dx[0, i] = 1.0
            try:
                bout = solver.backward(dx)
            except TypeError:
                bout = solver.backward(dx.reshape(-1))
            dq = _extract_dq(bout, n=n, batch=1)
            j_xq[i, :] = dq[0]
            if not np.all(np.isfinite(j_xq[i])):
                return _fail(
                    f"non_finite_vjp_row_{i}",
                    status=CapabilityStatus.UNAVAILABLE,
                    extras=caps,
                    runtime_sec=time.perf_counter() - t0,
                )

        jac = (-2.0 * pw) * j_xq

        agree: float | None = None
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
            u = qp["u"]
            rw = float(qp["rw"])

            def forward(pp: np.ndarray) -> np.ndarray:
                b2 = tmpl.allocate_buffers()
                tmpl.fill(
                    b2,
                    data,
                    pp,
                    prev,
                    ref,
                    policy_weight=pw,
                    reference_weight=rw,
                )
                solver.setup(b2.p_values, b2.a_values)
                s2 = solver.solve([b2.q.copy()], [b2.b.copy()])
                return np.asarray(s2.x, dtype=np.float64).reshape(-1)

            fd = central_finite_difference_jacobian(
                forward, u, h=float(fd_h), parameter_name="proposed_action"
            )
            fd_extras = {
                "fd_failure_status": fd.failure_status,
                "fd_active_set_changed": fd.active_set_changed,
            }
            if fd.failure_status is not None:
                return _fail(
                    f"fd_comparison_failed:{fd.failure_status}",
                    status=CapabilityStatus.UNAVAILABLE,
                    extras={**caps, **fd_extras},
                    runtime_sec=time.perf_counter() - t0,
                )
            if fd.active_set_changed:
                return _fail(
                    "active_set_change_under_fd_probe",
                    status=CapabilityStatus.UNAVAILABLE,
                    extras={**caps, **fd_extras},
                    runtime_sec=time.perf_counter() - t0,
                )
            if fd.jacobian.shape != jac.shape:
                return _fail(
                    "fd_jacobian_shape_mismatch",
                    status=CapabilityStatus.UNAVAILABLE,
                    extras={**caps, **fd_extras},
                    runtime_sec=time.perf_counter() - t0,
                )
            agree = fd_agreement_metric(jac, fd.jacobian)
            if not np.isfinite(agree) or agree > _FD_AGREE_FAIL:
                return _fail(
                    f"fd_agreement_exceeded:{agree}",
                    status=CapabilityStatus.UNAVAILABLE,
                    extras={
                        **caps,
                        **fd_extras,
                        "agreement_vs_central_fd": agree,
                        "threshold": _FD_AGREE_FAIL,
                    },
                    runtime_sec=time.perf_counter() - t0,
                )

        return ExactBackendGradientResult(
            available=True,
            status=CapabilityStatus.AVAILABLE,
            reason=(
                "Native Moreau CompiledSolver.backward VJP assembled into dx/du "
                "(experimental; production differentiation_api flag unchanged)."
            ),
            jacobian=jac,
            agreement_vs_central_fd=agree,
            runtime_sec=time.perf_counter() - t0,
            extras={
                **caps,
                **fd_extras,
                "corrected_action": x.tolist(),
                "policy_weight": pw,
                "reference_weight": float(qp["rw"]),
                "moreau_version": getattr(moreau, "__version__", None),
            },
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(
            f"native_backward_failure:{type(exc).__name__}:{exc}",
            status=CapabilityStatus.UNAVAILABLE,
            extras=caps,
            runtime_sec=time.perf_counter() - t0,
        )

