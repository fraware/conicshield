"""CS-SOLVER-005: invalid objective weights silently coerced."""

from __future__ import annotations

import numpy as np
import pytest

from conicshield.specs.shield_qp import objective_pq


@pytest.mark.xfail(
    strict=True,
    reason="CS-SOLVER-005: negative reference_weight is clipped to 0 instead of raising",
)
def test_negative_reference_weight_must_raise() -> None:
    p = np.array([0.5, 0.5], dtype=np.float64)
    r = np.array([1.0, 0.0], dtype=np.float64)
    with pytest.raises((ValueError, TypeError)):
        objective_pq(p, r, policy_weight=1.0, reference_weight=-0.5, n=2)


@pytest.mark.xfail(
    strict=True,
    reason="CS-SOLVER-005: nonpositive combined weight is replaced with 1e-12 instead of raising",
)
def test_nonpositive_combined_weight_must_raise() -> None:
    p = np.array([0.5, 0.5], dtype=np.float64)
    with pytest.raises((ValueError, TypeError)):
        objective_pq(p, None, policy_weight=0.0, reference_weight=0.0, n=2)


def test_current_defect_coerces_negative_reference_weight() -> None:
    """Evidence fixture: documents present coercion (not the desired end state)."""
    p = np.array([0.5, 0.5], dtype=np.float64)
    r = np.array([1.0, 0.0], dtype=np.float64)
    p_mat_neg, q_neg = objective_pq(p, r, policy_weight=1.0, reference_weight=-0.5, n=2)
    p_mat_zero, q_zero = objective_pq(p, r, policy_weight=1.0, reference_weight=0.0, n=2)
    assert np.allclose(p_mat_neg, p_mat_zero)
    assert np.allclose(q_neg, q_zero)


def test_current_defect_coerces_nonpositive_scale_to_1e_12() -> None:
    p = np.array([0.5, 0.5], dtype=np.float64)
    p_mat, q = objective_pq(p, None, policy_weight=0.0, reference_weight=0.0, n=2)
    assert np.allclose(np.diag(p_mat), 2.0 * 1e-12)
    assert np.allclose(q, 0.0)
