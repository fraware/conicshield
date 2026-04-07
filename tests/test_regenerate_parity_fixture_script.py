from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from conicshield.artifacts.validator import validate_run_bundle
from conicshield.parity.fixture_policy import validate_fixture_policy


def test_regenerate_parity_fixture_script_round_trip_to_tmp(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    src = repo / "tests/fixtures/parity_reference"
    dest = tmp_path / "promoted"
    env = {**os.environ, "PYTHONPATH": str(repo)}
    r = subprocess.run(
        [sys.executable, str(repo / "scripts/regenerate_parity_fixture.py"), "--source", str(src), "--dest", str(dest)],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    validate_run_bundle(dest)
    validate_fixture_policy(dest)
