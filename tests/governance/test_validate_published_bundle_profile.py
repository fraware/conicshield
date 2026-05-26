"""Published bundle tier file profile."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_validate_published_bundle_profile_passes_all_indexed_runs() -> None:
    proc = subprocess.run(
        [sys.executable, str(_root() / "scripts" / "validate_published_bundle_profile.py")],
        cwd=str(_root()),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_check_throughput_advisory_is_non_fatal_on_latest_report() -> None:
    path = _root() / "benchmarks" / "reports" / "batch_solve_report.latest.json"
    if not path.is_file():
        return
    proc = subprocess.run(
        [
            sys.executable,
            str(_root() / "scripts" / "check_batch_acceptance.py"),
            "--tier",
            "throughput_advisory",
            "--report",
            str(path),
        ],
        cwd=str(_root()),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
