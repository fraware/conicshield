from conicshield.artifacts.payloads import reward_retention, summary_payload
from conicshield.artifacts.summary_builder import build_summary_records
from conicshield.bench.episode_runner import EpisodeRecord, StepRecord


def test_reward_retention_none_on_zero_baseline() -> None:
    assert reward_retention(1.0, 0.0) is None


def test_summary_payload_basic_fields() -> None:
    ep = EpisodeRecord(
        episode_id="ep1",
        arm_label="baseline-unshielded",
        backend="none",
        root_address="Root",
        rule_choice="right",
        bank_id="bank",
        policy_id="policy",
        policy_checkpoint=None,
        seed=7,
        started_at_utc="2026-04-06T00:00:00Z",
    )
    ep.steps.append(
        StepRecord(
            step=0,
            current_address="Root",
            current_location=(0.0, 0.0),
            previous_instruction="turn_right",
            available_actions=["turn_right"],
            chosen_action="turn_right",
            reward=1.0,
            matched_action=True,
            fallback_used=False,
        )
    )
    ep.finalize()
    summary = summary_payload(label="baseline-unshielded", records=[ep])
    assert summary["episodes"] == 1
    assert summary["avg_reward"] == 1.0
    assert summary["rule_violation_rate"] == 0.0


def test_build_summary_records_ecos_style_solver_status_one_not_failure() -> None:
    """ECOS/MOSEK-style status ``1`` means optimal; must not count as solve failure."""
    episodes = [
        {
            "episode_id": "baseline-unshielded-001",
            "arm_label": "baseline-unshielded",
            "total_reward": 0.0,
            "num_steps": 1,
            "num_interventions": 0,
            "matched_action_steps": 1,
            "fallback_steps": 0,
            "rule_choice": "right",
            "steps": [
                {
                    "intervened": False,
                    "chosen_action": "turn_right",
                    "previous_instruction": None,
                    "solve_time_sec": None,
                }
            ],
        },
        {
            "episode_id": "shielded-native-moreau-001",
            "arm_label": "shielded-native-moreau",
            "total_reward": 0.0,
            "num_steps": 1,
            "num_interventions": 1,
            "matched_action_steps": 1,
            "fallback_steps": 0,
            "rule_choice": "right",
            "steps": [
                {
                    "intervened": True,
                    "chosen_action": "turn_right",
                    "previous_instruction": None,
                    "solve_time_sec": 1e-6,
                    "solver_status": "1",
                    "iterations": 1,
                    "warm_started": False,
                }
            ],
        },
    ]
    rows = build_summary_records(episodes)
    native = next(r for r in rows if r["label"] == "shielded-native-moreau")
    assert native["solve_failure_rate"] == 0.0
