from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

from conicshield.bench.metrics import step_solver_status_is_failure


def _safe_percentile_ms(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    return float(np.percentile(np.asarray(values, dtype=float), q) * 1000.0)


def _rule_violation_rate_for_episode(ep: dict[str, Any]) -> tuple[int, int]:
    violations = 0
    opportunities = 0
    rule = str(ep["rule_choice"])
    for s in ep["steps"]:
        prev = s.get("previous_instruction")
        if prev is None:
            continue
        opportunities += 1
        prev_l = str(prev).lower()
        act = str(s["chosen_action"])
        if (
            (rule == "right" and "right" in prev_l and act != "turn_right")
            or (rule == "left" and "left" in prev_l and act != "turn_left")
            or rule == "alternate"
            and ("left" in prev_l and act != "turn_right" or "right" in prev_l and act != "turn_left")
        ):
            violations += 1
    return violations, opportunities


def build_summary_records(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build summary.json rows consistent with `validate_summary_records` expectations."""
    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ep in episodes:
        by_label[str(ep["arm_label"])].append(ep)

    baseline_reward: float | None = None
    if "baseline-unshielded" in by_label:
        beps = by_label["baseline-unshielded"]
        baseline_reward = sum(float(e["total_reward"]) for e in beps) / len(beps)

    labels_sorted = sorted(by_label.keys())
    out: list[dict[str, Any]] = []

    for label in labels_sorted:
        eps = by_label[label]
        n = len(eps)
        avg_reward = sum(float(e["total_reward"]) for e in eps) / n
        avg_steps = sum(int(e["num_steps"]) for e in eps) / n
        avg_interventions = sum(int(e["num_interventions"]) for e in eps) / n

        total_steps = sum(int(e["num_steps"]) for e in eps)
        total_intervened = sum(sum(int(s["intervened"]) for s in e["steps"]) for e in eps)
        intervention_rate = total_intervened / total_steps if total_steps else 0.0

        rule_violations = 0
        rule_opportunities = 0
        for e in eps:
            v, o = _rule_violation_rate_for_episode(e)
            rule_violations += v
            rule_opportunities += o
        rule_violation_rate = rule_violations / rule_opportunities if rule_opportunities else 0.0

        total_matched = sum(int(e.get("matched_action_steps", 0)) for e in eps)
        total_fallback = sum(int(e.get("fallback_steps", 0)) for e in eps)
        matched_rate = total_matched / total_steps if total_steps else 0.0
        fallback_rate = total_fallback / total_steps if total_steps else 0.0

        solve_times: list[float] = []
        setup_times: list[float] = []
        iterations: list[float] = []
        intervention_norms: list[float] = []
        solve_attempts = 0
        solve_failures = 0
        warm_starts = 0
        warm_total = 0
        devices: list[str] = []

        for e in eps:
            for s in e["steps"]:
                st = s.get("solve_time_sec")
                if st is not None:
                    solve_times.append(float(st))
                    solve_attempts += 1
                    status = s.get("solver_status")
                    if status is not None and step_solver_status_is_failure(str(status)):
                        solve_failures += 1
                su = s.get("setup_time_sec")
                if su is not None:
                    setup_times.append(float(su))
                it = s.get("iterations")
                if it is not None:
                    iterations.append(float(it))
                inn = s.get("intervention_norm")
                if inn is not None:
                    intervention_norms.append(float(inn))
                ws = s.get("warm_started")
                if ws is not None:
                    warm_total += 1
                    if bool(ws):
                        warm_starts += 1
                dev = s.get("device")
                if dev is not None:
                    devices.append(str(dev))

        solve_failure_rate = solve_failures / solve_attempts if solve_attempts else 0.0
        warm_start_rate = warm_starts / warm_total if warm_total else 0.0
        avg_intervention_norm = sum(intervention_norms) / len(intervention_norms) if intervention_norms else 0.0

        device: str | None = devices[0] if devices else None

        retention: float | None = None
        if label != "baseline-unshielded" and baseline_reward is not None:
            retention = float(avg_reward / baseline_reward) if abs(baseline_reward) > 1e-12 else None

        out.append(
            {
                "label": label,
                "episodes": n,
                "avg_reward": avg_reward,
                "avg_steps": avg_steps,
                "avg_interventions_per_episode": avg_interventions,
                "intervention_rate": intervention_rate,
                "rule_violation_rate": rule_violation_rate,
                "matched_action_rate": matched_rate,
                "fallback_rate": fallback_rate,
                "solve_time_p50_ms": _safe_percentile_ms(solve_times, 50),
                "solve_time_p95_ms": _safe_percentile_ms(solve_times, 95),
                "solve_time_p99_ms": _safe_percentile_ms(solve_times, 99),
                "setup_time_p50_ms": _safe_percentile_ms(setup_times, 50),
                "iterations_p50": float(np.percentile(np.asarray(iterations, dtype=float), 50)) if iterations else 0.0,
                "avg_intervention_norm": avg_intervention_norm,
                "solve_failure_rate": solve_failure_rate,
                "warm_start_rate": warm_start_rate,
                "reward_retention_vs_baseline": retention,
                "device": device,
            }
        )

    return out
