from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_verify_v1_lock_quick_exits_zero() -> None:
    root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "verify_v1_lock.py")],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "v1 lock checks PASSED" in proc.stdout
