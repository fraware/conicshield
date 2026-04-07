from typing import Any

import numpy as np

from conicshield.adapters.inter_sim_rl.geometry_prior import (
    GeometryPriorConfig,
    infer_geometry_prior,
)


def test_geometry_prior_prefers_right_when_heading_plus_90_branch_exists() -> None:
    context = {
        "current_heading_deg": 0.0,
        "branch_bearings_deg": [92.0, 200.0],
        "hazard_score": 0.8,
    }
    prior, weight = infer_geometry_prior(context=context)
    assert prior is not None
    assert np.isclose(np.sum(prior), 1.0)
    assert prior[1] == max(prior)
    assert weight > 0.4


def test_geometry_prior_falls_back_uniformly_when_geometry_missing() -> None:
    context: dict[str, Any] = {
        "current_heading_deg": None,
        "branch_bearings_deg": [],
        "hazard_score": 0.1,
    }
    prior, weight = infer_geometry_prior(context=context, config=GeometryPriorConfig())
    assert prior is not None
    assert np.isclose(np.sum(prior), 1.0)
    assert np.allclose(prior, np.full(4, 0.25))
    assert weight == 0.0
