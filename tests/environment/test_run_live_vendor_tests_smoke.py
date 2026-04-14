"""Smoke tests for the live vendor test launcher (no vendor packages required)."""

from __future__ import annotations

import subprocess
import sys

from tests._repo import repo_root


def test_run_live_vendor_tests_dry_run_prints_pytest_command() -> None:
    repo = repo_root()
    script = repo / "scripts" / "run_live_vendor_tests.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--dry-run", "--no-dotenv"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "pytest" in proc.stderr
    assert "-m" in proc.stderr


def test_run_live_vendor_tests_collect_only() -> None:
    """``--collect-only`` should succeed (exit 0 or pytest's 'no tests' code 5)."""
    repo = repo_root()
    script = repo / "scripts" / "run_live_vendor_tests.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--no-dotenv", "--skip-preflight", "--collect-only", "-q"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode in (0, 5), proc.stdout + proc.stderr
