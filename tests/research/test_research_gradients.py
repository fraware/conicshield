"""Research KKT and smoothed projection gradient adapters."""

from __future__ import annotations

import sys

import numpy as np
import pytest

from conicshield.experimental.corpus.generate import load_all_scenarios
from conicshield.experimental.gradients.capability import CapabilityStatus
from conicshield.experimental.gradients.exact_backend import exact_backend_gradient
from conicshield.experimental.gradients.kkt_research import exact_research_kkt_jacobian
from conicshield.experimental.gradients.modes import GradientMode
from conicshield.experimental.gradients.observatory import observe_proposed_action_fd
from conicshield.experimental.gradients.smoothed_backend import smoothed_backend_gradient
from conicshield.experimental.gradients.smoothed_research import smoothed_research_projection_jacobian
from conicshield.specs.schema import SafetySpec


def test_native_modes_fail_closed_without_problem_data() -> None:
    ex = exact_backend_gradient()
    sm = smoothed_backend_gradient()
    assert ex.available is False
    assert sm.available is False
    assert ex.status == CapabilityStatus.UNAVAILABLE
    assert sm.status == CapabilityStatus.UNAVAILABLE
    assert ex.as_dict()["not_research_kkt"] is True
    assert sm.as_dict()["not_research_smoothed"] is True
    assert GradientMode.EXACT_RESEARCH_KKT.value == "exact_research_kkt"
    assert GradientMode.SMOOTHED_RESEARCH_PROJECTION.value == "smoothed_research_projection"
    assert GradientMode.EXACT_RESEARCH_KKT != GradientMode.EXACT_BACKEND_GRADIENT


def test_kkt_research_on_interior_or_fail_closed() -> None:
    scenario = next(s for s in load_all_scenarios() if s["family"] == "interior_feasible")
    spec = SafetySpec.model_validate(scenario["spec"])
    result = exact_research_kkt_jacobian(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
        compare_central_fd=True,
    )
    assert result.mode == GradientMode.EXACT_RESEARCH_KKT
    assert result.as_dict()["not_native_moreau"] is True
    assert result.available or result.status == CapabilityStatus.UNAVAILABLE
    if result.available:
        assert result.jacobian is not None
        assert result.jacobian.shape[0] == result.jacobian.shape[1]
        assert result.status == CapabilityStatus.AVAILABLE
    else:
        assert result.status == CapabilityStatus.UNAVAILABLE
        assert result.jacobian is None


def test_smoothed_research_records_epsilon() -> None:
    scenario = next(s for s in load_all_scenarios() if s["family"] == "interior_feasible")
    spec = SafetySpec.model_validate(scenario["spec"])
    result = smoothed_research_projection_jacobian(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
        epsilon=1e-2,
        compare_fd=False,
    )
    assert result.mode == GradientMode.SMOOTHED_RESEARCH_PROJECTION
    assert result.smoothing_parameter == 1e-2
    if result.available:
        assert result.extra_solves >= 1
        assert result.jacobian is not None


def test_observatory_keeps_mode_separation() -> None:
    scenario = next(s for s in load_all_scenarios() if s["family"] == "active_set_transition_neighborhoods")
    spec = SafetySpec.model_validate(scenario["spec"])
    report = observe_proposed_action_fd(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
        include_research_gradients=True,
    )
    modes = {str(m.mode) for m in report.metrics}
    assert "central_finite_difference" in modes
    assert "exact_research_kkt" in modes
    # On Windows without Moreau, backends fail closed; with Moreau they may be available.
    assert report.exact_backend["status"] in {
        CapabilityStatus.AVAILABLE.value,
        CapabilityStatus.UNAVAILABLE.value,
    }
    assert report.smoothed_backend["status"] in {
        CapabilityStatus.AVAILABLE.value,
        CapabilityStatus.UNAVAILABLE.value,
    }
    note = report.as_dict()["mode_separation_note"].lower()
    assert "never" in note or "distinct" in note


@pytest.mark.skipif(sys.platform == "win32", reason="vendor Moreau unsupported on native Windows")
def test_smoothed_backend_records_epsilon_mechanism() -> None:
    from conicshield.experimental.gradients.exact_backend import (
        _probe_vendor_compiled_backward,
    )

    caps = _probe_vendor_compiled_backward()
    if not caps.get("vendor_compiled_backward_api"):
        pytest.skip(f"Moreau backward unavailable: {caps}")

    scenario = next(s for s in load_all_scenarios() if s["family"] == "interior_feasible")
    spec = SafetySpec.model_validate(scenario["spec"])
    result = smoothed_backend_gradient(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
        smoothing_parameter=1e-2,
        compare_central_fd=True,
        compare_exact_backend=True,
    )
    assert result.mode == GradientMode.SMOOTHED_BACKEND_GRADIENT
    assert result.smoothing_parameter == 1e-2
    assert result.as_dict()["mechanism"] == "softplus_inequality_softening_moreau_qp"
    assert result.status in (CapabilityStatus.AVAILABLE, CapabilityStatus.UNAVAILABLE)
    if result.available:
        assert result.jacobian is not None
        assert result.agreement_vs_smoothed_central_fd is not None
        assert result.agreement_vs_smoothed_central_fd <= 5e-2
