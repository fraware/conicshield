"""Layer C (public): conic suite formulations solve under CLARABEL/SCS without vendor MOREAU."""

from __future__ import annotations

import pytest

cvxpy = pytest.importorskip("cvxpy")

pytestmark = pytest.mark.reference_correctness

from conicshield.reference_correctness.conic_suite import (  # noqa: E402
    iter_conic_suite_cases,
    run_conic_suite_trusted_only,
    solve_trusted_only,
)


def test_conic_smoke_trusted_optimal() -> None:
    rows = run_conic_suite_trusted_only(cvxpy, profile="smoke")
    assert rows
    assert all(r.get("status") == "ok" for r in rows)


def test_conic_standard_profile_trusted_optimal() -> None:
    """Full trusted-only suite (public solvers): larger LP/QP/SOCP mix than smoke."""
    rows = run_conic_suite_trusted_only(cvxpy, profile="standard")
    assert len(rows) >= 4
    assert all(r.get("status") == "ok" for r in rows)


@pytest.mark.slow
def test_conic_stress_profile_trusted_optimal() -> None:
    """Optional long run: doubled case list. Run with ``-m slow`` locally or in scheduled CI."""
    rows = run_conic_suite_trusted_only(cvxpy, profile="stress")
    assert rows
    assert all(r.get("status") == "ok" for r in rows)


@pytest.mark.parametrize("factory_index", list(range(4)))
def test_conic_smoke_case_trusted(factory_index: int) -> None:
    factory = iter_conic_suite_cases()[factory_index]
    prob, _variables, case = factory(cvxpy)
    row = solve_trusted_only(cvxpy, prob, family=case.family)
    assert row.get("status") == "ok", row
