"""Wave 7: disagreement corpus, mock sidecar, ASB/response-map polish."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from conicshield.experimental.adapters.mock_sidecar import (
    MOCK_SIDECAR_LABEL,
    describe_capability_matrix,
    research_sidecar_project_with_optional_mock,
)
from conicshield.experimental.adapters.research_sidecar import (
    SidecarProbeOutcome,
    probe_research_sidecar_capability,
)
from conicshield.experimental.corpus.active_set_benchmark import (
    ACTIVE_SET_BENCHMARK_VERSION,
    build_active_set_transition_benchmark,
)
from conicshield.experimental.corpus.generate import load_all_scenarios
from conicshield.experimental.frontiers.safety_response_map import export_safety_response_map
from conicshield.experimental.gradients.capability import CapabilityStatus
from conicshield.experimental.solver_assurance.disagreement_corpus import (
    DISAGREEMENT_CORPUS_VERSION,
    build_disagreement_corpus,
)
from conicshield.experimental.training.r6_decision_scaffold import build_r6_decision_report_scaffold
from conicshield.specs.schema import SafetySpec


def test_disagreement_corpus_packages(tmp_path: Path) -> None:
    corpus = build_disagreement_corpus(
        output_dir=tmp_path,
        exact_command="pytest:disagreement_corpus",
    )
    d = corpus.as_dict()
    assert d["disagreement_corpus_version"] == DISAGREEMENT_CORPUS_VERSION
    assert d["n_records"] > 0
    assert d["promotion_status"] == "experimental"
    assert (tmp_path / "solver_disagreement_corpus.json").is_file()
    assert (tmp_path / "solver_disagreement_corpus_index.json").is_file()


def test_active_set_benchmark_integrity() -> None:
    bench = build_active_set_transition_benchmark()
    assert bench.benchmark_version == ACTIVE_SET_BENCHMARK_VERSION
    assert bench.integrity_checks
    assert all(bench.integrity_checks.values())


def test_safety_response_map_r3_completeness() -> None:
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
    assert m.r3_completeness
    assert all(m.r3_completeness.values())
    assert m.publication_grade is False


def test_mock_sidecar_requires_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("CONICSHIELD_RESEARCH_MOCK_SIDECAR", raising=False)
    out = research_sidecar_project_with_optional_mock(
        np.array([0.5, 0.5, 0.0, 0.0]),
        use_mock=True,
    )
    assert out["available"] is False
    assert out["outcome"] == SidecarProbeOutcome.SKIPPED.value
    assert out["label"] == MOCK_SIDECAR_LABEL


def test_mock_sidecar_opt_in(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CONICSHIELD_RESEARCH_MOCK_SIDECAR", "1")
    out = research_sidecar_project_with_optional_mock(
        np.array([0.25, 0.25, 0.25, 0.25]),
        use_mock=True,
    )
    assert out["available"] is True
    assert out["mock"] is True
    assert out["production_attestation"] is False
    assert out["label"] == MOCK_SIDECAR_LABEL
    assert out["corrected_action"] is not None
    assert out["disagreement_hook"]["available"] is True


def test_sidecar_force_skip() -> None:
    cap = probe_research_sidecar_capability(force_skip=True)
    assert cap.status == CapabilityStatus.UNAVAILABLE
    assert cap.outcome == SidecarProbeOutcome.SKIPPED
    matrix = describe_capability_matrix()
    assert matrix["production_claim"] is False


def test_r6_scaffold_expanded_checklist() -> None:
    report = build_r6_decision_report_scaffold()
    d = report.as_dict()
    assert d["decision_status"] == "BLOCKED"
    assert d["results"] is None
    ids = {e["evidence_id"] for e in d["required_evidence"]}
    assert "track1_s4_hetero_batch_attestation" in ids
    assert "decision_report_with_negative_results" in ids
    assert "flagship_promotion_gate" in ids
    assert any(e.get("evidence_pointers") for e in d["required_evidence"])
    assert d["flagship_gate"]["passed"] is False
    assert d["execution_authorized"] is False
