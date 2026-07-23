"""Frontier sweeps and local-global consistency tests."""

from __future__ import annotations

import numpy as np

from conicshield.experimental.corpus.generate import load_all_scenarios
from conicshield.experimental.frontiers.local_global import run_local_global_consistency
from conicshield.experimental.frontiers.sweeps import (
    BATCH_EMULATION_SEQUENTIAL,
    FRONTIER_PARAMETERS,
    compute_pareto_indices,
    run_frontier_sweep_scaffold,
)
from conicshield.specs.schema import SafetySpec


def test_frontier_parameters_cover_directive() -> None:
    required = {
        "rate_limit",
        "hazard_multiplier",
        "geometry_prior_weight",
        "policy_weight",
        "reference_weight",
        "bound_margins",
        "robustness_margins",
        "fallback_thresholds",
    }
    assert required <= set(FRONTIER_PARAMETERS)


def test_frontier_sweep_batch_emulation_flag() -> None:
    scenario = load_all_scenarios()[0]
    spec = SafetySpec.model_validate(scenario["spec"])
    frontier = run_frontier_sweep_scaffold(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
    )
    assert frontier.batch_emulation == BATCH_EMULATION_SEQUENTIAL
    assert frontier.pareto_indices
    assert len(frontier.points) == 8  # 2x2x2 grid


def test_pareto_and_local_global() -> None:
    scenario = load_all_scenarios()[0]
    spec = SafetySpec.model_validate(scenario["spec"])
    frontier = run_frontier_sweep_scaffold(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
    )
    idxs = compute_pareto_indices(frontier.points)
    assert idxs == frontier.pareto_indices
    lg = run_local_global_consistency(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
        base_params={"policy_weight": 1.0, "rate_limit": 1.0},
        neighbor_params=[{"policy_weight": 1.2}, {"rate_limit": 0.7}],
    )
    assert lg.batch_emulation == BATCH_EMULATION_SEQUENTIAL
    assert len(lg.flags) == 2
    assert all(f.flag in {"ok", "active_set_change", "nonlinearity", "unreliable_sensitivity"} for f in lg.flags)
