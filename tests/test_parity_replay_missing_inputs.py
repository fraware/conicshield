from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

from conicshield.core.result import ProjectionResult
from conicshield.parity.replay import compare_against_reference


class _OkShield:
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


def _fixture_episode() -> dict[str, Any]:
    line = Path("tests/fixtures/parity_reference/episodes.jsonl").read_text(encoding="utf-8").splitlines()[2]
    return cast(dict[str, Any], json.loads(line))


def _strip_shield_context_snapshot(ep: dict[str, Any]) -> dict[str, Any]:
    ep = json.loads(json.dumps(ep))
    ep["steps"] = [dict(ep["steps"][0])]
    meta = dict(ep["steps"][0]["metadata"])
    meta.pop("shield_context_snapshot", None)
    ep["steps"][0]["metadata"] = meta
    return ep


def _null_raw_q_values(ep: dict[str, Any]) -> dict[str, Any]:
    ep = json.loads(json.dumps(ep))
    ep["steps"] = [dict(ep["steps"][0])]
    ep["steps"][0]["raw_q_values"] = None
    return ep


def _strip_canonical_action_space(ep: dict[str, Any]) -> dict[str, Any]:
    ep = json.loads(json.dumps(ep))
    ep["steps"] = [dict(ep["steps"][0])]
    meta = dict(ep["steps"][0]["metadata"])
    meta.pop("canonical_action_space", None)
    ep["steps"][0]["metadata"] = meta
    return ep


@pytest.mark.parametrize(
    ("mutator", "expected_substring"),
    [
        (_strip_shield_context_snapshot, "shield_context_snapshot"),
        (_null_raw_q_values, "raw_q_values"),
        (_strip_canonical_action_space, "canonical_action_space"),
    ],
)
def test_compare_raises_missing_required_step_input(
    tmp_path: Path,
    mutator: Callable[[dict[str, Any]], dict[str, Any]],
    expected_substring: str,
) -> None:
    ep = mutator(_fixture_episode())
    p = tmp_path / "episodes.jsonl"
    p.write_text(json.dumps(ep) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=expected_substring):
        compare_against_reference(episodes_jsonl=p, candidate_shield=_OkShield())
