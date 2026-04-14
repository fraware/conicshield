"""Finite-difference sanity on the inter-sim native shield path (vendor)."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("moreau")

from conicshield.adapters.inter_sim_rl.shield import CANONICAL_ACTION_SPACE, InterSimConicShield
from conicshield.core.solver_factory import Backend


def _ctx() -> dict[str, object]:
    return {
        "allowed_actions": list(CANONICAL_ACTION_SPACE),
        "blocked_actions": [],
        "action_upper_bounds": dict.fromkeys(CANONICAL_ACTION_SPACE, 1.0),
        "rule_choice": "right",
        "previous_instruction": None,
        "hazard_score": 0.0,
        "transition_candidates": [],
    }


def _corrected0(q: np.ndarray) -> float:
    shield = InterSimConicShield(backend=Backend.NATIVE_MOREAU, use_geometry_prior=False)
    shield.reset_episode()
    d = shield.choose_action(q_values=q, action_space=list(CANONICAL_ACTION_SPACE), context=_ctx())
    return float(d.corrected_distribution[0])


@pytest.mark.requires_moreau
@pytest.mark.vendor_moreau
@pytest.mark.solver
def test_inter_sim_shield_first_output_component_fd_bounded() -> None:
    """Central FD on corrected[0] w.r.t. q[0] stays finite (shield path smooth enough for local sensitivity)."""
    moreau = pytest.importorskip("moreau")
    if not hasattr(moreau, "CompiledSolver"):
        pytest.skip("moreau.CompiledSolver not available")

    q = np.array([0.5, 0.2, 0.15, 0.15], dtype=np.float64)
    h = 1e-5
    q_plus = q.copy()
    q_plus[0] += h
    q_minus = q.copy()
    q_minus[0] -= h
    slope = (_corrected0(q_plus) - _corrected0(q_minus)) / (2.0 * h)
    assert np.isfinite(slope)
    assert abs(slope) < 1e7
