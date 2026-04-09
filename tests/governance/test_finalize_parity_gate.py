"""Governance parity gate: parity_summary.json can satisfy parity without a native benchmark arm."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conicshield.governance.finalize import FinalizationInputs, finalize_run, sync_current_release_from_status
from conicshield.governance.policy import GovernanceError


def _passing_parity_payload() -> dict[str, float | int]:
    return {
        "action_match_rate": 1.0,
        "active_constraints_match_rate": 1.0,
        "max_corrected_linf": 0.0,
        "p95_corrected_linf": 0.0,
        "max_corrected_l2": 0.0,
    }


def test_parity_gate_green_from_parity_file_without_native_arm(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    ref = Path("tests/fixtures/parity_reference")
    for name in (
        "config.json",
        "config.schema.json",
        "summary.json",
        "summary.schema.json",
        "episodes.jsonl",
        "episodes.schema.json",
        "transition_bank.json",
        "RUN_PROVENANCE.json",
    ):
        (run_dir / name).write_text((ref / name).read_text(encoding="utf-8"), encoding="utf-8")
    parity_path = tmp_path / "parity_summary.json"
    parity_path.write_text(json.dumps(_passing_parity_payload()), encoding="utf-8")

    status = finalize_run(
        FinalizationInputs(
            run_dir=run_dir,
            family_id="conicshield-transition-bank-v1",
            task_contract_version="v1",
            fixture_version="fixture-v1",
            reference_fixture_dir=ref,
            parity_summary_path=parity_path,
            current_release_path=None,
        )
    )
    assert status["parity_gate"] == "green"


def test_parity_gate_red_when_parity_path_missing(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    ref = Path("tests/fixtures/parity_reference")
    for name in (
        "config.json",
        "config.schema.json",
        "summary.json",
        "summary.schema.json",
        "episodes.jsonl",
        "episodes.schema.json",
        "transition_bank.json",
        "RUN_PROVENANCE.json",
    ):
        (run_dir / name).write_text((ref / name).read_text(encoding="utf-8"), encoding="utf-8")
    missing = tmp_path / "nowhere/parity_summary.json"

    status = finalize_run(
        FinalizationInputs(
            run_dir=run_dir,
            family_id="conicshield-transition-bank-v1",
            task_contract_version="v1",
            fixture_version="fixture-v1",
            reference_fixture_dir=ref,
            parity_summary_path=missing,
            current_release_path=None,
        )
    )
    assert status["parity_gate"] == "red"


def test_parity_gate_red_when_native_arm_without_parity_file(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    ref = Path("tests/fixtures/parity_reference")
    for name in (
        "config.json",
        "config.schema.json",
        "summary.json",
        "summary.schema.json",
        "episodes.jsonl",
        "episodes.schema.json",
        "transition_bank.json",
        "RUN_PROVENANCE.json",
    ):
        (run_dir / name).write_text((ref / name).read_text(encoding="utf-8"), encoding="utf-8")
    rows = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    rows.append(
        {
            "label": "shielded-native-moreau",
            "rule_violation_rate": 0.0,
            "matched_action_rate": 1.0,
            "solve_failure_rate": 0.0,
            "solve_time_p95_ms": 1.0,
            "reward_retention_vs_baseline": 1.0,
        }
    )
    (run_dir / "summary.json").write_text(json.dumps(rows), encoding="utf-8")

    status = finalize_run(
        FinalizationInputs(
            run_dir=run_dir,
            family_id="conicshield-transition-bank-v1",
            task_contract_version="v1",
            fixture_version="fixture-v1",
            reference_fixture_dir=ref,
            parity_summary_path=None,
            current_release_path=None,
        )
    )
    assert status["parity_gate"] == "red"


def test_sync_current_release_from_status_updates_gates(tmp_path: Path) -> None:
    current = tmp_path / "CURRENT.json"
    current.write_text(
        json.dumps(
            {
                "family_id": "fam",
                "current_run_id": "run-a",
                "artifact_gate": "unknown",
                "parity_gate": "unknown",
                "promotion_gate": "unknown",
                "publishable_arms": [],
            }
        ),
        encoding="utf-8",
    )
    status = {
        "run_id": "run-a",
        "artifact_gate": "green",
        "parity_gate": "green",
        "promotion_gate": "green",
        "publishable_arms": ["baseline-unshielded"],
    }
    sync_current_release_from_status(current_release_path=current, status=status)
    payload = json.loads(current.read_text(encoding="utf-8"))
    assert payload["parity_gate"] == "green"
    assert payload["publishable_arms"] == ["baseline-unshielded"]


def test_sync_current_release_rejects_run_id_mismatch(tmp_path: Path) -> None:
    current = tmp_path / "CURRENT.json"
    current.write_text(json.dumps({"current_run_id": "other"}), encoding="utf-8")
    status = {"run_id": "run-a", "artifact_gate": "green", "parity_gate": "green", "promotion_gate": "green", "publishable_arms": []}
    with pytest.raises(GovernanceError):
        sync_current_release_from_status(current_release_path=current, status=status)
