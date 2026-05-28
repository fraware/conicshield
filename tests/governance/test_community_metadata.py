from __future__ import annotations

import json
from pathlib import Path

from conicshield.governance.community_metadata import build_community_metadata


def test_flagship_community_metadata_shape() -> None:
    root = Path(__file__).resolve().parents[2]
    run_dir = root / "benchmarks" / "published_runs" / "host-realistic-20260525"
    meta = build_community_metadata(run_dir=run_dir, repo_root=root, current_run_id="host-realistic-20260525")
    assert meta["schema_version"] == "conicshield_community_metadata/v1"
    assert meta["evidence_tier"] == "vendor_native"
    assert meta["host_realistic"] is True
    assert meta["includes_native_arm"] is True
    assert meta["is_family_current_run"] is True
    assert meta["solver_stack"] is not None
    assert meta["recommended_uses"]
    assert meta["known_limitations"]


def test_committed_community_metadata_files() -> None:
    root = Path(__file__).resolve().parents[2]
    index = json.loads((root / "benchmarks" / "PUBLISHED_RUN_INDEX.json").read_text(encoding="utf-8"))
    for run in index.get("runs", []):
        rel = str(run["repository_relative_path"]).replace("\\", "/")
        path = root / rel / "COMMUNITY_METADATA.json"
        assert path.is_file(), f"missing {path}; run scripts/sync_community_metadata.py"
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload.get("run_id") == run["run_id"]
        assert "known_limitations" in payload
