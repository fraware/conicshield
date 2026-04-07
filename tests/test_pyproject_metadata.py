from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_core_fields() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert project["name"] == "conicshield"
    assert project["version"] == "0.1.0"
    assert "3.11" in project["requires-python"]
    urls = project["urls"]
    assert "Repository" in urls
    assert "github.com/fraware/conicshield" in urls["Repository"]


def test_pyproject_dev_extra_includes_test_runners() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev = data["project"]["optional-dependencies"]["dev"]
    assert any("pytest" in x for x in dev)
    assert any("ruff" in x for x in dev)
    assert any("mypy" in x for x in dev)
