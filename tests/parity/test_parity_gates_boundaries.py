"""Thresholds match conicshield.parity.gates.enforce_default_parity_gates (Phase 5)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from conicshield.core.result import ProjectionResult
from conicshield.parity.gates import (
    ParityGateError,
    enforce_default_parity_gates,
    list_default_parity_gate_violations,
)
from conicshield.parity.replay import ParitySummary, compare_against_reference


def _ok_summary(
    *,
    total_steps: int = 4,
    action_match_rate: float = 1.0,
    max_corrected_linf: float = 1e-5,
    p95_corrected_linf: float = 1e-6,
    max_corrected_l2: float = 1e-5,
    p95_corrected_l2: float = 1e-6,
    active_constraints_match_rate: float = 0.999,
) -> ParitySummary:
    return ParitySummary(
        total_steps=total_steps,
        action_match_rate=action_match_rate,
        max_corrected_linf=max_corrected_linf,
        p95_corrected_linf=p95_corrected_linf,
        max_corrected_l2=max_corrected_l2,
        p95_corrected_l2=p95_corrected_l2,
        active_constraints_match_rate=active_constraints_match_rate,
    )


def test_parity_gate_passes_at_documented_boundaries() -> None:
    s = _ok_summary()
    assert list_default_parity_gate_violations(s) == []
    enforce_default_parity_gates(s)


def test_parity_gate_fails_action_match_below_one() -> None:
    bad = _ok_summary(action_match_rate=0.999)
    assert len(list_default_parity_gate_violations(bad)) == 1
    with pytest.raises(ParityGateError, match="Action match rate"):
        enforce_default_parity_gates(bad)


def test_parity_gate_fails_constraints_below_threshold() -> None:
    with pytest.raises(ParityGateError, match="Active-constraint match rate"):
        enforce_default_parity_gates(_ok_summary(active_constraints_match_rate=0.998))


def test_parity_gate_fails_max_corrected_linf_above_tolerance() -> None:
    with pytest.raises(ParityGateError, match="max_corrected_linf"):
        enforce_default_parity_gates(_ok_summary(max_corrected_linf=2e-5))


def test_parity_gate_fails_p95_corrected_linf_above_tolerance() -> None:
    with pytest.raises(ParityGateError, match="p95_corrected_linf"):
        enforce_default_parity_gates(_ok_summary(p95_corrected_linf=2e-6))


def test_parity_gate_fails_max_corrected_l2_above_tolerance() -> None:
    with pytest.raises(ParityGateError, match="max_corrected_l2"):
        enforce_default_parity_gates(_ok_summary(max_corrected_l2=2e-5))


def test_parity_gate_accepts_exact_tolerance_boundaries() -> None:
    """At-threshold values must pass (inclusive upper bounds in gates)."""
    enforce_default_parity_gates(
        _ok_summary(
            max_corrected_linf=1e-5,
            p95_corrected_linf=1e-6,
            max_corrected_l2=1e-5,
            active_constraints_match_rate=0.999,
        )
    )


def test_parity_gate_fails_just_above_max_corrected_linf() -> None:
    """Strict `>` tolerance: one ULP past 1e-5 must violate."""
    above = math.nextafter(1e-5, math.inf)
    bad = _ok_summary(max_corrected_linf=above)
    v = list_default_parity_gate_violations(bad)
    assert any("max_corrected_linf" in line for line in v)
    with pytest.raises(ParityGateError, match="max_corrected_linf"):
        enforce_default_parity_gates(bad)


def test_parity_gate_fails_just_above_p95_corrected_linf() -> None:
    above = math.nextafter(1e-6, math.inf)
    bad = _ok_summary(p95_corrected_linf=above)
    v = list_default_parity_gate_violations(bad)
    assert any("p95_corrected_linf" in line for line in v)
    with pytest.raises(ParityGateError, match="p95_corrected_linf"):
        enforce_default_parity_gates(bad)


def test_parity_gate_lists_all_violations_at_once() -> None:
    bad = _ok_summary(
        action_match_rate=0.5,
        active_constraints_match_rate=0.0,
        max_corrected_linf=1.0,
        p95_corrected_linf=1.0,
        max_corrected_l2=1.0,
    )
    violations = list_default_parity_gate_violations(bad)
    assert len(violations) == 5
    with pytest.raises(ParityGateError) as excinfo:
        enforce_default_parity_gates(bad)
    body = str(excinfo.value)
    assert "Action match rate" in body
    assert "max_corrected_linf" in body
    assert "p95_corrected_linf" in body


class _MatchingFixtureShield:
    def reset_episode(self) -> None:
        pass

    def choose_action(self, *, q_values, action_space, context):
        corrected = np.array([0.0, 1.0, 0.0, 0.0], dtype=float)
        proposed = np.array([0.02, 0.95, 0.02, 0.01], dtype=float)

        class Decision:
            action_name = "turn_right"
            proposed_distribution = proposed
            corrected_distribution = corrected
            projection = ProjectionResult(
                proposed_action=proposed,
                corrected_action=corrected,
                intervened=True,
                intervention_norm=float(np.linalg.norm(corrected - proposed)),
                solver_status="optimal",
                objective_value=0.0,
                active_constraints=["turn_feasibility"],
            )

        return Decision


def test_parity_replay_multi_step_fixture_shape(tmp_path: Path) -> None:
    """Two reference-arm steps: summary aggregates to total_steps==2 and perfect match (gate constants)."""
    line = Path("tests/fixtures/parity_reference/episodes.jsonl").read_text(encoding="utf-8").splitlines()[2]
    ep = json.loads(line)
    step0 = dict(ep["steps"][0])
    step0["step"] = 0
    step1 = dict(ep["steps"][0])
    step1["step"] = 1
    ep2 = dict(ep)
    ep2["steps"] = [step0, step1]
    ep2["num_steps"] = 2
    ep2["total_reward"] = 2.0
    ep2["num_interventions"] = 2
    p = tmp_path / "episodes.jsonl"
    p.write_text(json.dumps(ep2) + "\n", encoding="utf-8")

    steps, summary = compare_against_reference(
        episodes_jsonl=p,
        candidate_shield=_MatchingFixtureShield(),
        reference_arm_label="shielded-rules-plus-geometry",
    )
    assert len(steps) == 2
    assert summary.total_steps == 2
    assert summary.action_match_rate == 1.0
    assert summary.max_corrected_linf == 0.0
    assert summary.p95_corrected_linf == 0.0
    assert summary.active_constraints_match_rate == 1.0
    enforce_default_parity_gates(summary)
