from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("cvxpy")
cvxpy = pytest.importorskip("cvxpy")
pytestmark = pytest.mark.vendor_moreau

if not hasattr(cvxpy, "MOREAU"):
    pytest.skip("cp.MOREAU not available (install moreau + cvxpylayers)", allow_module_level=True)

from conicshield.specs.compiler import CVXPYMoreauProjector, SolverOptions
from conicshield.specs.schema import (
    BoxConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)


@pytest.mark.solver
def test_cvxpy_moreau_projects_onto_simplex_with_mask() -> None:
    spec = SafetySpec(
        spec_id="solver-test",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[1]),
            BoxConstraint(lower=[0.0] * 4, upper=[1.0] * 4),
            RateConstraint(max_delta=[1.0] * 4),
        ],
    )
    proj = CVXPYMoreauProjector(spec=spec, options=SolverOptions(device="cpu", max_iter=800, verbose=False))
    proposed = np.array([0.9, 0.05, 0.03, 0.02], dtype=np.float64)
    prev = np.full(4, 0.25, dtype=np.float64)
    try:
        result = proj.project(proposed, prev, policy_weight=1.0, reference_weight=0.0)
    except cvxpy.error.SolverError as exc:
        if "moreau" in str(exc).lower():
            pytest.skip(f"MOREAU solver not available to CVXPY: {exc}")
        raise
    except RuntimeError as exc:
        msg = str(exc).lower()
        if "license" in msg or "key" in msg:
            pytest.skip(f"Moreau license not available: {exc}")
        raise
    assert result.corrected_action.shape == (4,)
    assert abs(float(np.sum(result.corrected_action)) - 1.0) < 1e-5
    assert result.corrected_action[0] < 1e-5
    assert result.corrected_action[1] > 1.0 - 1e-4
    assert result.solver_status
    if result.iterations is not None:
        assert result.iterations >= 1
