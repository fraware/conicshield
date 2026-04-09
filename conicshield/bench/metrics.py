from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import mean

import numpy as np

from conicshield.bench.episode_runner import EpisodeRecord


def _safe_percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    return float(np.percentile(np.asarray(values, dtype=float), q))


@dataclass(slots=True)
class BenchmarkSummary:
    label: str
    episodes: int
    avg_reward: float
    avg_steps: float
    avg_interventions_per_episode: float
    intervention_rate: float
    rule_violation_rate: float
    matched_action_rate: float
    fallback_rate: float
    solve_time_p50_ms: float
    solve_time_p95_ms: float
    solve_time_p99_ms: float
    setup_time_p50_ms: float
    iterations_p50: float
    avg_intervention_norm: float
    solve_failure_rate: float
    warm_start_rate: float
    reward_retention_vs_baseline: float | None = None
    device: str | None = None

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "episodes": self.episodes,
            "avg_reward": self.avg_reward,
            "avg_steps": self.avg_steps,
            "avg_interventions_per_episode": self.avg_interventions_per_episode,
            "intervention_rate": self.intervention_rate,
            "rule_violation_rate": self.rule_violation_rate,
            "matched_action_rate": self.matched_action_rate,
            "fallback_rate": self.fallback_rate,
            "solve_time_p50_ms": self.solve_time_p50_ms,
            "solve_time_p95_ms": self.solve_time_p95_ms,
            "solve_time_p99_ms": self.solve_time_p99_ms,
            "setup_time_p50_ms": self.setup_time_p50_ms,
            "iterations_p50": self.iterations_p50,
            "avg_intervention_norm": self.avg_intervention_norm,
            "solve_failure_rate": self.solve_failure_rate,
            "warm_start_rate": self.warm_start_rate,
            "reward_retention_vs_baseline": self.reward_retention_vs_baseline,
            "device": self.device,
        }


def rule_violation_rate(episodes: list[EpisodeRecord]) -> float:
    violations = 0
    opportunities = 0
    for ep in episodes:
        for step in ep.steps:
            prev = step.previous_instruction
            rule = ep.rule_choice
            act = step.chosen_action
            if prev is None:
                continue
            prev_l = str(prev).lower()
            opportunities += 1
            if (
                (
                    rule == "right"
                    and "right" in prev_l
                    and act != "turn_right"
                    or rule == "left"
                    and "left" in prev_l
                    and act != "turn_left"
                )
                or rule == "alternate"
                and ("left" in prev_l and act != "turn_right" or "right" in prev_l and act != "turn_left")
            ):
                violations += 1
    return violations / opportunities if opportunities else 0.0


def fallback_rate(episodes: list[EpisodeRecord]) -> float:
    total = 0
    fallbacks = 0
    for ep in episodes:
        for step in ep.steps:
            total += 1
            if step.fallback_used:
                fallbacks += 1
    return fallbacks / total if total else 0.0


def step_solver_status_is_failure(solver_status: str | None) -> bool:
    """Return True when telemetry indicates a failed solve (not a successful projection).

    Avoids matching ``error`` inside tokens like ``error_tolerance`` (substring false positives).
    """
    if solver_status is None:
        return False
    s = str(solver_status).lower()
    if not s.strip() or s.strip() == "unknown":
        return False
    # Strong success (CVXPY + Moreau-style strings)
    if ("optimal" in s or "solved" in s or "converged" in s) and "infeas" not in s:
        return False
    if "almost" in s and "infeas" not in s:
        return False
    if s.strip() in ("1", "true", "4"):
        return False
    # Failures
    if "infeas" in s or "unbounded" in s:
        return True
    if "unsolved" in s:
        return True
    if "fail" in s:
        return True
    if re.search(r"\berror\b", s):
        if any(p in s for p in ("no error", "without error", "zero error", "error-free")):
            return False
        return True
    return False


def matched_action_rate(episodes: list[EpisodeRecord]) -> float:
    total = 0
    matched = 0
    for ep in episodes:
        for step in ep.steps:
            total += 1
            if step.matched_action:
                matched += 1
    return matched / total if total else 0.0


def summarize(label: str, episodes: list[EpisodeRecord]) -> BenchmarkSummary:
    rewards = [ep.total_reward for ep in episodes]
    steps = [ep.num_steps for ep in episodes]
    interventions = [ep.num_interventions for ep in episodes]

    solve_times_ms: list[float] = []
    setup_times_ms: list[float] = []
    iterations: list[float] = []
    intervention_norms: list[float] = []
    devices: list[str] = []
    total_steps = 0
    total_intervened_steps = 0
    total_warm_started = 0
    total_solver_steps = 0
    total_solve_failures = 0

    for ep in episodes:
        for step in ep.steps:
            total_steps += 1
            if step.intervened:
                total_intervened_steps += 1
            if step.solve_time_sec is not None:
                solve_times_ms.append(1000.0 * float(step.solve_time_sec))
            if step.setup_time_sec is not None:
                setup_times_ms.append(1000.0 * float(step.setup_time_sec))
            if step.iterations is not None:
                iterations.append(float(step.iterations))
            if step.intervention_norm is not None:
                intervention_norms.append(float(step.intervention_norm))
            if step.device is not None:
                devices.append(step.device)
            if step.solver_status is not None:
                total_solver_steps += 1
                total_warm_started += int(bool(step.warm_started))
                if step_solver_status_is_failure(step.solver_status):
                    total_solve_failures += 1

    device = max(set(devices), key=devices.count) if devices else None

    return BenchmarkSummary(
        label=label,
        episodes=len(episodes),
        avg_reward=float(mean(rewards)) if rewards else float("nan"),
        avg_steps=float(mean(steps)) if steps else float("nan"),
        avg_interventions_per_episode=float(mean(interventions)) if interventions else 0.0,
        intervention_rate=(total_intervened_steps / total_steps) if total_steps else 0.0,
        rule_violation_rate=rule_violation_rate(episodes),
        matched_action_rate=matched_action_rate(episodes),
        fallback_rate=fallback_rate(episodes),
        solve_time_p50_ms=_safe_percentile(solve_times_ms, 50),
        solve_time_p95_ms=_safe_percentile(solve_times_ms, 95),
        solve_time_p99_ms=_safe_percentile(solve_times_ms, 99),
        setup_time_p50_ms=_safe_percentile(setup_times_ms, 50),
        iterations_p50=_safe_percentile(iterations, 50),
        avg_intervention_norm=float(mean(intervention_norms)) if intervention_norms else 0.0,
        solve_failure_rate=(total_solve_failures / total_solver_steps) if total_solver_steps else 0.0,
        warm_start_rate=(total_warm_started / total_solver_steps) if total_solver_steps else 0.0,
        device=device,
    )


def attach_reward_retention(
    baseline: BenchmarkSummary,
    candidate: BenchmarkSummary,
) -> BenchmarkSummary:
    retention = None
    if baseline.avg_reward and not np.isnan(baseline.avg_reward):
        retention = candidate.avg_reward / baseline.avg_reward
    candidate.reward_retention_vs_baseline = retention
    return candidate
