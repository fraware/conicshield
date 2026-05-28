from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_apply_branch_protection_dry_run() -> None:
    root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "apply_branch_protection_github.py")],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "DRY RUN" in proc.stdout
    assert "quality" in proc.stdout
