from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_run_host_realistic_publish_rejects_minimal_fixture() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "run_host_realistic_publish.py"
    export = root / "tests" / "fixtures" / "offline_graph_export_minimal.json"
    proc = subprocess.run(
        [sys.executable, str(script), "--export-json", str(export), "--run-id", "should-not-run"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "minimal fixture" in (proc.stderr + proc.stdout).lower()
