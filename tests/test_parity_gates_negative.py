from pathlib import Path

import numpy as np
import pytest

from conicshield.core.result import ProjectionResult
from conicshield.parity.gates import ParityGateError, enforce_default_parity_gates
from conicshield.parity.replay import compare_against_reference


class DivergentShield:
    def reset_episode(self) -> None:
        pass

    def choose_action(self, *, q_values, action_space, context):
        corrected = np.array([1.0, 0.0, 0.0, 0.0], dtype=float)
        proposed = np.array([0.25, 0.25, 0.25, 0.25], dtype=float)

        class Decision:
            action_name = "turn_left"
            proposed_distribution = proposed
            corrected_distribution = corrected
            projection = ProjectionResult(
                proposed_action=proposed,
                corrected_action=corrected,
                intervened=True,
                intervention_norm=1.0,
                solver_status="optimal",
                objective_value=0.0,
                active_constraints=["turn_feasibility"],
            )

        return Decision()


def test_parity_gate_fails_on_divergent_candidate() -> None:
    steps, summary = compare_against_reference(
        episodes_jsonl=Path("tests/fixtures/parity_reference/episodes.jsonl"),
        candidate_shield=DivergentShield(),
        reference_arm_label="shielded-rules-plus-geometry",
    )
    assert len(steps) == 1
    with pytest.raises(ParityGateError, match="Action match rate"):
        enforce_default_parity_gates(summary)


def test_parity_gate_error_includes_summary_metrics() -> None:
    steps, summary = compare_against_reference(
        episodes_jsonl=Path("tests/fixtures/parity_reference/episodes.jsonl"),
        candidate_shield=DivergentShield(),
        reference_arm_label="shielded-rules-plus-geometry",
    )
    assert len(steps) == 1
    with pytest.raises(ParityGateError) as excinfo:
        enforce_default_parity_gates(summary)
    msg = str(excinfo.value)
    assert "Parity summary (metrics):" in msg
    assert "action_match_rate" in msg
