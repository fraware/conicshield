"""Layer C: suite metadata and family clustering (public solvers; no vendor MOREAU)."""

from __future__ import annotations

import pytest

cvxpy = pytest.importorskip("cvxpy")

from conicshield.reference_correctness.conic_suite import (  # noqa: E402
    group_suite_rows_by_family,
    run_conic_suite_trusted_only,
)


def test_standard_profile_rows_include_case_and_conditioning_metadata() -> None:
    rows = run_conic_suite_trusted_only(cvxpy, profile="standard")
    assert len(rows) >= 8
    for r in rows:
        assert r.get("status") == "ok"
        assert "case_id" in r
        assert "family" in r
        assert "conditioning" in r


def test_group_suite_rows_by_family_clusters_lp_qp_socp() -> None:
    rows = run_conic_suite_trusted_only(cvxpy, profile="standard")
    grouped = group_suite_rows_by_family(rows)
    assert "LP" in grouped and len(grouped["LP"]) >= 1
    assert "QP" in grouped and len(grouped["QP"]) >= 1
    assert "SOCP" in grouped and len(grouped["SOCP"]) >= 1
