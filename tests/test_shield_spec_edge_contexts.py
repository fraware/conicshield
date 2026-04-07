from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from conicshield.adapters.inter_sim_rl.context_validate import validate_shield_context_dict
from conicshield.adapters.inter_sim_rl.shield import CANONICAL_ACTION_SPACE, InterSimConicShield
from conicshield.bench.passthrough_projector import PassthroughProjector
from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions
from conicshield.core.solver_factory import Backend
from conicshield.specs.compiler import SolverOptions
from conicshield.specs.schema import SafetySpec


def _passthrough_factory(
    _spec: SafetySpec,
    _backend: Backend,
    _solver_options: SolverOptions | None,
    _native_options: NativeMoreauCompiledOptions | None,
) -> PassthroughProjector:
    return PassthroughProjector()


def _ctx(
    *,
    allowed: list[str],
    blocked: list[str],
    hazard: float,
    bounds: dict[str, float] | None = None,
) -> dict[str, Any]:
    if bounds is None:
        allowed_set = set(allowed)
        bounds = {a: (1.0 if a in allowed_set else 0.0) for a in CANONICAL_ACTION_SPACE}
    return {
        "allowed_actions": allowed,
        "blocked_actions": blocked,
        "action_upper_bounds": bounds,
        "rule_choice": "right",
        "previous_instruction": None,
        "hazard_score": hazard,
        "transition_candidates": [],
    }


@pytest.mark.parametrize(
    ("label", "payload"),
    [
        (
            "single_feasible",
            _ctx(allowed=["turn_right"], blocked=["turn_left", "go_straight", "turn_back"], hazard=0.0),
        ),
        (
            "all_feasible_high_hazard",
            _ctx(
                allowed=["turn_left", "turn_right", "go_straight", "turn_back"],
                blocked=[],
                hazard=0.99,
            ),
        ),
        (
            "empty_allowed_all_blocked_fallback",
            _ctx(
                allowed=[],
                blocked=["turn_left", "turn_right", "go_straight", "turn_back"],
                hazard=0.2,
                bounds={a: 0.0 for a in CANONICAL_ACTION_SPACE},
            ),
        ),
    ],
)
def test_shield_passthrough_choose_action_finite(label: str, payload: dict[str, Any]) -> None:
    validate_shield_context_dict(payload)
    shield = InterSimConicShield(
        backend=Backend.CVXPY_MOREAU,
        use_geometry_prior=False,
        projector_factory=_passthrough_factory,
    )
    q = np.array([0.5, 1.0, 0.25, -0.25], dtype=float)
    decision = shield.choose_action(
        q_values=q,
        action_space=list(CANONICAL_ACTION_SPACE),
        context=payload,
    )
    assert decision.action_name in CANONICAL_ACTION_SPACE
    assert np.all(np.isfinite(decision.proposed_distribution))
    assert np.all(np.isfinite(decision.corrected_distribution))
