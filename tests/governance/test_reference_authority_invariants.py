from __future__ import annotations

import json
from pathlib import Path

import pytest

_FAMILY = "conicshield-transition-bank-v1"
_FLAGSHIP = "host-realistic-20260525"


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_current_gates_match_flagship_governance_status() -> None:
    root = _root()
    current = json.loads(
        (root / "benchmarks" / "releases" / _FAMILY / "CURRENT.json").read_text(encoding="utf-8")
    )
    gov = json.loads(
        (root / "benchmarks" / "published_runs" / _FLAGSHIP / "governance_status.json").read_text(
            encoding="utf-8"
        )
    )
    for gate in ("artifact_gate", "parity_gate", "promotion_gate"):
        assert current[gate] == gov[gate] == "green"
    assert current["publishable_arms"] == gov["publishable_arms"]


def test_flagship_has_release_and_parity_artifacts() -> None:
    root = _root()
    base = root / "benchmarks" / "published_runs" / _FLAGSHIP
    assert (base / "release_decision.json").is_file()
    assert (base / "parity_out" / "parity_summary.json").is_file()
    assert (base / "governance_decision.md").is_file()
    text = (base / "governance_decision.md").read_text(encoding="utf-8")
    assert "approve" in text.lower()


def test_export_provenance_links_flagship_run() -> None:
    root = _root()
    prov = json.loads(
        (root / "benchmarks" / "external_evidence" / "EXPORT_PROVENANCE.json").read_text(encoding="utf-8")
    )
    assert prov.get("export_json") == "benchmarks/external_evidence/offline_graph_export_upstream.json"
    assert prov.get("flagship_run_id") == _FLAGSHIP
    assert prov.get("export_kind") == "structural_committed"


def test_committed_batch_solve_report_example_shape() -> None:
    root = _root()
    path = root / "benchmarks" / "reports" / "batch_solve_report.example.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload.get("example_only") is True
    assert isinstance(payload.get("comparisons"), list) and payload["comparisons"]
    row = payload["comparisons"][0]
    assert row["speedup_ratio"] == pytest.approx(
        row["mean_sec_sequential"] / row["mean_sec_batched"]
    )


def test_reference_authority_check_script_imports() -> None:
    root = _root()
    script = root / "scripts" / "reference_authority_check.py"
    assert script.is_file()
