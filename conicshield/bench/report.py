from __future__ import annotations

from pathlib import Path
import json
from typing import Any


def write_json(path: str | Path, summaries: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")


def render_markdown_card(summaries: list[Any]) -> str:
    lines = [
        "# ConicShield Benchmark Card",
        "",
        "## Summary",
        "",
    ]

    for s in summaries:
        label = getattr(s, "label", s["label"])
        lines.extend(
            [
                f"### {label}",
                "",
                f"- Episodes: {getattr(s, 'episodes', s['episodes'])}",
                f"- Avg reward: {getattr(s, 'avg_reward', s['avg_reward']):.4f}",
                f"- Avg steps: {getattr(s, 'avg_steps', s['avg_steps']):.2f}",
                f"- Avg interventions / episode: {getattr(s, 'avg_interventions_per_episode', s['avg_interventions_per_episode']):.4f}",
                f"- Intervention rate: {100.0 * getattr(s, 'intervention_rate', s['intervention_rate']):.2f}%",
                f"- Rule-violation rate: {100.0 * getattr(s, 'rule_violation_rate', s['rule_violation_rate']):.2f}%",
                f"- Matched-action rate: {100.0 * getattr(s, 'matched_action_rate', s['matched_action_rate']):.2f}%",
                f"- Fallback rate: {100.0 * getattr(s, 'fallback_rate', s['fallback_rate']):.2f}%",
                f"- Solve time p50: {getattr(s, 'solve_time_p50_ms', s['solve_time_p50_ms']):.4f} ms",
                f"- Solve time p95: {getattr(s, 'solve_time_p95_ms', s['solve_time_p95_ms']):.4f} ms",
                f"- Solve time p99: {getattr(s, 'solve_time_p99_ms', s['solve_time_p99_ms']):.4f} ms",
                f"- Setup time p50: {getattr(s, 'setup_time_p50_ms', s['setup_time_p50_ms']):.4f} ms",
                f"- Iterations p50: {getattr(s, 'iterations_p50', s['iterations_p50']):.2f}",
                f"- Avg intervention norm: {getattr(s, 'avg_intervention_norm', s['avg_intervention_norm']):.4f}",
                f"- Solve failure rate: {100.0 * getattr(s, 'solve_failure_rate', s['solve_failure_rate']):.2f}%",
                f"- Warm-start rate: {100.0 * getattr(s, 'warm_start_rate', s['warm_start_rate']):.2f}%",
            ]
        )
        reward_retention = getattr(s, "reward_retention_vs_baseline", None)
        if reward_retention is None and isinstance(s, dict):
            reward_retention = s.get("reward_retention_vs_baseline")
        if reward_retention is not None:
            lines.append(
                f"- Reward retention vs baseline: {100.0 * reward_retention:.2f}%"
            )
        lines.append("")

    lines.append("## Publication footer")
    lines.append("")
    lines.append(
        "This result is the current published run for the declared benchmark family only if governance, parity, and promotion gates are green."
    )
    return "\n".join(lines)


def write_markdown(path: str | Path, summaries: list[Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_card(summaries), encoding="utf-8")
