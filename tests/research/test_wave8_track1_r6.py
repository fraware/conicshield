"""Track 1 readiness probe + R6 decision matrix polish."""

from __future__ import annotations

from pathlib import Path

from conicshield.experimental.adapters.track1_probe import (
    TRACK1_PROBE_SCHEMA_ID,
    TRACK1_PROBE_VERSION,
    probe_track1_research_readiness,
    write_track1_probe_attestation,
)
from conicshield.experimental.frontiers.sweeps import (
    BATCH_EMULATION_SEQUENTIAL,
    probe_track1_hetero_batch_attestation,
)
from conicshield.experimental.gradients.capability import CapabilityStatus
from conicshield.experimental.gradients.exact_backend import exact_backend_gradient
from conicshield.experimental.gradients.smoothed_backend import smoothed_backend_gradient
from conicshield.experimental.training.r6_decision_scaffold import (
    R6_DECISION_DOC_VERSION,
    build_r6_decision_report_scaffold,
)


def test_track1_probe_keeps_watermarks_without_vendor() -> None:
    report = probe_track1_research_readiness()
    d = report.as_dict()
    assert d["schema_id"] == TRACK1_PROBE_SCHEMA_ID
    assert d["probe_version"] == TRACK1_PROBE_VERSION
    assert d["production_claim"] is False
    ids = {p["capability_id"] for p in d["probes"]}
    assert "S4_hetero_batch" in ids
    assert "S5_sidecar" in ids
    assert "S6_native_exact_smoothed_gradients" in ids
    s4 = next(p for p in d["probes"] if p["capability_id"] == "S4_hetero_batch")
    assert "missing_evidence" in s4
    assert s4["extras"].get("capability_discovery_alone_insufficient") is True
    assert "surfaces_present" in s4["extras"]
    assert "live_sample" in s4["extras"]
    s6 = next(p for p in d["probes"] if p["capability_id"] == "S6_native_exact_smoothed_gradients")
    assert s6["capability_status"] == CapabilityStatus.UNAVAILABLE.value
    assert s6["research_attested"] is False
    assert "gap_vs_research_kkt" in s6["extras"]
    assert s6["extras"].get("smoothed_mechanism") == "softplus_inequality_softening_moreau_qp"
    # Public / Windows without vendor: do not reduce watermarks
    if not d["reduce_watermarks"]:
        assert d["frontiers_watermark_required"] is True
        att = probe_track1_hetero_batch_attestation()
        assert att.track1_s4_attested is False
        assert att.batch_emulation == BATCH_EMULATION_SEQUENTIAL
        assert att.publication_grade is False
        assert "attestation_record" in att.as_dict()


def test_track1_probe_writes_attestation(tmp_path: Path) -> None:
    path = tmp_path / "attestation.json"
    report = write_track1_probe_attestation(path=path)
    assert path.is_file()
    assert report.probe_version == TRACK1_PROBE_VERSION


def test_capability_discovery_alone_does_not_clear_watermark() -> None:
    """Even if capability flags look green in a mock sense, probe requires live sample.

    On public hosts the live sample fails; watermark must remain.
    """

    att = probe_track1_hetero_batch_attestation()
    if not att.track1_s4_attested:
        record = att.attestation_record
        live = record.get("live_sample") or {}
        assert live.get("succeeded") is not True
        assert att.batch_emulation == BATCH_EMULATION_SEQUENTIAL


def test_native_gradient_backends_report_gap_without_live_data() -> None:
    ex = exact_backend_gradient()
    sm = smoothed_backend_gradient()
    assert ex.available is False
    assert sm.available is False
    assert ex.status == CapabilityStatus.UNAVAILABLE
    assert sm.status == CapabilityStatus.UNAVAILABLE
    assert "gap_vs_exact_research_kkt" in ex.extras
    assert "gap_vs_smoothed_research_projection" in sm.extras


def test_r6_decision_matrix_blocked_scientific_doc() -> None:
    report = build_r6_decision_report_scaffold()
    d = report.as_dict()
    assert d["decision_status"] == "BLOCKED"
    assert d["results"] is None
    assert d["document_type"] == "scientific_decision_evidence_matrix"
    assert d["document_version"] == R6_DECISION_DOC_VERSION
    assert d["blocking_evidence_incomplete"]
    assert d["decision_logic"]
    assert d["execution_authorized"] is False
    assert "flagship_promotion_gate" in d["blocked_until"]
    ids = {e["evidence_id"] for e in d["required_evidence"]}
    assert "negative_retention_protocol" in ids
    assert "track1_s4_hetero_batch_attestation" in ids
    assert "flagship_promotion_gate" in ids
    for e in d["required_evidence"]:
        assert e["acceptance_criterion"]
        assert "evidence_pointers" in e
