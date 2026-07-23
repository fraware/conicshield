"""Optional live tests for exact/smoothed backend gradients via Moreau."""

from __future__ import annotations

import sys

import numpy as np
import pytest

from conicshield.experimental.corpus.generate import load_all_scenarios
from conicshield.experimental.gradients.capability import CapabilityStatus
from conicshield.experimental.gradients.exact_backend import (
    _probe_vendor_compiled_backward,
    exact_backend_gradient,
)
from conicshield.experimental.gradients.modes import GradientMode
from conicshield.experimental.gradients.smoothed_backend import smoothed_backend_gradient
from conicshield.specs.schema import SafetySpec


@pytest.mark.skipif(sys.platform == "win32", reason="vendor Moreau unsupported on native Windows")
def test_exact_backend_gradient_live_or_fail_closed() -> None:
    caps = _probe_vendor_compiled_backward()
    if not caps.get("vendor_compiled_backward_api"):
        pytest.skip(f"CompiledSolver.backward unavailable: {caps}")

    scenario = next(s for s in load_all_scenarios() if s["family"] == "interior_feasible")
    spec = SafetySpec.model_validate(scenario["spec"])
    result = exact_backend_gradient(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
        compare_central_fd=True,
    )
    assert result.mode == GradientMode.EXACT_BACKEND_GRADIENT
    assert result.as_dict()["not_research_kkt"] is True
    assert result.status in (CapabilityStatus.AVAILABLE, CapabilityStatus.UNAVAILABLE)
    if result.available:
        assert result.jacobian is not None
        assert result.jacobian.shape[0] == result.jacobian.shape[1]
        assert result.agreement_vs_central_fd is not None
        assert result.agreement_vs_central_fd <= 1e-2


@pytest.mark.skipif(sys.platform == "win32", reason="vendor Moreau unsupported on native Windows")
def test_smoothed_backend_gradient_live_or_fail_closed() -> None:
    caps = _probe_vendor_compiled_backward()
    if not caps.get("vendor_compiled_backward_api"):
        pytest.skip(f"CompiledSolver.backward unavailable: {caps}")

    scenario = next(s for s in load_all_scenarios() if s["family"] == "interior_feasible")
    spec = SafetySpec.model_validate(scenario["spec"])
    sm = smoothed_backend_gradient(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
        smoothing_parameter=1e-2,
        compare_central_fd=True,
        compare_exact_backend=True,
    )
    assert sm.mode == GradientMode.SMOOTHED_BACKEND_GRADIENT
    assert sm.status in (CapabilityStatus.AVAILABLE, CapabilityStatus.UNAVAILABLE)
    assert sm.smoothing_parameter == 1e-2
    if sm.available:
        assert sm.jacobian is not None
        assert sm.agreement_vs_smoothed_central_fd is not None
        assert sm.agreement_vs_smoothed_central_fd <= 5e-2
