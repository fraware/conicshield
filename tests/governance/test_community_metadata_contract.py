from __future__ import annotations

import json
from pathlib import Path

from conicshield.governance.community_metadata_contract import validate_community_metadata


def test_flagship_community_metadata_contract() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "benchmarks" / "published_runs" / "host-realistic-20260525" / "COMMUNITY_METADATA.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert validate_community_metadata(payload, expected_run_id="host-realistic-20260525") == []


def test_all_committed_bundles_satisfy_contract() -> None:
    root = Path(__file__).resolve().parents[2]
    index = json.loads((root / "benchmarks" / "PUBLISHED_RUN_INDEX.json").read_text(encoding="utf-8"))
    for run in index.get("runs", []):
        rid = str(run["run_id"])
        rel = str(run["repository_relative_path"]).replace("\\", "/")
        path = root / rel / "COMMUNITY_METADATA.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        failures = validate_community_metadata(payload, expected_run_id=rid)
        assert failures == [], f"{rid}: {failures}"
