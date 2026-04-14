"""Native batched softmax projection on the inter-sim shield path (vendor Moreau)."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("moreau")

from conicshield.adapters.inter_sim_rl.shield import CANONICAL_ACTION_SPACE, InterSimConicShield
from conicshield.core.solver_factory import Backend


def _minimal_context() -> dict[str, object]:
    return {
        "allowed_actions": list(CANONICAL_ACTION_SPACE),
        "blocked_actions": [],
        "action_upper_bounds": dict.fromkeys(CANONICAL_ACTION_SPACE, 1.0),
        "rule_choice": "right",
        "previous_instruction": None,
        "hazard_score": 0.0,
        "transition_candidates": [],
    }


@pytest.mark.requires_moreau
@pytest.mark.vendor_moreau
@pytest.mark.solver
def test_project_softmax_batch_first_row_matches_sequential() -> None:
    """Row 0 of a batched native projection matches sequential ``project`` for that row."""
    moreau = pytest.importorskip("moreau")
    if not hasattr(moreau, "CompiledSolver"):
        pytest.skip("moreau.CompiledSolver not available")

    shield = InterSimConicShield(backend=Backend.NATIVE_MOREAU, use_geometry_prior=False)
    ctx = _minimal_context()
    q = np.array([0.85, 0.1, 0.03, 0.02], dtype=np.float64)
    from conicshield.adapters.inter_sim_rl.shield import stable_softmax

    p0 = stable_softmax(q)
    p1 = stable_softmax(q * 0.9)
    batch_in = np.stack([p0, p1], axis=0)

    out_batch = shield.project_softmax_batch(proposed_softmax_rows=batch_in, context=ctx)
    assert out_batch.shape == batch_in.shape

    shield.reset_episode()
    dec0 = shield.choose_action(q_values=q, action_space=list(CANONICAL_ACTION_SPACE), context=ctx)
    np.testing.assert_allclose(out_batch[0], dec0.corrected_distribution, rtol=1e-5, atol=1e-5)
