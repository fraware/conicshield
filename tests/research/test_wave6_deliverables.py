"""Deliverable packaging: active-set benchmark, response map, R6 scaffold, sidecar stub."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from conicshield.experimental.adapters.research_sidecar import (
    SidecarProbeOutcome,
    probe_research_sidecar_capability,
    research_sidecar_project,
)
from conicshield.experimental.corpus.active_set_benchmark import (
    ACTIVE_SET_BENCHMARK_VERSION,
    build_active_set_transition_benchmark,
)
from conicshield.experimental.corpus.generate import load_all_scenarios
from conicshield.experimental.corpus.paths import CORPUS_VERSION
from conicshield.experimental.frontiers.safety_response_map import export_safety_response_map
from conicshield.experimental.gradients.capability import CapabilityStatus
from conicshield.experimental.training.r6_decision_scaffold import build_r6_decision_report_scaffold
from conicshield.specs.schema import SafetySpec


def test_active_set_benchmark_packages_corpus() -> None:
    bench = build_active_set_transition_benchmark()
    assert bench.benchmark_version == ACTIVE_SET_BENCHMARK_VERSION
    assert bench.corpus_version == CORPUS_VERSION
    assert bench.cases
    assert bench.expected_regimes
    assert bench.integrity_checks
    assert bench.promotion_status == "experimental"


def test_safety_response_map_has_regime_tags() -> None:
    scenario = load_all_scenarios()[0]
    spec = SafetySpec.model_validate(scenario["spec"])
    m = export_safety_response_map(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
        grid={
            "policy_weight": [1.0],
            "reference_weight": [0.0],
            "rate_limit": [1.0],
            "hazard_multiplier": [1.0],
            "geometry_prior_weight": [0.0],
            "bound_margins": [0.0],
            "robustness_margins": [0.0],
            "fallback_thresholds": [0.5],
        },
    )
    assert m.cells
    assert m.regime_counts
    assert m.publication_grade is False
    assert "NOT_PUBLICATION_GRADE" in m.watermark


def test_r6_decision_scaffold_blocked_no_results() -> None:
    report = build_r6_decision_report_scaffold()
    d = report.as_dict()
    assert d["decision_status"] == "BLOCKED"
    assert d["results"] is None
    assert d["required_evidence"]
    assert any("safer" in n.lower() for n in d["non_claims"])


def test_research_sidecar_fail_closed(tmp_path: Path) -> None:
    _ = tmp_path
    cap = probe_research_sidecar_capability(force_unavailable=True)
    assert cap.status == CapabilityStatus.UNAVAILABLE
    assert cap.outcome in {
        SidecarProbeOutcome.UNAVAILABLE,
        SidecarProbeOutcome.FAIL_CLOSED,
        SidecarProbeOutcome.SKIPPED,
    }
    out = research_sidecar_project(np.array([0.25, 0.25, 0.25, 0.25]), capability=cap)
    assert out["available"] is False
    assert out["corrected_action"] is None
    assert out["fake_success"] is False
    assert out["disagreement_hook"]["available"] is False
