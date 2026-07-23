"""S1 specification schema validation tests."""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from conicshield.specs.errors import (
    ContradictoryConstraintError,
    DimensionMismatchError,
    DuplicateConstraintError,
    MissingFailSafePolicyError,
    NoAdmissibleActionError,
)
from conicshield.specs.schema import (
    BoxConstraint,
    FailSafePolicy,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)


def _raises_typed_or_validation(*exc_types: type[BaseException]):
    return pytest.raises((*exc_types, ValidationError))


def test_box_vector_lengths_must_match_action_dim() -> None:
    with _raises_typed_or_validation(DimensionMismatchError):
        SafetySpec(
            spec_id="dim-box",
            action_dim=3,
            constraints=[
                SimplexConstraint(total=1.0),
                BoxConstraint(lower=[0.0, 0.0], upper=[1.0, 1.0]),
            ],
        )


def test_rate_vector_length_must_match_action_dim() -> None:
    with _raises_typed_or_validation(DimensionMismatchError):
        SafetySpec(
            spec_id="dim-rate",
            action_dim=2,
            constraints=[
                SimplexConstraint(total=1.0),
                RateConstraint(max_delta=[0.1, 0.1, 0.1]),
            ],
        )


def test_turn_index_out_of_range() -> None:
    with _raises_typed_or_validation(DimensionMismatchError):
        SafetySpec(
            spec_id="dim-turn",
            action_dim=2,
            constraints=[
                SimplexConstraint(total=1.0),
                TurnFeasibilityConstraint(allowed_actions=[0, 2]),
            ],
        )


def test_duplicate_simplex_rejected() -> None:
    with _raises_typed_or_validation(DuplicateConstraintError):
        SafetySpec(
            spec_id="dup-simplex",
            action_dim=2,
            constraints=[SimplexConstraint(total=1.0), SimplexConstraint(total=1.0)],
        )


def test_duplicate_box_rejected() -> None:
    with _raises_typed_or_validation(DuplicateConstraintError):
        SafetySpec(
            spec_id="dup-box",
            action_dim=2,
            constraints=[
                SimplexConstraint(total=1.0),
                BoxConstraint(lower=[0.0, 0.0], upper=[1.0, 1.0]),
                BoxConstraint(lower=[0.0, 0.0], upper=[0.5, 0.5]),
            ],
        )


def test_duplicate_rate_rejected() -> None:
    with _raises_typed_or_validation(DuplicateConstraintError):
        SafetySpec(
            spec_id="dup-rate",
            action_dim=2,
            constraints=[
                SimplexConstraint(total=1.0),
                RateConstraint(max_delta=[0.1, 0.1]),
                RateConstraint(max_delta=[0.2, 0.2]),
            ],
        )


def test_nonfinite_box_bounds_rejected() -> None:
    with pytest.raises(ValidationError):
        BoxConstraint(lower=[0.0, -math.inf], upper=[1.0, 1.0])
    with pytest.raises(ValidationError):
        BoxConstraint(lower=[0.0, math.nan], upper=[1.0, 1.0])


def test_contradictory_lower_sum_exceeds_simplex() -> None:
    with _raises_typed_or_validation(ContradictoryConstraintError):
        SafetySpec(
            spec_id="contra-lower",
            action_dim=2,
            constraints=[
                SimplexConstraint(total=1.0),
                BoxConstraint(lower=[0.6, 0.6], upper=[1.0, 1.0]),
            ],
        )


def test_contradictory_upper_sum_below_simplex() -> None:
    with _raises_typed_or_validation(ContradictoryConstraintError):
        SafetySpec(
            spec_id="contra-upper",
            action_dim=2,
            constraints=[
                SimplexConstraint(total=1.0),
                BoxConstraint(lower=[0.0, 0.0], upper=[0.2, 0.2]),
            ],
        )


def test_empty_admissible_requires_fail_safe_policy() -> None:
    with _raises_typed_or_validation(MissingFailSafePolicyError):
        SafetySpec(
            spec_id="empty-no-policy",
            action_dim=2,
            constraints=[
                SimplexConstraint(total=1.0),
                TurnFeasibilityConstraint(allowed_actions=[]),
            ],
        )


def test_empty_admissible_with_reject_fail_safe() -> None:
    with _raises_typed_or_validation(NoAdmissibleActionError):
        SafetySpec(
            spec_id="empty-reject",
            action_dim=2,
            fail_safe_policy=FailSafePolicy.REJECT,
            constraints=[
                SimplexConstraint(total=1.0),
                TurnFeasibilityConstraint(allowed_actions=[]),
            ],
        )


def test_one_admissible_action_ok() -> None:
    spec = SafetySpec(
        spec_id="one-ok",
        action_dim=3,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[1]),
            BoxConstraint(lower=[0.0, 0.0, 0.0], upper=[1.0, 1.0, 1.0]),
        ],
    )
    assert spec.action_dim == 3


def test_negative_and_asymmetric_box_ok() -> None:
    spec = SafetySpec(
        spec_id="neg-box",
        action_dim=3,
        constraints=[
            SimplexConstraint(total=1.0),
            BoxConstraint(lower=[-0.25, 0.0, 0.1], upper=[0.8, 1.5, 1.0]),
        ],
    )
    box = next(c for c in spec.constraints if isinstance(c, BoxConstraint))
    assert box.lower[0] == pytest.approx(-0.25)
    assert box.upper[1] == pytest.approx(1.5)


def test_rate_allows_positive_infinity() -> None:
    spec = SafetySpec(
        spec_id="rate-inf",
        action_dim=2,
        constraints=[
            SimplexConstraint(total=1.0),
            RateConstraint(max_delta=[0.1, math.inf]),
        ],
    )
    rate = next(c for c in spec.constraints if isinstance(c, RateConstraint))
    assert math.isinf(rate.max_delta[1])
