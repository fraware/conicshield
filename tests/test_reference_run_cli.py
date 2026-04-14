from __future__ import annotations

import os
import subprocess
import sys

from tests._repo import repo_root


def test_reference_run_module_help_exits_zero() -> None:
    repo = repo_root()
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


def test_produce_reference_bundle_strict_real_projector_rejects_passthrough() -> None:
    repo = repo_root()
    env = {**os.environ, "PYTHONPATH": str(repo)}
    export_json = repo / "tests" / "fixtures" / "offline_graph_export_minimal.json"
    r = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "produce_reference_bundle.py"),
            "--export-json",
            str(export_json),
            "--run-id",
            "pytest-strict-projector-guard",
            "--passthrough",
            "--strict-real-projector",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert r.returncode != 0
    assert "--strict-real-projector forbids --passthrough" in (r.stderr + r.stdout)


def test_produce_reference_bundle_real_projector_preflight_error_without_moreau() -> None:
    repo = repo_root()
    env = {**os.environ, "PYTHONPATH": str(repo)}
    export_json = repo / "tests" / "fixtures" / "offline_graph_export_minimal.json"
    r = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "produce_reference_bundle.py"),
            "--export-json",
            str(export_json),
            "--run-id",
            "pytest-real-preflight-guard",
            "--no-passthrough",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if "MOREAU solver is not registered" in (r.stderr + r.stdout):
        assert r.returncode == 3
        return
    # In a licensed environment this command may proceed past preflight.
    assert r.returncode in (0, 1)
