from __future__ import annotations

from typing import Any

from conicshield.governance.finalize import _promotion_gate


def _row(label: str, *, p95_ms: float) -> dict[str, Any]:
    return {
        "label": label,
        "rule_violation_rate": 0.0,
        "matched_action_rate": 1.0,
        "reward_retention_vs_baseline": 1.0,
        "solve_failure_rate": 0.0,
        "solve_time_p95_ms": p95_ms,
    }


def test_promotion_gate_allows_sub_ms_native_timing_noise() -> None:
    """Single-step micro-benchmarks: native p95 slightly above geometry should not fail promotion."""
    summary_by_label = {
        "baseline-unshielded": _row("baseline-unshielded", p95_ms=0.0),
        "shielded-rules-only": _row("shielded-rules-only", p95_ms=1.0),
        "shielded-rules-plus-geometry": _row("shielded-rules-plus-geometry", p95_ms=0.005003),
        "shielded-native-moreau": _row("shielded-native-moreau", p95_ms=0.006237),
    }
    result = _promotion_gate(summary_by_label)
    assert result.status == "green", result.detail
