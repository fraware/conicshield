"""CS-SOLVER-005: invalid objective weights must raise typed errors (no silent coercion)."""

from __future__ import annotations

import numpy as np
import pytest

from conicshield.specs.errors import InvalidObjectiveWeightError
from conicshield.specs.shield_qp import objective_pq, validate_objective_weights


def test_negative_reference_weight_must_raise() -> None:
    p = np.array([0.5, 0.5], dtype=np.float64)
    r = np.array([1.0, 0.0], dtype=np.float64)
    with pytest.raises(InvalidObjectiveWeightError):
        objective_pq(p, r, policy_weight=1.0, reference_weight=-0.5, n=2)


def test_nonpositive_combined_weight_must_raise() -> None:
    p = np.array([0.5, 0.5], dtype=np.float64)
    with pytest.raises(InvalidObjectiveWeightError):
        objective_pq(p, None, policy_weight=0.0, reference_weight=0.0, n=2)


def test_negative_policy_weight_must_raise() -> None:
    with pytest.raises(InvalidObjectiveWeightError):
        validate_objective_weights(-1.0, 1.0, reference_present=True)


def test_valid_weights_unchanged() -> None:
    p = np.array([0.5, 0.5], dtype=np.float64)
    r = np.array([1.0, 0.0], dtype=np.float64)
    p_mat, q = objective_pq(p, r, policy_weight=1.0, reference_weight=1.0, n=2)
    assert np.allclose(np.diag(p_mat), 4.0)
    assert np.allclose(q, -2.0 * (p + r))
