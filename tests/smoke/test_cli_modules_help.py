from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from tests._repo import repo_root


def _repo() -> Path:
    return repo_root()


def _env() -> dict[str, str]:
    return {**os.environ, "PYTHONPATH": str(_repo())}


def test_parity_cli_help_exits_zero() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "conicshield.parity.cli", "--help"],
        cwd=_repo(),
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr


def test_finalize_cli_help_exits_zero() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "conicshield.governance.finalize_cli", "--help"],
        cwd=_repo(),
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr


def test_parity_regenerate_fixture_cli_help_exits_zero() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "conicshield.parity.regenerate_fixture", "--help"],
        cwd=_repo(),
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr


def test_release_cli_help_exits_zero() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "conicshield.governance.release_cli", "--help"],
        cwd=_repo(),
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr


def test_dashboard_cli_help_exits_zero() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "conicshield.governance.dashboard_cli", "--help"],
        cwd=_repo(),
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr


def test_audit_cli_help_exits_zero() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "conicshield.governance.audit_cli", "--help"],
        cwd=_repo(),
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr


def test_build_transition_bank_cli_help_exits_zero() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "conicshield.bench.build_transition_bank", "--help"],
        cwd=_repo(),
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    assert "--from-offline-graph-export" in r.stdout
