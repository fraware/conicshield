from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_reference_run_module_help_exits_zero() -> None:
    repo = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(repo)}
    r = subprocess.run(
        [sys.executable, "-m", "conicshield.bench.reference_run", "--help"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert r.returncode == 0, r.stderr
