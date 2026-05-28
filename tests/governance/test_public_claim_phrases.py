from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_public_claim_phrase_scan_passes() -> None:
    root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "check_public_claim_phrases.py")],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
