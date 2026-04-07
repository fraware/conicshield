"""Smoke tests for Layer G / parity report helper scripts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def test_artifact_validation_report_ok_on_fixture(tmp_path: Path) -> None:
    out = tmp_path / "out"
    r = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts" / "artifact_validation_report.py"),
            "--run-dir",
            str(_REPO / "tests" / "fixtures" / "parity_reference"),
            "--out-dir",
            str(out),
        ],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    payload = json.loads((out / "artifact_validation_report.json").read_text(encoding="utf-8"))
    assert payload["status"] == "ok"


def test_generate_parity_report_passing_summary(tmp_path: Path) -> None:
    summary = {
        "total_steps": 10,
        "action_match_rate": 1.0,
        "max_corrected_linf": 1e-7,
        "p95_corrected_linf": 1e-7,
        "max_corrected_l2": 1e-7,
        "p95_corrected_l2": 1e-7,
        "active_constraints_match_rate": 1.0,
    }
    p = tmp_path / "parity_summary.json"
    p.write_text(json.dumps(summary), encoding="utf-8")
    out = tmp_path / "report_out"
    out.mkdir()
    r = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts" / "generate_parity_report.py"),
            "--parity-summary",
            str(p),
            "--out-dir",
            str(out),
        ],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    text = (out / "parity_report.md").read_text(encoding="utf-8")
    assert "Gate state" in text
    assert "pass" in text.lower()
