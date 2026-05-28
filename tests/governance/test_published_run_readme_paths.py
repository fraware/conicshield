from __future__ import annotations

import json
from pathlib import Path


def test_published_readme_validate_commands_are_repo_relative() -> None:
    root = Path(__file__).resolve().parents[2]
    index = json.loads((root / "benchmarks" / "PUBLISHED_RUN_INDEX.json").read_text(encoding="utf-8"))
    for run in index.get("runs", []):
        rel = str(run["repository_relative_path"]).replace("\\", "/")
        text = (root / rel / "README.md").read_text(encoding="utf-8")
        assert "C:/Users" not in text and "C:\\Users" not in text
        assert f"--run-dir {rel}" in text
        assert "python -m conicshield.published_runs.cli verify" in text
