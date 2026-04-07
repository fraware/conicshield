"""Layer C: LP / QP / SOCP / mixed-conic — cp.MOREAU vs trusted public solver (CLARABEL or SCS)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

cvxpy = pytest.importorskip("cvxpy")
cp = cvxpy

pytestmark = [pytest.mark.requires_moreau, pytest.mark.reference_correctness, pytest.mark.solver]


def _moreau_installed() -> bool:
    """True only when CVXPY registered the Moreau backend (`cp.MOREAU` alone is not enough)."""
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


def _trusted_solver() -> tuple[Any, str]:
    if hasattr(cp, "CLARABEL"):
        return cp.CLARABEL, "CLARABEL"
    return cp.SCS, "SCS"


def _status_ok(prob: Any) -> bool:
    s = prob.status
    if s == cp.OPTIMAL:
        return True
    if getattr(cp, "OPTIMAL_INACCURATE", None) is not None and s == cp.OPTIMAL_INACCURATE:
        return True
    sl = str(s).lower()
    return "optimal" in sl


def _assert_agreement(
    x_m: np.ndarray,
    x_r: np.ndarray,
    obj_m: float,
    obj_r: float,
    *,
    family: str,
) -> None:
    linf = float(np.max(np.abs(x_m - x_r)))
    assert linf < 5e-3, f"{family}: primal linf delta {linf}"
    assert abs(obj_m - obj_r) < 1e-3 * max(1.0, abs(obj_r)), f"{family}: objective delta"


@pytest.mark.parametrize("seed", [0, 1])
def test_lp_moreau_matches_reference(seed: int) -> None:
    if not _moreau_installed():
        pytest.skip("MOREAU solver backend not installed")
    rng = np.random.default_rng(seed)
    n = 5
    c = rng.standard_normal(n)
    # Simplex LP (bounded, feasible) — avoid unbounded/infeasible random halfspace LPs.
    x = cp.Variable(n)
    prob = cp.Problem(cp.Minimize(c @ x), [cp.sum(x) == 1.0, x >= 0])
    ref_sol, _ = _trusted_solver()
    prob.solve(solver=ref_sol, verbose=False)
    assert _status_ok(prob)
    x_ref = np.asarray(x.value, dtype=np.float64).ravel()
    obj_ref = float(prob.value)

    x.value = None
    prob.solve(solver=cp.MOREAU, verbose=False, device="cpu", max_iter=500)
    assert _status_ok(prob)
    x_m = np.asarray(x.value, dtype=np.float64).ravel()
    obj_m = float(prob.value)
    _assert_agreement(x_m, x_ref, obj_m, obj_ref, family="LP")


def test_qp_moreau_matches_reference() -> None:
    if not _moreau_installed():
        pytest.skip("MOREAU solver backend not installed")
    n = 4
    P = np.eye(n) * 0.5
    q = np.array([1.0, -0.5, 0.2, 0.0])
    x = cp.Variable(n)
    prob = cp.Problem(
        cp.Minimize(cp.quad_form(x, P) + q @ x),
        [cp.sum(x) == 1.0, x >= 0],
    )
    ref_sol, _ = _trusted_solver()
    prob.solve(solver=ref_sol, verbose=False)
    assert _status_ok(prob)
    x_ref = np.asarray(x.value, dtype=np.float64).ravel()
    obj_ref = float(prob.value)

    x.value = None
    prob.solve(solver=cp.MOREAU, verbose=False, device="cpu", max_iter=500)
    assert _status_ok(prob)
    x_m = np.asarray(x.value, dtype=np.float64).ravel()
    obj_m = float(prob.value)
    _assert_agreement(x_m, x_ref, obj_m, obj_ref, family="QP")


def test_socp_moreau_matches_reference() -> None:
    """Minimal SOCP: minimize t subject to ||x||_2 <= t, sum(x)=1, x >= 0 (feasible simplex slice)."""
    if not _moreau_installed():
        pytest.skip("MOREAU solver backend not installed")
    n = 3
    x = cp.Variable(n)
    t = cp.Variable()
    prob = cp.Problem(
        cp.Minimize(t),
        [cp.norm(x, 2) <= t, cp.sum(x) == 1.0, x >= 0],
    )
    ref_sol, _ = _trusted_solver()
    prob.solve(solver=ref_sol, verbose=False)
    assert _status_ok(prob)
    xv_ref = np.concatenate([np.asarray(x.value, dtype=np.float64).ravel(), np.asarray(t.value).ravel()])
    obj_ref = float(prob.value)

    x.value = None
    t.value = None
    prob.solve(solver=cp.MOREAU, verbose=False, device="cpu", max_iter=500)
    assert _status_ok(prob)
    xv_m = np.concatenate([np.asarray(x.value, dtype=np.float64).ravel(), np.asarray(t.value).ravel()])
    obj_m = float(prob.value)
    _assert_agreement(xv_m, xv_ref, obj_m, obj_ref, family="SOCP")


def test_mixed_conic_qp_soc_moreau_matches_reference() -> None:
    """Strictly convex QP objective with linear inequalities and an SOC constraint (mixed-conic)."""
    if not _moreau_installed():
        pytest.skip("MOREAU solver backend not installed")
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
    ref_sol, _ = _trusted_solver()
    prob.solve(solver=ref_sol, verbose=False)
    assert _status_ok(prob)
    x_ref = np.asarray(x.value, dtype=np.float64).ravel()
    obj_ref = float(prob.value)

    x.value = None
    prob.solve(solver=cp.MOREAU, verbose=False, device="cpu", max_iter=500)
    assert _status_ok(prob)
    x_m = np.asarray(x.value, dtype=np.float64).ravel()
    obj_m = float(prob.value)
    _assert_agreement(x_m, x_ref, obj_m, obj_ref, family="mixed-conic")
