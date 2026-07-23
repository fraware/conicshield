"""Finite-difference gradient infrastructure tests."""

from __future__ import annotations

import numpy as np

from conicshield.experimental.gradients.finite_difference import (
    central_finite_difference_jacobian,
    one_sided_finite_difference_jacobian,
)
from conicshield.experimental.gradients.modes import GradientMode
from conicshield.experimental.gradients.observatory import observe_proposed_action_fd
from conicshield.specs.schema import (
    BoxConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)


def test_central_fd_on_quadratic() -> None:
    a = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float64)

    def f(x: np.ndarray) -> np.ndarray:
        return (x - a) ** 2

    x0 = np.ones(4) / 4.0
    res = central_finite_difference_jacobian(f, x0, h=1e-6)
    assert res.mode == GradientMode.CENTRAL_FINITE_DIFFERENCE
    # Analytic diag(2*(x-a))
    analytic = np.diag(2.0 * (x0 - a))
    assert np.allclose(res.jacobian, analytic, atol=1e-6)


def test_one_sided_fd_mode_label() -> None:
    def f(x: np.ndarray) -> np.ndarray:
        return x * 2.0

    res = one_sided_finite_difference_jacobian(f, np.ones(3), h=1e-5)
    assert res.mode == GradientMode.ONE_SIDED_FINITE_DIFFERENCE
    assert np.allclose(res.jacobian, np.eye(3) * 2.0, atol=1e-4)


def test_observatory_fd_modes_distinct() -> None:
    spec = SafetySpec(
        spec_id="research/fd_test",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[0, 1, 2, 3]),
            BoxConstraint(lower=[0.0] * 4, upper=[1.0] * 4),
            RateConstraint(max_delta=[1.0] * 4),
        ],
    )
    report = observe_proposed_action_fd(
        spec=spec,
        proposed_action=np.array([0.4, 0.3, 0.2, 0.1]),
        previous_action=np.array([0.25] * 4),
        reference_action=np.array([0.25] * 4),
        h=1e-5,
    )
    modes = {m.mode for m in report.metrics}
    assert GradientMode.CENTRAL_FINITE_DIFFERENCE in modes
    assert GradientMode.ONE_SIDED_FINITE_DIFFERENCE in modes
    assert report.exact_backend["status"] in {"available", "unavailable"}
    assert report.smoothed_backend["status"] in {"available", "unavailable"}
