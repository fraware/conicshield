from __future__ import annotations

import numpy as np
import pytest

cvxpy = pytest.importorskip("cvxpy")
pytestmark = pytest.mark.vendor_moreau

from conicshield.adapters.inter_sim_rl.shield import CANONICAL_ACTION_SPACE, InterSimConicShield
from conicshield.core.solver_factory import Backend


@pytest.mark.solver
def test_shield_with_real_cvxpy_moreau_backend() -> None:
    shield = InterSimConicShield(
        backend=Backend.CVXPY_MOREAU,
        use_geometry_prior=False,
    )
    q_values = np.array([5.0, 1.0, 0.2, -3.0], dtype=float)
    context = {
        "rule_choice": "right",
        "previous_instruction": "turn_right",
        "allowed_actions": ["turn_right"],
        "blocked_actions": ["turn_left", "go_straight", "turn_back"],
        "action_upper_bounds": {
            "turn_left": 0.0,
            "turn_right": 1.0,
            "go_straight": 0.0,
            "turn_back": 0.0,
        },
        "hazard_score": 0.25,
    }
    try:
        decision = shield.choose_action(
            q_values=q_values,
            action_space=list(CANONICAL_ACTION_SPACE),
            context=context,
        )
    except cvxpy.error.SolverError as exc:
        if "moreau" in str(exc).lower():
            pytest.skip(f"MOREAU solver not available to CVXPY: {exc}")
        raise
    except RuntimeError as exc:
        if "license" in str(exc).lower() or "key" in str(exc).lower():
            pytest.skip(str(exc))
        raise
    assert decision.action_name == "turn_right"
    assert decision.projection.solver_status
    # CVXPY+MOREAU may omit iteration count on some solves; native path often fills it.
    if decision.projection.iterations is not None:
        assert decision.projection.iterations >= 1
    assert decision.projection.warm_started is not None
