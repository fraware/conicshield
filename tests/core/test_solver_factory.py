"""Factory surface for single vs batched native projectors."""

from __future__ import annotations

from conicshield.core.moreau_batched import NativeMoreauCompiledBatchProjector
from conicshield.core.moreau_compiled import NativeMoreauCompiledProjector
from conicshield.core.solver_factory import Backend, create_batch_projector, create_projector
from conicshield.specs.schema import (
    BoxConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)


def _spec() -> SafetySpec:
    return SafetySpec(
        spec_id="factory/test",
        version="0.1.0",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[0, 1, 2, 3]),
            BoxConstraint(lower=[0.0] * 4, upper=[1.0] * 4),
            RateConstraint(max_delta=[0.9] * 4),
        ],
    )


def test_create_projector_native_is_single() -> None:
    p = create_projector(spec=_spec(), backend=Backend.NATIVE_MOREAU)
    assert isinstance(p, NativeMoreauCompiledProjector)


def test_create_batch_projector_is_batched_native() -> None:
    p = create_batch_projector(spec=_spec(), backend=Backend.NATIVE_MOREAU)
    assert isinstance(p, NativeMoreauCompiledBatchProjector)


def test_create_batch_projector_rejects_cvxpy_backend() -> None:
    try:
        create_batch_projector(spec=_spec(), backend=Backend.CVXPY_MOREAU)
    except ValueError as exc:
        assert "native_moreau" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")
