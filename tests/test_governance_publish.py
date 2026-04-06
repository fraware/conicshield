import json
from pathlib import Path

from conicshield.governance.publish import publish_from_governance_status


def test_publish_from_governance_status_updates_current(tmp_path) -> None:
    family_dir = tmp_path / "benchmarks" / "releases" / "fam-v1"
    family_dir.mkdir(parents=True)
    (family_dir / "CURRENT.json").write_text(json.dumps({
        "family_id":"fam-v1",
        "task_contract_version":"v1",
        "fixture_version":"fixture-v1",
        "current_run_id":None,
        "state":"uninitialized",
        "publishable_arms":[],
        "artifact_gate":"unknown",
        "parity_gate":"unknown",
        "promotion_gate":"unknown",
        "published_at_utc":None,
        "notes":""
    }), encoding="utf-8")
    (family_dir / "HISTORY.json").write_text(json.dumps({"family_id":"fam-v1","entries":[]}), encoding="utf-8")

    registry = tmp_path / "benchmarks" / "registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps({"benchmark_families":[{"family_id":"fam-v1","status":"active","task_contract_version":"v1","current_fixture_version":"fixture-v1","current_run_id":None,"published_at_utc":None,"history":[]}]}), encoding="utf-8")

    run_dir = tmp_path / "run_x"
    run_dir.mkdir()
    (run_dir / "governance_status.json").write_text(json.dumps({
        "run_id":"run_x","family_id":"fam-v1","task_contract_version":"v1","fixture_version":"fixture-v1","state":"review-locked","artifact_gate":"green","fixture_gate":"green","parity_gate":"green","promotion_gate":"green","review_locked":True,"publishable_arms":["baseline-unshielded"],"gate_details":{"artifact_gate":{"status":"green","detail":"ok"},"fixture_gate":{"status":"green","detail":"ok"},"parity_gate":{"status":"green","detail":"ok"},"promotion_gate":{"status":"green","detail":"ok"},"review_lock_gate":{"status":"green","detail":"ok"}}}), encoding="utf-8")
    (run_dir / "governance_decision.md").write_text("ok", encoding="utf-8")

    import os
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        publish_from_governance_status(run_dir=run_dir, reason="test publish")
        current = json.loads((family_dir / "CURRENT.json").read_text(encoding="utf-8"))
        assert current["current_run_id"] == "run_x"
    finally:
        os.chdir(cwd)
