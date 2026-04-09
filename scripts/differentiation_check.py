#!/usr/bin/env python3
"""Layer F: finite-difference sanity on the reference projector; optional native FD; extras probe."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions
from conicshield.core.solver_factory import Backend, create_projector
from conicshield.specs.compiler import SolverOptions
from conicshield.specs.schema import (
    BoxConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)


def _spec() -> SafetySpec:
    return SafetySpec(
        spec_id="diff/minimal",
        version="0.1.0",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[0, 1, 2, 3]),
            BoxConstraint(lower=[0.0] * 4, upper=[1.0] * 4),
            RateConstraint(max_delta=[0.9] * 4),
        ],
    )


def _scalar_sum_corrected(
    project: Callable[..., Any],
    proposed: np.ndarray,
    prev: np.ndarray,
) -> float:
    r = project(proposed, prev, policy_weight=1.0, reference_weight=0.0)
    return float(np.sum(np.asarray(r.corrected_action, dtype=np.float64)))


def _central_fd_dim0(
    project_factory: Callable[[], Callable[..., Any]],
    proposed: np.ndarray,
    prev: np.ndarray,
    *,
    h: float,
) -> dict[str, Any]:
    """Fresh projector per evaluation so CVXPY state does not leak across perturbed points."""

    def f(p: np.ndarray) -> float:
        return _scalar_sum_corrected(project_factory(), p, prev)

    p0 = proposed.copy()
    p_plus = p0.copy()
    p_minus = p0.copy()
    p_plus[0] += h
    p_minus[0] -= h
    f_plus = f(p_plus)
    f_minus = f(p_minus)
    f0 = f(p0)
    fd = (f_plus - f_minus) / (2.0 * h)
    return {
        "dim": 0,
        "h": float(h),
        "fd_slope": float(fd),
        "scalar_at_base": float(f0),
    }


def _central_fd_dims(
    project_factory: Callable[[], Callable[..., Any]],
    proposed: np.ndarray,
    prev: np.ndarray,
    *,
    h_values: list[float],
    dims: list[int],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for d in dims:
        if d < 0 or d >= int(proposed.size):
            raise ValueError(f"dimension index out of range: {d}")
        for h in h_values:
            p_plus = proposed.copy()
            p_minus = proposed.copy()
            p_plus[d] += h
            p_minus[d] -= h
            f_plus = _scalar_sum_corrected(project_factory(), p_plus, prev)
            f_minus = _scalar_sum_corrected(project_factory(), p_minus, prev)
            f0 = _scalar_sum_corrected(project_factory(), proposed.copy(), prev)
            out.append(
                {
                    "dim": int(d),
                    "h": float(h),
                    "fd_slope": float((f_plus - f_minus) / (2.0 * h)),
                    "scalar_at_base": float(f0),
                }
            )
    return out


def _micrograd_fd_torch(*, h: float) -> dict[str, Any]:
    try:
        import torch
    except ImportError:
        return {"import_ok": False}
    n = 4
    a = torch.linspace(0.1, 0.9, n, dtype=torch.float64)
    x_base = torch.ones(n, dtype=torch.float64) / n
    x_base.requires_grad_(True)
    y = torch.sum((x_base - a) ** 2)
    g_auto = torch.autograd.grad(y, x_base)[0].detach().cpu().numpy().copy()
    x_np = (torch.ones(n, dtype=torch.float64) / n).numpy()
    fd = np.zeros(n, dtype=np.float64)

    def fval(vec: np.ndarray) -> float:
        t = torch.tensor(vec, dtype=torch.float64)
        return float(torch.sum((t - a) ** 2).item())

    for i in range(n):
        xp = x_np.copy()
        xm = x_np.copy()
        xp[i] += h
        xm[i] -= h
        fd[i] = (fval(xp) - fval(xm)) / (2.0 * h)
    scale = max(1.0, float(np.max(np.abs(g_auto))))
    err = float(np.max(np.abs(g_auto - fd)))
    return {
        "import_ok": True,
        "probe": "torch R^4 quadratic f(x)=sum((x-a)^2)",
        "max_abs_err_vs_fd": err,
        "scaled_err": err / scale,
        "fd_ok": err < 1e-4 * scale,
    }


def _micrograd_fd_jax(*, h: float) -> dict[str, Any]:
    try:
        import jax
        import jax.numpy as jnp
    except ImportError:
        return {"import_ok": False}

    n = 4
    a = jnp.linspace(0.1, 0.9, n, dtype=jnp.float64)

    def f(z: Any) -> Any:
        return jnp.sum((z - a) ** 2)

    x0 = jnp.ones(n, dtype=jnp.float64) / n
    g_auto = np.asarray(jax.grad(f)(x0), dtype=np.float64)
    x_np = np.ones(n, dtype=np.float64) / n
    fd = np.zeros(n, dtype=np.float64)
    for i in range(n):
        xp = x_np.copy()
        xm = x_np.copy()
        xp[i] += h
        xm[i] -= h
        fd[i] = (float(f(jnp.asarray(xp))) - float(f(jnp.asarray(xm)))) / (2.0 * h)
    scale = max(1.0, float(np.max(np.abs(g_auto))))
    err = float(np.max(np.abs(g_auto - fd)))
    return {
        "import_ok": True,
        "probe": "jax R^4 quadratic f(x)=sum((x-a)^2)",
        "max_abs_err_vs_fd": err,
        "scaled_err": err / scale,
        "fd_ok": err < 1e-4 * scale,
    }


def _probe_torch_jax_extras(*, h: float) -> dict[str, Any]:
    return {
        "torch_micrograd": _micrograd_fd_torch(h=h),
        "jax_micrograd": _micrograd_fd_jax(h=h),
    }


def _cvxpy_moreau_available() -> tuple[bool, str]:
    try:
        import cvxpy as cp
    except ImportError:
        return False, "cvxpy not installed"
    if getattr(cp, "MOREAU", None) is None:
        return False, "cp.MOREAU not available (install vendor moreau + cvxpylayers)"
    installed = {str(s).upper() for s in cp.installed_solvers()}
    if "MOREAU" not in installed:
        return False, "MOREAU is not a registered CVXPY solver in this environment (vendor moreau not installed)."
    return True, ""


def _native_fd_if_requested(
    *,
    proposed: np.ndarray,
    prev: np.ndarray,
    h: float,
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return (
            _central_fd_dim0(
                lambda: create_projector(
                    spec=_spec(),
                    backend=Backend.NATIVE_MOREAU,
                    native_options=NativeMoreauCompiledOptions(
                        device="cpu",
                        max_iter=500,
                        verbose=False,
                        persist_warm_start=False,
                    ),
                ).project,
                proposed,
                prev,
                h=h,
            ),
            None,
        )
    except Exception as exc:
        return None, str(exc)


def collect_differentiation_report(
    *,
    h: float,
    h_values: list[float],
    dims: list[int],
    include_native: bool,
    probe_torch_jax: bool,
    strict: bool,
) -> dict[str, Any]:
    proposed = np.array([0.65, 0.2, 0.1, 0.05], dtype=np.float64)
    prev = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64)
    errors: list[str] = []
    extras: dict[str, Any] = _probe_torch_jax_extras(h=h) if probe_torch_jax else {}
    ok, reason = _cvxpy_moreau_available()
    if not ok:
        payload = {
            "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "deferred",
            "message": reason,
            "reference": None,
            "native": None,
            "extras": extras,
            "errors": errors,
            "recommended_next_steps": [
                "Install solver extras on a licensed host (see README / MAINTAINER_RUNBOOK).",
                "Re-run this script; optional --include-native for native FD smoke.",
            ],
        }
        if strict:
            payload["status"] = "fail"
        return payload

    ref_block = _central_fd_dim0(
        lambda: create_projector(
            spec=_spec(),
            backend=Backend.CVXPY_MOREAU,
            cvxpy_options=SolverOptions(device="cpu", max_iter=500, verbose=False),
        ).project,
        proposed,
        prev,
        h=h,
    )
    ref_grid = _central_fd_dims(
        lambda: create_projector(
            spec=_spec(),
            backend=Backend.CVXPY_MOREAU,
            cvxpy_options=SolverOptions(device="cpu", max_iter=500, verbose=False),
        ).project,
        proposed,
        prev,
        h_values=h_values,
        dims=dims,
    )

    native_block: dict[str, Any] | None = None
    if include_native:
        native_block, nerr = _native_fd_if_requested(proposed=proposed, prev=prev, h=h)
        if nerr is not None:
            errors.append(f"native_fd: {nerr}")

    status = "ok"
    if native_block is None and include_native and errors:
        status = "partial"
    if strict and status != "ok":
        status = "fail"
    return {
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "message": (
            "Finite-difference slope of sum(corrected_action) w.r.t. proposed[0] on the minimal shield spec "
            "(reference CVXPY/Moreau path)."
        ),
        "reference": ref_block,
        "reference_grid": ref_grid,
        "native": native_block,
        "extras": extras,
        "errors": errors,
        "recommended_next_steps": [
            "Compare FD slopes across proposed/prev corners when changing constraint tightness.",
            "If enabling NativeMoreauCompiledOptions.enable_grad, add autograd vs FD tests in a vendor env.",
        ],
    }


def _write_md(path: Path, data: dict[str, Any]) -> None:
    lines = [
        "# Differentiation report",
        "",
        f"Generated: {data.get('generated_at_utc', '')}",
        "",
        f"**Status:** {data.get('status')}",
        "",
        str(data.get("message", "")),
        "",
    ]
    ref = data.get("reference")
    if isinstance(ref, dict):
        lines.extend(
            [
                "## Reference (CVXPY / MOREAU)",
                "",
                f"- dim: {ref.get('dim')}",
                f"- h: {ref.get('h')}",
                f"- fd_slope: {ref.get('fd_slope')}",
                f"- scalar_at_base: {ref.get('scalar_at_base')}",
                "",
            ]
        )
    nat = data.get("native")
    if isinstance(nat, dict):
        lines.extend(
            [
                "## Native (finite difference)",
                "",
                f"- fd_slope: {nat.get('fd_slope')}",
                "",
            ]
        )
    if data.get("extras"):
        lines.extend(["## Optional stacks", "", "```json", json.dumps(data["extras"], indent=2), "```", ""])
    errs = data.get("errors") or []
    if errs:
        lines.extend(["## Errors", "", "\n".join(str(e) for e in errs), ""])
    lines.extend(["## Next steps", ""])
    for s in data.get("recommended_next_steps", []):
        lines.append(f"- {s}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Write differentiation_summary under output/.")
    p.add_argument("--out-dir", type=Path, default=None, help="Default: repo output/")
    p.add_argument("--h-step", type=float, default=1e-5, dest="h_step")
    p.add_argument("--h-grid", type=str, default="", help="Comma-separated finite-difference h values.")
    p.add_argument("--dims", type=str, default="0", help="Comma-separated proposal dimensions to probe.")
    p.add_argument(
        "--include-native",
        action="store_true",
        help="Also run a native Moreau finite-difference slope (requires vendor stack).",
    )
    p.add_argument(
        "--probe-torch-jax",
        action="store_true",
        help="Run optional torch/jax micrograd vs finite-difference probes (no shield autograd yet).",
    )
    p.add_argument("--strict", action="store_true", help="Return fail status when checks are deferred/partial.")
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    out_dir = args.out_dir or (root / "output")
    out_dir.mkdir(parents=True, exist_ok=True)
    h_values = [float(x.strip()) for x in args.h_grid.split(",") if x.strip()] or [float(args.h_step)]
    dims = [int(x.strip()) for x in args.dims.split(",") if x.strip()]
    data = collect_differentiation_report(
        h=float(args.h_step),
        h_values=h_values,
        dims=dims,
        include_native=bool(args.include_native),
        probe_torch_jax=bool(args.probe_torch_jax),
        strict=bool(args.strict),
    )
    (out_dir / "differentiation_summary.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    _write_md(out_dir / "differentiation_report.md", data)
    print(out_dir / "differentiation_summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
