"""§7.1 parity replay invariants (step counts, reference-arm filtering)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from conicshield.core.result import ProjectionResult
from conicshield.parity.replay import compare_against_reference


def _count_reference_steps(episodes_path: Path, arm: str) -> int:
    n = 0
    for line in episodes_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ep = json.loads(line)
        if ep["arm_label"] == arm:
            n += len(ep["steps"])
    return n


def test_compare_total_steps_matches_reference_arm_step_count() -> None:
    path = Path("tests/fixtures/parity_reference/episodes.jsonl")
    arm = "shielded-rules-plus-geometry"
    expected = _count_reference_steps(path, arm)

    class _MatchShield:
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

    steps, summary = compare_against_reference(
        episodes_jsonl=path,
        candidate_shield=_MatchShield(),
        reference_arm_label=arm,
    )
    assert summary.total_steps == expected
    assert len(steps) == expected


def test_compare_step_index_monotonic_per_episode(tmp_path) -> None:
    class _MatchShield:
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
                    intervention_norm=0.0,
                    solver_status="optimal",
                    objective_value=0.0,
                    active_constraints=["turn_feasibility"],
                )

            return Decision

    line = Path("tests/fixtures/parity_reference/episodes.jsonl").read_text(encoding="utf-8").splitlines()[2]
    ep = json.loads(line)
    step0 = dict(ep["steps"][0])
    step0["step"] = 0
    step1 = dict(ep["steps"][0])
    step1["step"] = 1
    ep2 = dict(ep)
    ep2["steps"] = [step0, step1]
    ep2["num_steps"] = 2
    p2 = Path(tmp_path) / "episodes.jsonl"
    p2.write_text(json.dumps(ep2) + "\n", encoding="utf-8")
    rows, _ = compare_against_reference(
        episodes_jsonl=p2,
        candidate_shield=_MatchShield(),
        reference_arm_label="shielded-rules-plus-geometry",
    )
    assert [r.step for r in rows] == [0, 1]
