from __future__ import annotations

import math

from conicshield.bench.episode_runner import EpisodeRecord, StepRecord
from conicshield.bench.metrics import (
    BenchmarkSummary,
    attach_reward_retention,
    fallback_rate,
    matched_action_rate,
    rule_violation_rate,
    summarize,
)


def _ep(
    rule_choice: str,
    steps: list[StepRecord],
    *,
    label: str = "arm",
) -> EpisodeRecord:
    ep = EpisodeRecord(
        episode_id="e1",
        arm_label=label,
        backend="none",
        root_address="R",
        rule_choice=rule_choice,
        bank_id="b",
        policy_id="p",
        policy_checkpoint=None,
        seed=0,
        started_at_utc="2026-01-01T00:00:00Z",
        steps=steps,
    )
    ep.finalize()
    return ep


def _step(
    chosen: str,
    *,
    prev: str | None = "turn right",
    matched: bool = True,
    fallback: bool = False,
    intervened: bool = False,
    solver_status: str | None = None,
    warm_started: bool | None = None,
    solve_time_sec: float | None = None,
    intervention_norm: float | None = None,
    device: str | None = None,
) -> StepRecord:
    return StepRecord(
        step=0,
        current_address="Root",
        current_location=(0.0, 0.0),
        previous_instruction=prev,
        available_actions=["turn_right"],
        chosen_action=chosen,
        reward=0.0,
        intervened=intervened,
        intervention_norm=intervention_norm,
        matched_action=matched,
        fallback_used=fallback,
        solver_status=solver_status,
        warm_started=warm_started,
        solve_time_sec=solve_time_sec,
        device=device,
    )


def test_rule_violation_rate_right_rule() -> None:
    ok = _ep("right", [_step("turn_right", prev="turn right")])
    bad = _ep("right", [_step("turn_left", prev="turn right")])
    assert rule_violation_rate([ok]) == 0.0
    assert rule_violation_rate([bad]) == 1.0
    assert rule_violation_rate([ok, bad]) == 0.5


def test_rule_violation_rate_left_rule() -> None:
    ok = _ep("left", [_step("turn_left", prev="turn left")])
    bad = _ep("left", [_step("turn_right", prev="turn left")])
    assert rule_violation_rate([ok]) == 0.0
    assert rule_violation_rate([bad]) == 1.0


def test_rule_violation_rate_alternate_rule() -> None:
    ok1 = _ep("alternate", [_step("turn_right", prev="turn left")])
    ok2 = _ep("alternate", [_step("turn_left", prev="turn right")])
    bad = _ep("alternate", [_step("go_straight", prev="turn left")])
    assert rule_violation_rate([ok1]) == 0.0
    assert rule_violation_rate([ok2]) == 0.0
    assert rule_violation_rate([bad]) == 1.0


def test_rule_violation_rate_no_opportunities() -> None:
    ep = _ep("right", [_step("turn_left", prev=None)])
    assert rule_violation_rate([ep]) == 0.0


def test_matched_and_fallback_rates() -> None:
    ep = _ep(
        "right",
        [
            _step("turn_right", matched=True, fallback=False),
            _step("turn_right", matched=False, fallback=True),
        ],
    )
    assert matched_action_rate([ep]) == 0.5
    assert fallback_rate([ep]) == 0.5


def test_summarize_intervention_and_solver_telemetry() -> None:
    steps = [
        StepRecord(
            step=0,
            current_address="Root",
            current_location=None,
            previous_instruction=None,
            available_actions=["turn_right"],
            chosen_action="turn_right",
            reward=1.0,
            intervened=True,
            intervention_norm=0.5,
            solver_status="optimal",
            warm_started=True,
            solve_time_sec=0.002,
            setup_time_sec=0.001,
            iterations=3,
            device="cpu",
        ),
        StepRecord(
            step=1,
            current_address="Root",
            current_location=None,
            previous_instruction=None,
            available_actions=["turn_right"],
            chosen_action="turn_right",
            reward=0.0,
            intervened=False,
            solver_status="failed",
            warm_started=False,
            solve_time_sec=0.001,
            device="cpu",
        ),
    ]
    ep = _ep("right", steps)
    s = summarize("test", [ep])
    assert s.intervention_rate == 0.5
    assert s.solve_failure_rate == 0.5
    assert s.warm_start_rate == 0.5
    assert s.avg_intervention_norm == 0.5
    assert not math.isnan(s.solve_time_p50_ms)
    assert s.device == "cpu"


def test_summarize_empty_episodes_percentiles_nan() -> None:
    s = summarize("empty", [])
    assert math.isnan(s.avg_reward)
    assert math.isnan(s.avg_steps)
    assert math.isnan(s.solve_time_p50_ms)


