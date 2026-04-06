from conicshield.artifacts.payloads import reward_retention, summary_payload
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
