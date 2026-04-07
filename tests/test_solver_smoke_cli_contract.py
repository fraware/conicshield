"""§7.2 solver smoke CLI emits structured JSON (solver-marked)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.solver
def test_solver_smoke_cli_stdout_is_json_object() -> None:
    env = {**os.environ, "PYTHONPATH": str(REPO)}
    r = subprocess.run(
        [sys.executable, "-m", "conicshield.core.solver_smoke_cli", "--skip-native"],
        cwd=REPO,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if r.returncode != 0:
        pytest.skip(f"solver smoke reference arm failed (license or install): {r.stdout}{r.stderr}")
    data = json.loads(r.stdout)
    assert isinstance(data, dict)
    assert "reference" in data
    assert "errors" in data
    assert isinstance(data["errors"], list)
    ref = data["reference"]
    assert isinstance(ref, dict)
    assert "solver_status" in ref or ref.get("corrected_action") is not None


@pytest.mark.solver
def test_solver_smoke_cli_native_arm_or_structured_error() -> None:
    env = {**os.environ, "PYTHONPATH": str(REPO)}
    r = subprocess.run(
        [sys.executable, "-m", "conicshield.core.solver_smoke_cli"],
        cwd=REPO,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    data = json.loads(r.stdout)
    assert isinstance(data, dict)
    if r.returncode == 0:
        assert isinstance(data.get("native"), dict)
        return
    errs = data.get("errors", [])
    if any(e.get("arm") == "reference" for e in errs):
        pytest.skip(f"reference arm failed: {r.stdout}{r.stderr}")
    assert any(e.get("arm") == "native" for e in errs), r.stdout
