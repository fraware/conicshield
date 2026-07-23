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
    current = json.loads((root / "benchmarks" / "releases" / _FAMILY / "CURRENT.json").read_text(encoding="utf-8"))
    gov = json.loads(
        (root / "benchmarks" / "published_runs" / _FLAGSHIP / "governance_status.json").read_text(encoding="utf-8")
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
    assert prov.get("export_kind") == "live_upstream_dump"
    assert prov.get("graph_shape") == "host_realistic_fork"
    history = prov.get("refresh_history") or []
    assert len(history) >= 2
    live = [h for h in history if h.get("export_kind") == "live_upstream_dump"]
    assert len(live) >= 1
    full = [h for h in history if h.get("workflow") == "live-export-full" and h.get("authority_ok")]
    assert full, "at least one refresh must complete live-export-full with authority_ok"


def test_committed_batch_solve_report_example_shape() -> None:
    root = _root()
    path = root / "benchmarks" / "reports" / "batch_solve_report.example.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload.get("example_only") is True
    assert isinstance(payload.get("comparisons"), list) and payload["comparisons"]
    row = payload["comparisons"][0]
    assert row["speedup_ratio"] == pytest.approx(row["mean_sec_sequential"] / row["mean_sec_batched"])
    assert payload.get("batch_story") in ("viability_only", "throughput_win", "below_viability")


def test_reference_authority_check_script_imports() -> None:
    root = _root()
    script = root / "scripts" / "reference_authority_check.py"
    assert script.is_file()


def test_reference_authority_snapshot_aligned() -> None:
    from conicshield.governance.reference_authority import build_reference_authority_snapshot

    snapshot = build_reference_authority_snapshot(repo_root=_root())
    assert snapshot["aligned"] is True
    assert snapshot["flagship_run_id"] == _FLAGSHIP
    assert snapshot["current_release"]["current_run_id"] == _FLAGSHIP


def test_committed_reference_authority_snapshot_matches_live() -> None:
    import json
    import subprocess
    import sys

    root = _root()
    path = root / "benchmarks" / "reports" / "reference_authority_snapshot.json"
    assert path.is_file(), f"missing {path}; run scripts/generate_reference_authority_snapshot.py"
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "generate_reference_authority_snapshot.py"), "--check"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload.get("aligned") is True
