from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_export_provenance_has_refresh_history() -> None:
    root = Path(__file__).resolve().parents[2]
    prov = json.loads(
        (root / "benchmarks" / "external_evidence" / "EXPORT_PROVENANCE.json").read_text(encoding="utf-8")
    )
    history = prov.get("refresh_history") or []
    assert len(history) >= 2
    live = [h for h in history if h.get("export_kind") == "live_upstream_dump"]
    assert len(live) >= 1
    assert prov.get("last_flagship_refresh_at_utc")


def test_cadence_check_script_passes_when_fresh() -> None:
    root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "check_reference_refresh_cadence.py"), "--max-days", "365"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
