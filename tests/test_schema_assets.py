from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]


def _schema_files() -> list[Path]:
    root = REPO_ROOT / "schemas"
    return sorted(root.glob("*.schema.json"))


@pytest.mark.parametrize("path", _schema_files(), ids=lambda p: p.name)
def test_schema_json_parses(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "$schema" in data, f"{path.name} must declare $schema (Draft 2020-12 meta-schema URL)"
    assert "$schema" in data or "$id" in data or "type" in data or "$defs" in data


def test_schema_directory_nonempty() -> None:
    assert len(_schema_files()) >= 4


def test_offline_graph_export_fixture_validates_against_schema() -> None:
    schema_path = REPO_ROOT / "schemas" / "offline_transition_graph_export.schema.json"
    schema = cast(dict[str, Any], json.loads(schema_path.read_text(encoding="utf-8")))
    export_path = REPO_ROOT / "tests" / "fixtures" / "offline_graph_export_minimal.json"
    payload = cast(dict[str, Any], json.loads(export_path.read_text(encoding="utf-8")))
    Draft202012Validator(schema).validate(payload)


def test_mini_bundle_paths_exist_relative_to_repo() -> None:
    """Golden dirs referenced by other tests remain present."""
    mini = REPO_ROOT / "tests" / "fixtures" / "mini_reference_bundle"
    assert (mini / "episodes.jsonl").is_file()
    assert (mini / "transition_bank.json").is_file()
    assert (mini / "SHA256SUMS").is_file()
