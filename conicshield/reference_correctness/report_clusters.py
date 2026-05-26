"""Helpers for trusted conic suite reporting (no cvxpy import)."""

from __future__ import annotations

from typing import Any


def cluster_cases_by_family(case_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Aggregate suite rows by ``family`` for failure dashboards."""
    clusters: dict[str, dict[str, Any]] = {}
    for row in case_rows:
        family = str(row.get("family", "unknown"))
        bucket = clusters.setdefault(family, {"total": 0, "ok": 0, "failed_case_ids": []})
        bucket["total"] += 1
        if row.get("status") == "ok":
            bucket["ok"] += 1
        else:
            bucket["failed_case_ids"].append(row.get("case_id"))
    return clusters
