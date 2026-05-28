"""Smoke-run public examples (no vendor Moreau required)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run(script: str) -> None:
    root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, str(root / "examples" / script)],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"{script} failed:\n{proc.stdout}\n{proc.stderr}"


def test_verify_published_run_index_example() -> None:
    _run("verify_published_run_index.py")


def test_inspect_flagship_bundle_example() -> None:
    _run("inspect_flagship_bundle.py")


def test_load_flagship_run_example() -> None:
    _run("load_flagship_run.py")


def test_minimal_reference_projection_example() -> None:
    _run("minimal_reference_projection.py")


def test_compare_reference_vs_native_metrics_example() -> None:
    _run("compare_reference_vs_native_metrics.py")
