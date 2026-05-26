from __future__ import annotations

from conicshield.reference_correctness.report_clusters import cluster_cases_by_family


def test_cluster_cases_by_family_groups_failures() -> None:
    rows = [
        {"family": "lp", "case_id": "lp_a", "status": "ok"},
        {"family": "lp", "case_id": "lp_b", "status": "fail"},
        {"family": "socp", "case_id": "socp_a", "status": "ok"},
    ]
    clusters = cluster_cases_by_family(rows)
    assert clusters["lp"]["total"] == 2
    assert clusters["lp"]["ok"] == 1
    assert clusters["lp"]["failed_case_ids"] == ["lp_b"]
    assert clusters["socp"]["failed_case_ids"] == []
