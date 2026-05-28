from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_print_v1_status_exits_zero() -> None:
    root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "print_v1_status.py")],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "host-realistic-20260525" in proc.stdout
    assert "COMMUNITY_LAYER" in proc.stdout
