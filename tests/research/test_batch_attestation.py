"""Batch attestation and local-global quality tests."""

from __future__ import annotations

import numpy as np

from conicshield.experimental.corpus.generate import load_all_scenarios
from conicshield.experimental.frontiers.local_global import run_local_global_consistency
from conicshield.experimental.frontiers.sweeps import (
    BATCH_EMULATION_SEQUENTIAL,
    probe_track1_hetero_batch_attestation,
    project_batch_sequential,
    run_frontier_sweep_scaffold,
)
from conicshield.specs.schema import SafetySpec


def test_batch_attestation_defaults_to_sequential() -> None:
    att = probe_track1_hetero_batch_attestation()
    # Public CI / Windows without vendor: sequential adapter
    if not att.track1_s4_attested:
        assert att.batch_emulation == BATCH_EMULATION_SEQUENTIAL
        assert att.publication_grade is False
        assert "NOT_PUBLICATION_GRADE" in att.attestation_note
        assert isinstance(att.attestation_record, dict)
        # Live-sample bar: capability discovery alone must not clear watermark
        live = att.attestation_record.get("live_sample") or {}
        assert live.get("succeeded") is not True


def test_project_batch_mandatory_provenance() -> None:
    scenario = next(s for s in load_all_scenarios() if s["family"] == "interior_feasible")
    spec = SafetySpec.model_validate(scenario["spec"])
    p = np.asarray(scenario["proposed_action"], dtype=np.float64)
    prev = np.asarray(scenario["previous_action"], dtype=np.float64)
    ref = np.asarray(scenario["reference_action"], dtype=np.float64)
    batch = project_batch_sequential(
        specs=[spec, spec],
        proposed_actions=[p, p],
        previous_actions=[prev, prev],
        reference_actions=[ref, ref],
        policy_weights=[1.0, 1.0],
        reference_weights=[0.0, 0.0],
    )
    assert batch.batch_emulation in {BATCH_EMULATION_SEQUENTIAL, "none"}
    assert "batch_emulation" in batch.results[0].metadata
    payload = batch.as_dict()
    if not batch.publication_grade:
        assert payload["not_publication_grade_watermark"] is not None


def test_local_global_regime_tags() -> None:
    scenario = next(s for s in load_all_scenarios() if s["family"] == "interior_feasible")
    spec = SafetySpec.model_validate(scenario["spec"])
    result = run_local_global_consistency(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
        base_params={"policy_weight": 1.0, "rate_limit": 1.0},
        neighbor_params=[
            {"policy_weight": 1.2},
            {"rate_limit": 0.5},
        ],
    )
    assert result.mean_relative_error is not None or result.flags
    assert result.regime_counts
    assert "NOT_PUBLICATION_GRADE" in result.publication_grade_watermark
    frontier = run_frontier_sweep_scaffold(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
    )
    assert frontier.batch_emulation == BATCH_EMULATION_SEQUENTIAL
