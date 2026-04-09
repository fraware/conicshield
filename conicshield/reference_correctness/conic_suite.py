"""LP / QP / SOCP / mixed-conic problems: Moreau vs CLARABEL or SCS.

Used by ``tests/reference/test_reference_conic_correctness.py`` and
``scripts/reference_correctness_summary.py`` so CI gates and maintainer reports stay aligned.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class ConicCase:
    """One row in the reference-correctness matrix."""

    family: str
    case_id: str
    n: str
    density: str
    conditioning: str


def moreau_installed(cp: Any) -> bool:
    if not hasattr(cp, "MOREAU"):
        return False
    try:
        solvers = cp.installed_solvers()
        return "MOREAU" in solvers
    except Exception:
        try:
            from cvxpy.reductions.solvers.defines import INSTALLED_SOLVERS

            return "MOREAU" in INSTALLED_SOLVERS
        except Exception:
            return False


def trusted_solver(cp: Any) -> tuple[Any, str]:
    if hasattr(cp, "CLARABEL"):
        return cp.CLARABEL, "CLARABEL"
    return cp.SCS, "SCS"


def status_ok(cp: Any, prob: Any) -> bool:
    s = prob.status
    if s == cp.OPTIMAL:
        return True
    if getattr(cp, "OPTIMAL_INACCURATE", None) is not None and s == cp.OPTIMAL_INACCURATE:
        return True
    sl = str(s).lower()
    return "optimal" in sl


def primal_vector(prob: Any, *vars_: Any) -> np.ndarray:
    parts = []
    for v in vars_:
        parts.append(np.asarray(v.value, dtype=np.float64).ravel())
    return np.concatenate(parts) if len(parts) > 1 else parts[0]


def assert_agreement(
    x_m: np.ndarray,
    x_r: np.ndarray,
    obj_m: float,
    obj_r: float,
    *,
    family: str,
    linf_tol: float = 5e-3,
    obj_rtol: float = 1e-3,
) -> None:
    linf = float(np.max(np.abs(x_m - x_r)))
    if linf >= linf_tol:
        raise ValueError(f"{family}: primal linf delta {linf} (tol {linf_tol})")
    bound = obj_rtol * max(1.0, abs(obj_r))
    if abs(obj_m - obj_r) >= bound:
        raise ValueError(f"{family}: objective delta {abs(obj_m - obj_r)} (bound {bound})")


def _solver_num_iters(prob: Any) -> int | None:
    st = getattr(prob, "solver_stats", None)
    if st is None:
        return None
    ni = getattr(st, "num_iters", None)
    return int(ni) if ni is not None else None


def solve_pair(
    cp: Any,
    prob: Any,
    *,
    family: str,
    variables: tuple[Any, ...],
) -> dict[str, Any]:
    """Solve with trusted solver then MOREAU; return row dict and agreement check (or error)."""
    ref_sol, ref_name = trusted_solver(cp)
    row: dict[str, Any] = {
        "family": family,
        "trusted_solver": ref_name,
        "status": "pending",
    }
    try:
        prob.solve(solver=ref_sol, verbose=False)
        if not status_ok(cp, prob):
            row["status"] = "fail"
            row["error"] = f"trusted status {prob.status}"
            return row
        x_ref = primal_vector(prob, *variables)
        obj_ref = float(prob.value)
        row["objective_trusted"] = obj_ref
        row["trusted_num_iters"] = _solver_num_iters(prob)

        for v in variables:
            v.value = None
        prob.solve(solver=cp.MOREAU, verbose=False, device="cpu", max_iter=500)
        if not status_ok(cp, prob):
            row["status"] = "fail"
            row["error"] = f"moreau status {prob.status}"
            return row
        x_m = primal_vector(prob, *variables)
        obj_m = float(prob.value)
        row["objective_moreau"] = obj_m
        row["moreau_num_iters"] = _solver_num_iters(prob)
        linf = float(np.max(np.abs(x_m - x_ref)))
        row["primal_linf_delta"] = linf
        row["objective_abs_delta"] = abs(obj_m - obj_ref)
        row["objective_rel_delta"] = float(abs(obj_m - obj_ref) / max(1e-12, abs(obj_ref)))
        assert_agreement(x_m, x_ref, obj_m, obj_ref, family=family)
        row["status"] = "ok"
    except Exception as exc:
        row["status"] = "error"
        row["error"] = str(exc)
    return row


def build_lp_problem(cp: Any, *, seed: int, n: int, density: str) -> tuple[Any, tuple[Any, ...], ConicCase]:
    rng = np.random.default_rng(seed)
    c = rng.standard_normal(n)
    if density == "sparse":
        mask = rng.random(n) > 0.6
        c = np.where(mask, c, 0.0)
        if float(np.sum(np.abs(c))) < 1e-6:
            c[0] = 1.0
    x = cp.Variable(n)
    prob = cp.Problem(cp.Minimize(c @ x), [cp.sum(x) == 1.0, x >= 0])
    case = ConicCase(
        family="LP",
        case_id=f"lp_seed{seed}_n{n}_{density}",
        n=str(n),
        density=density,
        conditioning="nominal",
    )
    return prob, (x,), case


def build_qp_problem(cp: Any, *, n: int, conditioning: str) -> tuple[Any, tuple[Any, ...], ConicCase]:
    scale = 0.01 if conditioning == "ill" else 0.5
    P = np.eye(n) * scale
    q = np.linspace(1.0, -0.5, n)
    x = cp.Variable(n)
    prob = cp.Problem(
        cp.Minimize(cp.quad_form(x, P) + q @ x),
        [cp.sum(x) == 1.0, x >= 0],
    )
    case = ConicCase(
        family="QP",
        case_id=f"qp_n{n}_{conditioning}",
        n=str(n),
        density="dense",
        conditioning=conditioning,
    )
    return prob, (x,), case


def build_socp_problem(cp: Any, *, n: int = 3) -> tuple[Any, tuple[Any, ...], ConicCase]:
    x = cp.Variable(n)
    t = cp.Variable()
    prob = cp.Problem(
        cp.Minimize(t),
        [cp.norm(x, 2) <= t, cp.sum(x) == 1.0, x >= 0],
    )
    case = ConicCase(
        family="SOCP",
        case_id=f"socp_min_t_n{n}",
        n=str(n),
        density="dense",
        conditioning="nominal",
    )
    return prob, (x, t), case


def build_mixed_conic_problem(cp: Any) -> tuple[Any, tuple[Any, ...], ConicCase]:
    x = cp.Variable(4)
    prob = cp.Problem(
        cp.Minimize(cp.sum_squares(x) + 0.05 * cp.sum(x)),
        [
            cp.sum(x) == 1.0,
            x >= 0,
            x[0] + x[1] <= 0.9,
            cp.norm(x[2:], 2) <= 0.5,
        ],
    )
    case = ConicCase(
        family="mixed-conic",
        case_id="qp_soc_mix",
        n="4",
        density="dense",
        conditioning="nominal",
    )
    return prob, (x,), case


def iter_conic_suite_cases() -> list[Callable[[Any], tuple[Any, tuple[Any, ...], ConicCase]]]:
    """Factories in stable order for reports and tests."""

    def _lp01(cp: Any) -> tuple[Any, tuple[Any, ...], ConicCase]:
        return build_lp_problem(cp, seed=0, n=5, density="dense")

    def _lp02(cp: Any) -> tuple[Any, tuple[Any, ...], ConicCase]:
        return build_lp_problem(cp, seed=1, n=5, density="dense")

    def _lp_sparse(cp: Any) -> tuple[Any, tuple[Any, ...], ConicCase]:
        return build_lp_problem(cp, seed=2, n=8, density="sparse")

    def _lp_large(cp: Any) -> tuple[Any, tuple[Any, ...], ConicCase]:
        return build_lp_problem(cp, seed=3, n=12, density="dense")

    def _lp_xl(cp: Any) -> tuple[Any, tuple[Any, ...], ConicCase]:
        return build_lp_problem(cp, seed=4, n=24, density="dense")

    def _lp_sparse_xl(cp: Any) -> tuple[Any, tuple[Any, ...], ConicCase]:
        return build_lp_problem(cp, seed=5, n=16, density="sparse")

    def _qp_well(cp: Any) -> tuple[Any, tuple[Any, ...], ConicCase]:
        return build_qp_problem(cp, n=4, conditioning="well")

    def _qp_well8(cp: Any) -> tuple[Any, tuple[Any, ...], ConicCase]:
        return build_qp_problem(cp, n=8, conditioning="well")

    def _qp_ill(cp: Any) -> tuple[Any, tuple[Any, ...], ConicCase]:
        return build_qp_problem(cp, n=6, conditioning="ill")

    def _qp_ill10(cp: Any) -> tuple[Any, tuple[Any, ...], ConicCase]:
        return build_qp_problem(cp, n=10, conditioning="ill")

    def _socp(cp: Any) -> tuple[Any, tuple[Any, ...], ConicCase]:
        return build_socp_problem(cp, n=3)

    def _socp6(cp: Any) -> tuple[Any, tuple[Any, ...], ConicCase]:
        return build_socp_problem(cp, n=6)

    def _mixed(cp: Any) -> tuple[Any, tuple[Any, ...], ConicCase]:
        return build_mixed_conic_problem(cp)

    return [
        _lp01,
        _lp02,
        _lp_sparse,
        _lp_large,
        _lp_xl,
        _lp_sparse_xl,
        _qp_well,
        _qp_well8,
        _qp_ill,
        _qp_ill10,
        _socp,
        _socp6,
        _mixed,
    ]


def run_full_conic_suite(cp: Any, *, profile: str = "standard") -> list[dict[str, Any]]:
    if profile not in {"smoke", "standard", "stress"}:
        raise ValueError(f"Unknown profile: {profile}")
    rows: list[dict[str, Any]] = []
    factories = iter_conic_suite_cases()
    if profile == "smoke":
        factories = factories[:4]
    elif profile == "stress":
        factories = factories + factories
    for factory in factories:
        prob, variables, case = factory(cp)
        row = solve_pair(cp, prob, family=case.family, variables=variables)
        row["case_id"] = case.case_id
        row["n"] = case.n
        row["density"] = case.density
        row["conditioning"] = case.conditioning
        row["suite_profile"] = profile
        rows.append(row)
    return rows
