from __future__ import annotations

from statistics import mean
from typing import Any

import numpy as np

from conicshield.bench.episode_runner import EpisodeRecord
from conicshield.bench.metrics import step_solver_status_is_failure


def episode_payloads_from_records(records: list[EpisodeRecord]) -> list[dict[str, Any]]:
    return [r.as_dict() for r in records]


def _safe_percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    return float(np.percentile(np.asarray(values, dtype=float), q))


def reward_retention(candidate_avg_reward: float, baseline_avg_reward: float) -> float | None:
    if baseline_avg_reward == 0:
        return None
    return candidate_avg_reward / baseline_avg_reward


def _rates_from_records(records: list[EpisodeRecord]) -> dict[str, float]:
    total_steps = sum(r.num_steps for r in records)
    total_rule_opportunities = 0
    total_rule_violations = 0
    total_intervened_steps = 0
    total_matched_steps = 0
    total_fallback_steps = 0
    total_warm_started = 0
    total_solver_steps = 0
    total_solve_failures = 0

    for r in records:
        total_rule_violations += r.rule_violations
        for s in r.steps:
            if s.previous_instruction is not None:
                total_rule_opportunities += 1
            total_intervened_steps += int(s.intervened)
            total_matched_steps += int(s.matched_action)
            total_fallback_steps += int(s.fallback_used)
            if s.solver_status is not None:
                total_solver_steps += 1
                total_warm_started += int(bool(s.warm_started))
                if step_solver_status_is_failure(s.solver_status):
                    total_solve_failures += 1

    return {
        "intervention_rate": total_intervened_steps / total_steps if total_steps else 0.0,
        "rule_violation_rate": (total_rule_violations / total_rule_opportunities if total_rule_opportunities else 0.0),
        "matched_action_rate": total_matched_steps / total_steps if total_steps else 0.0,
        "fallback_rate": total_fallback_steps / total_steps if total_steps else 0.0,
        "warm_start_rate": total_warm_started / total_solver_steps if total_solver_steps else 0.0,
        "solve_failure_rate": total_solve_failures / total_solver_steps if total_solver_steps else 0.0,
    }


def summary_payload(
    *,
    label: str,
    records: list[EpisodeRecord],
    reward_retention_vs_baseline: float | None = None,
) -> dict[str, Any]:
    rewards = [r.total_reward for r in records]
    steps = [r.num_steps for r in records]
    interventions = [r.num_interventions for r in records]

    intervention_norms: list[float] = []
    solve_times_ms: list[float] = []
    setup_times_ms: list[float] = []
    iterations: list[float] = []
    devices: list[str] = []

    for r in records:
        for s in r.steps:
            if s.intervention_norm is not None:
                intervention_norms.append(float(s.intervention_norm))
            if s.solve_time_sec is not None:
                solve_times_ms.append(1000.0 * float(s.solve_time_sec))
            if s.setup_time_sec is not None:
                setup_times_ms.append(1000.0 * float(s.setup_time_sec))
            if s.iterations is not None:
                iterations.append(float(s.iterations))
            if s.device is not None:
                devices.append(str(s.device))

    rates = _rates_from_records(records)
    device = max(set(devices), key=devices.count) if devices else None

    return {
        "label": label,
        "episodes": len(records),
        "avg_reward": float(mean(rewards)) if rewards else float("nan"),
        "avg_steps": float(mean(steps)) if steps else float("nan"),
        "avg_interventions_per_episode": float(mean(interventions)) if interventions else 0.0,
        "intervention_rate": rates["intervention_rate"],
        "rule_violation_rate": rates["rule_violation_rate"],
        "matched_action_rate": rates["matched_action_rate"],
        "fallback_rate": rates["fallback_rate"],
        "solve_time_p50_ms": _safe_percentile(solve_times_ms, 50),
        "solve_time_p95_ms": _safe_percentile(solve_times_ms, 95),
        "solve_time_p99_ms": _safe_percentile(solve_times_ms, 99),
        "setup_time_p50_ms": _safe_percentile(setup_times_ms, 50),
        "iterations_p50": _safe_percentile(iterations, 50),
        "avg_intervention_norm": (float(mean(intervention_norms)) if intervention_norms else 0.0),
        "solve_failure_rate": rates["solve_failure_rate"],
        "warm_start_rate": rates["warm_start_rate"],
        "reward_retention_vs_baseline": reward_retention_vs_baseline,
        "device": device,
    }
