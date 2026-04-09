from __future__ import annotations

from pathlib import Path

import numpy as np

from conicshield.core.result import ProjectionResult
from conicshield.parity.gates import enforce_default_parity_gates
from conicshield.parity.replay import compare_against_reference


class _MatchingCorrectedMismatchedProposedShield:
    """Corrected distribution and action match fixture; proposed differs strongly (uniform)."""

    def reset_episode(self) -> None:
        pass

    def choose_action(self, *, q_values, action_space, context):
        corrected = np.array([0.0, 1.0, 0.0, 0.0], dtype=float)
        proposed = np.array([0.25, 0.25, 0.25, 0.25], dtype=float)

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


def test_parity_proposed_linf_positive_corrected_linf_zero_still_passes_gates() -> None:
    steps, summary = compare_against_reference(
        episodes_jsonl=Path("tests/fixtures/parity_reference/episodes.jsonl"),
        candidate_shield=_MatchingCorrectedMismatchedProposedShield(),
        reference_arm_label="shielded-rules-plus-geometry",
    )
    assert len(steps) == 1
    assert steps[0].corrected_linf == 0.0
    assert steps[0].proposed_linf > 0.1
    enforce_default_parity_gates(summary)


def test_compare_against_reference_summary_is_deterministic(tmp_path: Path) -> None:
    src = Path("tests/fixtures/parity_reference/episodes.jsonl").read_text(encoding="utf-8")
    p = tmp_path / "episodes.jsonl"
    p.write_text(src, encoding="utf-8")
    shield = _MatchingCorrectedMismatchedProposedShield()
    _, s1 = compare_against_reference(episodes_jsonl=p, candidate_shield=shield)
    shield2 = _MatchingCorrectedMismatchedProposedShield()
    _, s2 = compare_against_reference(episodes_jsonl=p, candidate_shield=shield2)
    assert s1.as_dict() == s2.as_dict()
