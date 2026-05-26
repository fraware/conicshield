"""Capture script smoke (requires inter-sim checkout)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from conicshield.bench.inter_sim_export import intersim_checkout_root

_REPO = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(intersim_checkout_root() is None, reason="inter-sim-rl checkout missing")
def test_capture_host_realistic_fork_writes_json(tmp_path: Path) -> None:
    out = tmp_path / "graph.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts" / "capture_inter_sim_offline_graph.py"),
            "--host-realistic-fork",
            "--out",
            str(out),
        ],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "Root" in data
    assert data["Root"], "Root must have outgoing edges"
