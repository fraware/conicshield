"""CLI smoke for scripts/governed_local_promotion.py (no vendor solver)."""

from __future__ import annotations

import subprocess
import sys

from tests._repo import repo_root


def test_governed_local_promotion_help_exits_zero() -> None:
    repo = repo_root()
    script = repo / "scripts" / "governed_local_promotion.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "validate" in proc.stdout
