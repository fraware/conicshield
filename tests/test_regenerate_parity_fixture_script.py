from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

from conicshield.artifacts.validator import validate_run_bundle
from conicshield.parity.fixture_policy import validate_fixture_policy
from tests._repo import repo_root


def _load_regenerate_script_module(repo: Path):
    path = repo / "scripts" / "regenerate_parity_fixture.py"
    spec = importlib.util.spec_from_file_location("regenerate_parity_fixture_script", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_copy2_unless_same_file_is_noop_when_paths_identical(tmp_path: Path) -> None:
    mod = _load_regenerate_script_module(repo_root())
    p = tmp_path / "same.txt"
    p.write_text("keep", encoding="utf-8")
    mod._copy2_unless_same_file(p, p)
    assert p.read_text(encoding="utf-8") == "keep"


def test_regenerate_parity_fixture_script_round_trip_to_tmp(tmp_path: Path) -> None:
    repo = repo_root()
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


def test_regenerate_parity_fixture_fallback_fixture_manifest_when_run_bundle_lacks_it(
    tmp_path: Path,
) -> None:
    """benchmarks/runs/<id> from produce_reference_bundle omits FIXTURE_MANIFEST."""
    repo = repo_root()
    full = repo / "tests/fixtures/parity_reference"
    src = tmp_path / "run_only"
    dest = tmp_path / "promoted"
    src.mkdir(parents=True)
    for name in (
        "config.json",
        "summary.json",
        "episodes.jsonl",
        "transition_bank.json",
        "RUN_PROVENANCE.json",
        "config.schema.json",
        "summary.schema.json",
        "episodes.schema.json",
    ):
        shutil.copy2(full / name, src / name)
    env = {**os.environ, "PYTHONPATH": str(repo)}
    r = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts/regenerate_parity_fixture.py"),
            "--source",
            str(src),
            "--dest",
            str(dest),
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert (dest / "FIXTURE_MANIFEST.json").is_file()
    validate_run_bundle(dest)
    validate_fixture_policy(dest)