def test_attach_reward_retention() -> None:
    base = BenchmarkSummary(
        label="b",
        episodes=1,
        avg_reward=2.0,
        avg_steps=1.0,
        avg_interventions_per_episode=0.0,
        intervention_rate=0.0,
        rule_violation_rate=0.0,
        matched_action_rate=1.0,
        fallback_rate=0.0,
        solve_time_p50_ms=float("nan"),
        solve_time_p95_ms=float("nan"),
        solve_time_p99_ms=float("nan"),
        setup_time_p50_ms=float("nan"),
        iterations_p50=float("nan"),
        avg_intervention_norm=0.0,
        solve_failure_rate=0.0,
        warm_start_rate=0.0,
    )
    cand = BenchmarkSummary(
        label="c",
        episodes=1,
        avg_reward=1.0,
        avg_steps=1.0,
        avg_interventions_per_episode=0.0,
        intervention_rate=0.0,
        rule_violation_rate=0.0,
        matched_action_rate=1.0,
        fallback_rate=0.0,
        solve_time_p50_ms=float("nan"),
        solve_time_p95_ms=float("nan"),
        solve_time_p99_ms=float("nan"),
        setup_time_p50_ms=float("nan"),
        iterations_p50=float("nan"),
        avg_intervention_norm=0.0,
        solve_failure_rate=0.0,
        warm_start_rate=0.0,
    )
    attach_reward_retention(base, cand)
    assert cand.reward_retention_vs_baseline == 0.5


def test_attach_reward_retention_skips_when_baseline_nan() -> None:
    base = BenchmarkSummary(
        label="b",
        episodes=0,
        avg_reward=float("nan"),
        avg_steps=float("nan"),
        avg_interventions_per_episode=0.0,
        intervention_rate=0.0,
        rule_violation_rate=0.0,
        matched_action_rate=0.0,
        fallback_rate=0.0,
        solve_time_p50_ms=float("nan"),
        solve_time_p95_ms=float("nan"),
        solve_time_p99_ms=float("nan"),
        setup_time_p50_ms=float("nan"),
        iterations_p50=float("nan"),
        avg_intervention_norm=0.0,
        solve_failure_rate=0.0,
        warm_start_rate=0.0,
    )
    cand = BenchmarkSummary(
        label="c",
        episodes=1,
        avg_reward=1.0,
        avg_steps=1.0,
        avg_interventions_per_episode=0.0,
        intervention_rate=0.0,
        rule_violation_rate=0.0,
        matched_action_rate=1.0,
        fallback_rate=0.0,
        solve_time_p50_ms=float("nan"),
        solve_time_p95_ms=float("nan"),
        solve_time_p99_ms=float("nan"),
        setup_time_p50_ms=float("nan"),
        iterations_p50=float("nan"),
        avg_intervention_norm=0.0,
        solve_failure_rate=0.0,
        warm_start_rate=0.0,
    )
    attach_reward_retention(base, cand)
    assert cand.reward_retention_vs_baseline is None


def test_attach_reward_retention_zero_baseline_no_retention() -> None:
    """baseline.avg_reward is 0.0 (falsy); attach_reward_retention leaves retention None."""
    base = BenchmarkSummary(
        label="b",
        episodes=1,
        avg_reward=0.0,
        avg_steps=1.0,
        avg_interventions_per_episode=0.0,
        intervention_rate=0.0,
        rule_violation_rate=0.0,
        matched_action_rate=1.0,
        fallback_rate=0.0,
        solve_time_p50_ms=float("nan"),
        solve_time_p95_ms=float("nan"),
        solve_time_p99_ms=float("nan"),
        setup_time_p50_ms=float("nan"),
        iterations_p50=float("nan"),
        avg_intervention_norm=0.0,
        solve_failure_rate=0.0,
        warm_start_rate=0.0,
    )
    cand = BenchmarkSummary(
        label="c",
        episodes=1,
        avg_reward=1.0,
        avg_steps=1.0,
        avg_interventions_per_episode=0.0,
        intervention_rate=0.0,
        rule_violation_rate=0.0,
        matched_action_rate=1.0,
        fallback_rate=0.0,
        solve_time_p50_ms=float("nan"),
        solve_time_p95_ms=float("nan"),
        solve_time_p99_ms=float("nan"),
        setup_time_p50_ms=float("nan"),
        iterations_p50=float("nan"),
        avg_intervention_norm=0.0,
        solve_failure_rate=0.0,
        warm_start_rate=0.0,
    )
    attach_reward_retention(base, cand)
    assert cand.reward_retention_vs_baseline is None
