from __future__ import annotations

import json
import os

from tests._repo import repo_root


def test_flagship_solver_versions_present_when_required() -> None:
    if os.environ.get("REQUIRE_REAL_SOLVER_VERSIONS", "").strip() != "1":
        return
    path = (
        repo_root()
        / "benchmarks"
        / "published_runs"
        / "host-realistic-20260525"
        / "solver_versions.json"
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("moreau"), "flagship solver_versions.json must record moreau pin"
