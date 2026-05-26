from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conicshield.bench.offline_graph_export import validate_offline_graph_export


def test_export_inter_sim_rehearsal_fork_cli(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    out = tmp_path / "export.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "export_inter_sim_offline_graph.py"),
            "--rehearsal-fork",
            "--out",
            str(out),
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    validate_offline_graph_export(payload)
    assert "NodeA" in payload["coords_by_address"]
