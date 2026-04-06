from pathlib import Path

import numpy as np

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


def test_parity_replay_matches_fixture() -> None:
    steps, summary = compare_against_reference(
        episodes_jsonl=Path("tests/fixtures/parity_reference/episodes.jsonl"),
        candidate_shield=FakeShield(),
        reference_arm_label="shielded-rules-plus-geometry",
    )
    assert len(steps) == 1
    enforce_default_parity_gates(summary)
