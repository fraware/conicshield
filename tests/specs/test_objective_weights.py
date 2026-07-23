"""S1 objective weight validation and IR parsing tests."""

from __future__ import annotations

import numpy as np
import pytest

from conicshield.specs.errors import InvalidObjectiveWeightError
from conicshield.specs.schema import (
    BoxConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)
from conicshield.specs.shield_qp import (
    objective_pq,
    parse_safety_spec_for_shield,
    validate_objective_weights,
)


def test_validate_objective_weights_accepts_positive_sum() -> None:
    pw, rw = validate_objective_weights(1.0, 0.5, reference_present=True)
    assert pw == 1.0
    assert rw == 0.5


def test_negative_policy_weight_raises() -> None:
    with pytest.raises(InvalidObjectiveWeightError):
        validate_objective_weights(-0.1, 1.0, reference_present=True)


def test_negative_reference_weight_raises() -> None:
    with pytest.raises(InvalidObjectiveWeightError):
        objective_pq(
            np.array([0.5, 0.5]),
            np.array([1.0, 0.0]),
            policy_weight=1.0,
            reference_weight=-0.5,
            n=2,
        )


def test_zero_combined_weight_raises() -> None:
    with pytest.raises(InvalidObjectiveWeightError):
        objective_pq(
            np.array([0.5, 0.5]),
            None,
            policy_weight=0.0,
            reference_weight=0.0,
            n=2,
        )


def test_nonfinite_weights_raise() -> None:
    with pytest.raises(InvalidObjectiveWeightError):
        validate_objective_weights(float("nan"), 1.0, reference_present=False)
    with pytest.raises(InvalidObjectiveWeightError):
        validate_objective_weights(1.0, float("inf"), reference_present=True)


def test_reference_absent_zeros_reference_weight_for_sum_check() -> None:
    # Declared reference_weight is ignored for the sum when no reference vector.
    pw, rw = validate_objective_weights(1.0, 5.0, reference_present=False)
    assert pw == 1.0
    assert rw == 0.0


def test_parse_ir_encodes_turn_box_rate() -> None:
    spec = SafetySpec(
        spec_id="ir",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[1]),
            BoxConstraint(lower=[-0.1, 0.0, 0.0, 0.0], upper=[1.0, 1.0, 0.0, 0.0]),
            RateConstraint(max_delta=[0.5, 0.5, 0.5, 0.5]),
        ],
    )
    data = parse_safety_spec_for_shield(spec)
    assert data.n == 4
    assert data.simplex_total == 1.0
    assert bool(data.allowed_mask[1])
    assert not bool(data.allowed_mask[0])
    assert data.lower[0] == pytest.approx(-0.1)
    assert data.upper[2] == pytest.approx(0.0)
    assert data.max_delta[0] == pytest.approx(0.5)


def test_parse_does_not_silently_allow_all_when_mask_empty() -> None:
    """Defense-in-depth: IR parse refuses empty masks without fail-safe.

    SafetySpec construction already rejects empty turn feasibility; this uses
    model_construct to assert the parser itself never restores all-True.
    """
    from conicshield.specs.errors import MissingFailSafePolicyError

    spec = SafetySpec.model_construct(
        spec_id="empty-ir",
        version="0.1.0",
        action_dim=2,
        slack_weight=10.0,
        fail_safe_policy=None,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[]),
        ],
    )
    with pytest.raises(MissingFailSafePolicyError):
        parse_safety_spec_for_shield(spec)
