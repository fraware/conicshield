from __future__ import annotations

import numpy as np
import pytest

from conicshield.specs.schema import (
    BoxConstraint,
    ProgressConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)
from conicshield.specs.shield_qp import objective_pq, parse_safety_spec_for_shield


def test_parse_shield_spec_matches_inter_sim_order() -> None:
    spec = SafetySpec(
        spec_id="t",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[1]),
            BoxConstraint(lower=[0.0] * 4, upper=[1.0, 1.0, 0.0, 0.0]),
            RateConstraint(max_delta=[0.5] * 4),
        ],
    )
    data = parse_safety_spec_for_shield(spec)
    assert data.n == 4
    assert data.simplex_total == 1.0
    assert data.allowed_mask[1]
    assert not data.allowed_mask[0]
    assert data.upper[2] == 0.0
    assert data.max_delta[0] == 0.5


def test_objective_pq_diagonal() -> None:
    n = 4
    p = np.array([1.0, 0.0, 0.0, 0.0])
    p_mat, q = objective_pq(p, None, policy_weight=2.0, reference_weight=0.0, n=n)
    assert p_mat.shape == (4, 4)
    assert np.allclose(np.diag(p_mat), 4.0)
    assert np.allclose(q, -4.0 * p)


def test_unsupported_constraint_raises() -> None:
    spec = SafetySpec(
        spec_id="bad",
        action_dim=2,
        constraints=[SimplexConstraint(total=1.0), ProgressConstraint(min_progress=0.1)],
    )
    with pytest.raises(NotImplementedError):
        parse_safety_spec_for_shield(spec)


def test_objective_pq_with_reference() -> None:
    n = 3
    p = np.array([0.2, 0.5, 0.3])
    r = np.array([0.0, 1.0, 0.0])
    p_mat, q = objective_pq(p, r, policy_weight=1.0, reference_weight=1.0, n=n)
    assert np.allclose(np.diag(p_mat), 4.0)
    assert np.allclose(q, -2.0 * (p + r))
