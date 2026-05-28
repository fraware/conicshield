from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_full_refresh_cadence_script_passes() -> None:
    root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "check_flagship_full_refresh_cadence.py"), "--max-days", "365"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
