from __future__ import annotations

import json
from pathlib import Path

from conicshield.bench.metrics import BenchmarkSummary
from conicshield.bench.report import render_markdown_card, write_json, write_markdown


def _summary_obj(*, label: str, retention: float | None = None) -> BenchmarkSummary:
    s = BenchmarkSummary(
        label=label,
        episodes=2,
        avg_reward=1.5,
        avg_steps=3.0,
        avg_interventions_per_episode=0.5,
        intervention_rate=0.25,
        rule_violation_rate=0.0,
        matched_action_rate=1.0,
        fallback_rate=0.0,
        solve_time_p50_ms=1.0,
        solve_time_p95_ms=2.0,
        solve_time_p99_ms=3.0,
        setup_time_p50_ms=0.5,
        iterations_p50=4.0,
        avg_intervention_norm=0.1,
        solve_failure_rate=0.0,
        warm_start_rate=1.0,
    )
    s.reward_retention_vs_baseline = retention
    return s


def _summary_dict(*, label: str, retention: float | None = None) -> dict[str, float | int | str | None]:
    d: dict[str, float | int | str | None] = {
        "label": label,
        "episodes": 1,
        "avg_reward": -0.5,
        "avg_steps": 2.0,
        "avg_interventions_per_episode": 0.0,
        "intervention_rate": 0.0,
        "rule_violation_rate": 1.0,
        "matched_action_rate": 1.0,
        "fallback_rate": 0.0,
        "solve_time_p50_ms": float("nan"),
        "solve_time_p95_ms": float("nan"),
        "solve_time_p99_ms": float("nan"),
        "setup_time_p50_ms": float("nan"),
        "iterations_p50": float("nan"),
        "avg_intervention_norm": 0.0,
        "solve_failure_rate": 0.0,
        "warm_start_rate": 0.0,
    }
    if retention is not None:
        d["reward_retention_vs_baseline"] = retention
    return d


def test_render_markdown_card_from_objects_and_dicts() -> None:
    md = render_markdown_card(
        [
            _summary_obj(label="arm_a", retention=0.5),
            _summary_dict(label="arm_b", retention=None),
        ]
    )
    assert "# ConicShield Benchmark Card" in md
    assert "### arm_a" in md
    assert "### arm_b" in md
    assert "Intervention rate: 25.00%" in md
    assert "Rule-violation rate: 100.00%" in md
    assert "Reward retention vs baseline: 50.00%" in md
    assert "Publication footer" in md
    assert "governance, parity, and promotion gates are green" in md


def test_render_markdown_card_skips_retention_line_when_none() -> None:
    md = render_markdown_card([_summary_dict(label="solo")])
    assert "### solo" in md
    assert "Reward retention vs baseline" not in md


def test_write_json_roundtrip(tmp_path: Path) -> None:
    rows = [
        {"label": "x", "episodes": 1, "avg_reward": 0.0},
        {"label": "y", "episodes": 2, "avg_reward": 1.0},
    ]
    path = tmp_path / "out" / "summary.json"
    write_json(path, rows)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == rows


def test_write_markdown_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "card.md"
    write_markdown(path, [_summary_obj(label="z")])
    text = path.read_text(encoding="utf-8")
    assert len(text) > 50
    assert "### z" in text


def test_render_markdown_nan_metrics_renders() -> None:
    md = render_markdown_card([_summary_dict(label="nan_arm")])
    assert "### nan_arm" in md
    assert "nan" in md
