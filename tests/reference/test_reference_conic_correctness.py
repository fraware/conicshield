"""Layer C: LP / QP / SOCP / mixed-conic — cp.MOREAU vs trusted public solver (CLARABEL or SCS)."""

from __future__ import annotations

import pytest

cvxpy = pytest.importorskip("cvxpy")
cp = cvxpy

from conicshield.reference_correctness.conic_suite import (
    iter_conic_suite_cases,
    moreau_installed,
    run_full_conic_suite,
    solve_pair,
)

pytestmark = [pytest.mark.requires_moreau, pytest.mark.reference_correctness, pytest.mark.solver]


@pytest.mark.parametrize("factory_index", list(range(len(iter_conic_suite_cases()))))
def test_conic_suite_case(factory_index: int) -> None:
    if not moreau_installed(cp):
        pytest.skip("MOREAU solver backend not installed")
    factory = iter_conic_suite_cases()[factory_index]
    prob, variables, case = factory(cp)
    row = solve_pair(cp, prob, family=case.family, variables=variables)
    assert row.get("status") == "ok", row


def test_lp_moreau_matches_reference_seed0_n5_dense() -> None:
    """Explicit alias for the first LP case (readable name in pytest -q)."""
    if not moreau_installed(cp):
        pytest.skip("MOREAU solver backend not installed")
    from conicshield.reference_correctness.conic_suite import build_lp_problem

    prob, variables, case = build_lp_problem(cp, seed=0, n=5, density="dense")
    row = solve_pair(cp, prob, family=case.family, variables=variables)
    assert row["status"] == "ok"


def test_conic_suite_smoke_profile_is_non_empty() -> None:
    if not moreau_installed(cp):
        pytest.skip("MOREAU solver backend not installed")
    rows = run_full_conic_suite(cp, profile="smoke")
    assert rows
    assert all(r.get("suite_profile") == "smoke" for r in rows)
