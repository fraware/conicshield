from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import jsonschema
import pytest

from conicshield.bench.transition_bank import TransitionBank


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _bank_file_schema() -> dict[str, Any]:
    path = _repo_root() / "schemas" / "transition_bank_file.schema.json"
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_build_transition_bank_demo_cli_validates_schema(tmp_path: Path) -> None:
    out = tmp_path / "demo.json"
    repo = _repo_root()
    env = {**os.environ, "PYTHONPATH": str(repo)}
    subprocess.run(
        [sys.executable, "-m", "conicshield.bench.build_transition_bank", "--demo", "--out", str(out)],
        check=True,
        cwd=repo,
        env=env,
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(_bank_file_schema()).validate(payload)
    assert payload["provenance"]["bank_id"]


def test_build_transition_bank_cli_requires_mode(tmp_path: Path) -> None:
    out = tmp_path / "x.json"
    repo = _repo_root()
    env = {**os.environ, "PYTHONPATH": str(repo)}
    r = subprocess.run(
        [sys.executable, "-m", "conicshield.bench.build_transition_bank", "--out", str(out)],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode != 0


def test_transition_bank_from_json_rejects_malformed(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        TransitionBank.from_json(p)


def test_transition_bank_from_json_rejects_missing_nodes(tmp_path: Path) -> None:
    p = tmp_path / "partial.json"
    p.write_text(json.dumps({"root_address": "Root"}), encoding="utf-8")
    with pytest.raises(KeyError):
        TransitionBank.from_json(p)


def test_build_transition_bank_from_offline_graph_export_cli_validates_schema(tmp_path: Path) -> None:
    out = tmp_path / "from_export.json"
    repo = _repo_root()
    src = repo / "tests" / "fixtures" / "offline_graph_export_minimal.json"
    env = {**os.environ, "PYTHONPATH": str(repo)}
    subprocess.run(
        [
            sys.executable,
            "-m",
            "conicshield.bench.build_transition_bank",
            "--from-offline-graph-export",
            str(src),
            "--out",
            str(out),
        ],
        check=True,
        cwd=repo,
        env=env,
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(_bank_file_schema()).validate(payload)
    assert payload["root_address"] == "Root"


def test_build_transition_bank_cli_rejects_multiple_modes(tmp_path: Path) -> None:
    out = tmp_path / "x.json"
    repo = _repo_root()
    src = repo / "tests" / "fixtures" / "offline_graph_export_minimal.json"
    env = {**os.environ, "PYTHONPATH": str(repo)}
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "conicshield.bench.build_transition_bank",
            "--demo",
            "--from-offline-graph-export",
            str(src),
            "--out",
            str(out),
        ],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode != 0


def test_build_transition_bank_from_json_roundtrip(tmp_path: Path) -> None:
    src = Path("tests/fixtures/parity_reference/transition_bank.json")
    out = tmp_path / "out.json"
    repo = _repo_root()
    env = {**os.environ, "PYTHONPATH": str(repo)}
    subprocess.run(
        [sys.executable, "-m", "conicshield.bench.build_transition_bank", "--from-json", str(src), "--out", str(out)],
        check=True,
        cwd=repo,
        env=env,
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "provenance" in payload
    bank = TransitionBank.from_json(out)
    assert bank.root_address
    assert bank.nodes
