"""S8 decision-grade report contract tests (no vendor Moreau required)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "benchmarks" / "reports" / "s8_qualification" / "decision_grade_summary.json"


def test_s8_decision_grade_summary_committed() -> None:
    assert SUMMARY.is_file(), "commit benchmarks/reports/s8_qualification/decision_grade_summary.json"
    payload = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert payload.get("schema_version") == "conicshield_s8_decision_grade/v1"
    assert "provenance" in payload
    assert "solver_doctor_subset" in payload["provenance"]
    assert "comparisons" in payload
    assert "cells" in payload
    assert payload["counts"]["cells_total"] == len(payload["cells"])


def test_s8_unavailable_backends_are_not_run_not_invented() -> None:
    payload = json.loads(SUMMARY.read_text(encoding="utf-8"))
    by_label = {c["label"]: c for c in payload["comparisons"]}
    for label in ("moreau_cvxpy", "moreau_native", "heterogeneous_batch", "windows_sidecar"):
        row = by_label[label]
        assert row["status"] == "NOT_RUN", label
        assert row.get("reason"), label
        assert "e2e_p50_sec" not in row or row.get("e2e_p50_sec") is None


def test_s8_public_reference_measured_or_explicit() -> None:
    payload = json.loads(SUMMARY.read_text(encoding="utf-8"))
    pub = next(c for c in payload["comparisons"] if c["label"] == "public_reference")
    assert pub["status"] in {"ok", "NOT_RUN"}
    if pub["status"] == "ok":
        assert pub.get("e2e_p50_sec") is not None
        assert pub.get("e2e_p95_sec") is not None
        assert pub.get("e2e_p99_sec") is not None
        assert pub.get("e2e_max_sec") is not None


def test_decision_grade_script_exists() -> None:
    assert (ROOT / "scripts" / "decision_grade_benchmark.py").is_file()
