from __future__ import annotations

from pathlib import Path


def test_artifact_schemas_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    assert (root / "schemas" / "summary.schema.json").is_file()
    assert (root / "schemas" / "config.schema.json").is_file()
