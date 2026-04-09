import json
import os
from pathlib import Path

from conicshield.governance.release import decide_release_mode


def test_release_dry_run_same_family_for_uninitialized_family(tmp_path: Path) -> None:
    """Hermetic: real repo CURRENT.json may point at a run whose config does not match this stub."""
    rel = tmp_path / "benchmarks" / "releases" / "conicshield-transition-bank-v1"
    rel.mkdir(parents=True)
    (rel / "CURRENT.json").write_text(
        json.dumps({"family_id": "conicshield-transition-bank-v1", "current_run_id": None}),
        encoding="utf-8",
    )

    run_dir = tmp_path / "run_x"
    run_dir.mkdir()
    (run_dir / "config.json").write_text(
        json.dumps(
            {
                "environment": {
                    "action_space": ["turn_left", "turn_right", "go_straight", "turn_back"],
                    "rule_choices": ["right", "left", "alternate"],
                    "state_contract": {"location_dim": 2, "direction_dim": 2, "nearby_places_feature_size": 20},
                },
                "transition_bank": {"max_depth": 4, "max_nodes": 300, "radius": 500, "max_candidates_per_node": 12},
                "arms": [
                    {"label": "baseline-unshielded", "backend": "none"},
                    {"label": "shielded-rules-only", "backend": "cvxpy_moreau", "use_geometry_prior": False},
                    {"label": "shielded-rules-plus-geometry", "backend": "cvxpy_moreau", "use_geometry_prior": True},
                ],
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "governance_status.json").write_text(
        json.dumps(
            {
                "run_id": "run_x",
                "family_id": "conicshield-transition-bank-v1",
                "task_contract_version": "v1",
                "fixture_version": "fixture-v1",
                "state": "review-locked",
                "artifact_gate": "green",
                "fixture_gate": "green",
                "parity_gate": "unknown",
                "promotion_gate": "green",
                "review_locked": True,
                "publishable_arms": ["baseline-unshielded", "shielded-rules-only", "shielded-rules-plus-geometry"],
                "gate_details": {
                    "artifact_gate": {"status": "green", "detail": "ok"},
                    "fixture_gate": {"status": "green", "detail": "ok"},
                    "parity_gate": {"status": "unknown", "detail": "n/a"},
                    "promotion_gate": {"status": "green", "detail": "ok"},
                    "review_lock_gate": {"status": "green", "detail": "ok"},
                },
            }
        ),
        encoding="utf-8",
    )
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        decision = decide_release_mode(run_dir=run_dir, family_id="conicshield-transition-bank-v1")
    finally:
        os.chdir(cwd)
    assert decision.mode == "same-family"
