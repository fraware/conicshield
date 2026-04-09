import json
from pathlib import Path

import pytest

from conicshield.governance.publish import PublishError, publish_from_governance_status


def test_publish_from_governance_status_updates_current(tmp_path) -> None:
    family_dir = tmp_path / "benchmarks" / "releases" / "fam-v1"
    family_dir.mkdir(parents=True)
    (family_dir / "CURRENT.json").write_text(
        json.dumps(
            {
                "family_id": "fam-v1",
                "task_contract_version": "v1",
                "fixture_version": "fixture-v1",
                "current_run_id": None,
                "state": "uninitialized",
                "publishable_arms": [],
                "artifact_gate": "unknown",
                "parity_gate": "unknown",
                "promotion_gate": "unknown",
                "published_at_utc": None,
                "notes": "",
            }
        ),
        encoding="utf-8",
    )
    (family_dir / "HISTORY.json").write_text(json.dumps({"family_id": "fam-v1", "entries": []}), encoding="utf-8")

    registry = tmp_path / "benchmarks" / "registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        json.dumps(
            {
                "benchmark_families": [
                    {
                        "family_id": "fam-v1",
                        "status": "active",
                        "task_contract_version": "v1",
                        "current_fixture_version": "fixture-v1",
                        "current_run_id": None,
                        "published_at_utc": None,
                        "history": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    run_dir = tmp_path / "run_x"
    run_dir.mkdir()
    (run_dir / "governance_status.json").write_text(
        json.dumps(
            {
                "run_id": "run_x",
                "family_id": "fam-v1",
                "task_contract_version": "v1",
                "fixture_version": "fixture-v1",
                "state": "review-locked",
                "artifact_gate": "green",
                "fixture_gate": "green",
                "parity_gate": "green",
                "promotion_gate": "green",
                "review_locked": True,
                "publishable_arms": ["baseline-unshielded"],
                "gate_details": {
                    "artifact_gate": {"status": "green", "detail": "ok"},
                    "fixture_gate": {"status": "green", "detail": "ok"},
                    "parity_gate": {"status": "green", "detail": "ok"},
                    "promotion_gate": {"status": "green", "detail": "ok"},
                    "review_lock_gate": {"status": "green", "detail": "ok"},
                },
            }
        ),
        encoding="utf-8",
    )
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


def test_publish_preserves_benchmark_bundle_paths(tmp_path) -> None:
    """Optional audit keys on CURRENT.json survive publish_from_governance_status."""
    family_dir = tmp_path / "benchmarks" / "releases" / "fam-v1"
    family_dir.mkdir(parents=True)
    paths = ["benchmarks/published_runs/run_a", "benchmarks/published_runs/run_b"]
    (family_dir / "CURRENT.json").write_text(
        json.dumps(
            {
                "family_id": "fam-v1",
                "task_contract_version": "v1",
                "fixture_version": "fixture-v1",
                "current_run_id": None,
                "state": "uninitialized",
                "publishable_arms": [],
                "artifact_gate": "unknown",
                "parity_gate": "unknown",
                "promotion_gate": "unknown",
                "published_at_utc": None,
                "notes": "",
                "benchmark_bundle_paths": paths,
                "external_artifact": {"url": "https://example.invalid/bundle.tgz", "sha256": "0" * 64},
            }
        ),
        encoding="utf-8",
    )
    (family_dir / "HISTORY.json").write_text(json.dumps({"family_id": "fam-v1", "entries": []}), encoding="utf-8")

    registry = tmp_path / "benchmarks" / "registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        json.dumps(
            {
                "benchmark_families": [
                    {
                        "family_id": "fam-v1",
                        "status": "active",
                        "task_contract_version": "v1",
                        "current_fixture_version": "fixture-v1",
                        "current_run_id": None,
                        "published_at_utc": None,
                        "history": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    run_dir = tmp_path / "run_x"
    run_dir.mkdir()
    (run_dir / "governance_status.json").write_text(
        json.dumps(
            {
                "run_id": "run_x",
                "family_id": "fam-v1",
                "task_contract_version": "v1",
                "fixture_version": "fixture-v1",
                "state": "review-locked",
                "artifact_gate": "green",
                "fixture_gate": "green",
                "parity_gate": "green",
                "promotion_gate": "green",
                "review_locked": True,
                "publishable_arms": ["baseline-unshielded"],
                "gate_details": {
                    "artifact_gate": {"status": "green", "detail": "ok"},
                    "fixture_gate": {"status": "green", "detail": "ok"},
                    "parity_gate": {"status": "green", "detail": "ok"},
                    "promotion_gate": {"status": "green", "detail": "ok"},
                    "review_lock_gate": {"status": "green", "detail": "ok"},
                },
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "governance_decision.md").write_text("ok", encoding="utf-8")

    import os

    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        publish_from_governance_status(run_dir=run_dir, reason="test publish")
        current = json.loads((family_dir / "CURRENT.json").read_text(encoding="utf-8"))
        assert current["benchmark_bundle_paths"] == paths
        assert current["external_artifact"]["url"].startswith("https://")
    finally:
        os.chdir(cwd)


def _review_locked_status(run_id: str) -> dict:
    return {
        "run_id": run_id,
        "family_id": "fam-v1",
        "task_contract_version": "v1",
        "fixture_version": "fixture-v1",
        "state": "review-locked",
        "artifact_gate": "green",
        "fixture_gate": "green",
        "parity_gate": "green",
        "promotion_gate": "green",
        "review_locked": True,
        "publishable_arms": ["baseline-unshielded"],
        "gate_details": {
            "artifact_gate": {"status": "green", "detail": "ok"},
            "fixture_gate": {"status": "green", "detail": "ok"},
            "parity_gate": {"status": "green", "detail": "ok"},
            "promotion_gate": {"status": "green", "detail": "ok"},
            "review_lock_gate": {"status": "green", "detail": "ok"},
        },
    }


def test_second_publish_deprecates_previous_in_history(tmp_path: Path) -> None:
    family_dir = tmp_path / "benchmarks" / "releases" / "fam-v1"
    family_dir.mkdir(parents=True)
    (family_dir / "CURRENT.json").write_text(
        json.dumps(
            {
                "family_id": "fam-v1",
                "task_contract_version": "v1",
                "fixture_version": "fixture-v1",
                "current_run_id": None,
                "state": "uninitialized",
                "publishable_arms": [],
                "artifact_gate": "unknown",
                "parity_gate": "unknown",
                "promotion_gate": "unknown",
                "published_at_utc": None,
                "notes": "",
            }
        ),
        encoding="utf-8",
    )
    (family_dir / "HISTORY.json").write_text(json.dumps({"family_id": "fam-v1", "entries": []}), encoding="utf-8")

    registry = tmp_path / "benchmarks" / "registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        json.dumps(
            {
                "benchmark_families": [
                    {
                        "family_id": "fam-v1",
                        "status": "active",
                        "task_contract_version": "v1",
                        "current_fixture_version": "fixture-v1",
                        "current_run_id": None,
                        "published_at_utc": None,
                        "history": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    import os

    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        run_x = tmp_path / "run_x"
        run_x.mkdir()
        (run_x / "governance_status.json").write_text(json.dumps(_review_locked_status("run_x")), encoding="utf-8")
        (run_x / "governance_decision.md").write_text("first", encoding="utf-8")
        publish_from_governance_status(run_dir=run_x, reason="first publish")

        run_y = tmp_path / "run_y"
        run_y.mkdir()
        (run_y / "governance_status.json").write_text(json.dumps(_review_locked_status("run_y")), encoding="utf-8")
        (run_y / "governance_decision.md").write_text("second", encoding="utf-8")
        publish_from_governance_status(run_dir=run_y, reason="second publish")

        history = json.loads((family_dir / "HISTORY.json").read_text(encoding="utf-8"))
        entries = history["entries"]
        assert any(e.get("run_id") == "run_x" and e.get("status") == "deprecated" for e in entries)
        assert any(e.get("run_id") == "run_y" and e.get("status") == "published" for e in entries)
        current = json.loads((family_dir / "CURRENT.json").read_text(encoding="utf-8"))
        assert current["current_run_id"] == "run_y"
    finally:
        os.chdir(cwd)


def test_publish_fails_without_governance_decision_md(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_only_status"
    run_dir.mkdir()
    (run_dir / "governance_status.json").write_text(json.dumps({"run_id": "x"}), encoding="utf-8")

    import os

    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        with pytest.raises(PublishError, match="governance_decision"):
            publish_from_governance_status(run_dir=run_dir, reason="should not run")
    finally:
        os.chdir(cwd)
