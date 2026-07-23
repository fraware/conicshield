"""FD metrics, dual-pressure, and observatory tests."""

from __future__ import annotations

import numpy as np

from conicshield.experimental.corpus.generate import load_all_scenarios
from conicshield.experimental.gradients.capability import CapabilityStatus
from conicshield.experimental.gradients.dual_pressure import correlate_dual_pressure, normalize_dual_pressure
from conicshield.experimental.gradients.exact_backend import exact_backend_gradient
from conicshield.experimental.gradients.finite_difference import (
    central_finite_difference_jacobian,
    directional_derivative,
    fd_agreement_metric,
    one_sided_finite_difference_jacobian,
)
from conicshield.experimental.gradients.observatory import (
    observe_proposed_action_fd,
    render_observatory_report_markdown,
)
from conicshield.experimental.gradients.smoothed_backend import smoothed_backend_gradient
from conicshield.specs.schema import SafetySpec


def test_exact_smoothed_fail_closed_without_problem_data() -> None:
    ex = exact_backend_gradient()
    sm = smoothed_backend_gradient()
    assert ex.available is False
    assert sm.available is False
    assert ex.status == CapabilityStatus.UNAVAILABLE
    assert sm.status == CapabilityStatus.UNAVAILABLE


def test_fd_metrics_and_directional() -> None:
    def f(x: np.ndarray) -> np.ndarray:
        return np.array([x[0] + 2 * x[1], x[0] ** 2], dtype=np.float64)

    x = np.array([1.0, 0.5], dtype=np.float64)
    c = central_finite_difference_jacobian(f, x, h=1e-6)
    o = one_sided_finite_difference_jacobian(f, x, h=1e-6)
    assert c.jacobian.shape == (2, 2)
    assert fd_agreement_metric(c.jacobian, o.jacobian) < 0.05
    d = directional_derivative(c.jacobian, np.array([1.0, 0.0]))
    assert d.shape == (2,)


def test_dual_pressure_correlation_caveat() -> None:
    report = normalize_dual_pressure(
        constraint_ids=("a", "b"),
        dual_values=np.array([2.0, -1.0]),
    )
    assert "causal" in report.interpretation_warning.lower()
    study = correlate_dual_pressure(
        max_abs_normalized_pressure=np.array([0.1, 0.5, 0.9, 0.2, 0.7]),
        intervention_size=np.array([0.0, 0.4, 0.8, 0.1, 0.6]),
        active_set_transition=np.array([0.0, 1.0, 1.0, 0.0, 1.0]),
    )
    assert study.n_samples == 5
    assert "causal" in study.interpretation_warning.lower()


def test_observatory_active_set_family() -> None:
    scenarios = [
        s for s in load_all_scenarios() if s["family"] == "active_set_transition_neighborhoods"
    ]
    assert len(scenarios) >= 10
    scenario = scenarios[0]
    spec = SafetySpec.model_validate(scenario["spec"])
    report = observe_proposed_action_fd(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
        scenario_id=scenario["scenario_id"],
    )
    assert report.metrics
    assert report.exact_backend["status"] in {
        CapabilityStatus.AVAILABLE.value,
        CapabilityStatus.UNAVAILABLE.value,
    }
    assert report.smoothed_backend["status"] in {
        CapabilityStatus.AVAILABLE.value,
        CapabilityStatus.UNAVAILABLE.value,
    }
    md = render_observatory_report_markdown([report])
    assert "Machine-filled summary" in md
    assert scenario["scenario_id"] in md
