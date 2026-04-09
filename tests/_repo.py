"""Repository root discovery for tests at any depth under ``tests/``."""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while True:
        if (p / "pyproject.toml").is_file():
            return p
        if p == p.parent:
            raise RuntimeError("pyproject.toml not found above tests/")
        p = p.parent
