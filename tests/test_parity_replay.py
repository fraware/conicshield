import json
from pathlib import Path

import numpy as np
import pytest

from conicshield.core.result import ProjectionResult
from conicshield.parity.gates import enforce_default_parity_gates
from conicshield.parity.replay import compare_against_reference


class FakeShield:
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

        return Decision()


class FakeShieldReorderedConstraints:
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
                active_constraints=["geometry_prior", "turn_feasibility"],
            )

        return Decision()


def test_parity_replay_matches_fixture() -> None:
    steps, summary = compare_against_reference(
        episodes_jsonl=Path("tests/fixtures/parity_reference/episodes.jsonl"),
        candidate_shield=FakeShield(),
        reference_arm_label="shielded-rules-plus-geometry",
    )
    assert len(steps) == 1
    assert steps[0].action_match is True
    assert steps[0].corrected_linf == 0.0
    assert summary.max_corrected_linf == 0.0
    enforce_default_parity_gates(summary)


def test_parity_active_constraints_match_is_order_insensitive(tmp_path: Path) -> None:
    line = Path("tests/fixtures/parity_reference/episodes.jsonl").read_text(encoding="utf-8").splitlines()[2]
    ep = json.loads(line)
    step = dict(ep["steps"][0])
    step["active_constraints"] = ["turn_feasibility", "geometry_prior"]
    ep = dict(ep)
    ep["steps"] = [step]
    p = tmp_path / "episodes.jsonl"
    p.write_text(json.dumps(ep) + "\n", encoding="utf-8")
    steps, summary = compare_against_reference(
        episodes_jsonl=p,
        candidate_shield=FakeShieldReorderedConstraints(),
        reference_arm_label="shielded-rules-plus-geometry",
    )
    assert steps[0].active_constraints_match is True
    enforce_default_parity_gates(summary)


def test_parity_no_reference_arm_raises(tmp_path: Path) -> None:
    line = Path("tests/fixtures/parity_reference/episodes.jsonl").read_text(encoding="utf-8").splitlines()[0]
    p = tmp_path / "episodes.jsonl"
    p.write_text(line.strip() + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="No reference-arm"):
        compare_against_reference(
            episodes_jsonl=p,
            candidate_shield=FakeShield(),
            reference_arm_label="shielded-rules-plus-geometry",
        )
