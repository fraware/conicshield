"""Wave 7: CBF held-out corpus, infeasibility taxonomy, stage-4 wiring."""

from __future__ import annotations

from pathlib import Path

from conicshield.experimental.domains.cbf_corpus import (
    CBF_CORPUS_VERSION,
    MIN_HELD_OUT_NOMINAL,
    evaluate_held_out_nominal,
    generate_cbf_corpus,
    held_out_nominal_cases,
    load_cbf_cases,
    load_cbf_manifest,
)
from conicshield.experimental.domains.infeasibility_taxonomy import (
    InfeasibilityClass,
    audit_infeasibility,
    classify_filter_result,
)
from conicshield.experimental.domains.stage4_gate import CriterionStatus, evaluate_stage4_gate


def test_cbf_corpus_committed_and_reproducible(tmp_path: Path) -> None:
    # Committed corpus must exist after generation in-repo
    manifest = load_cbf_manifest()
    assert manifest["corpus_version"] == CBF_CORPUS_VERSION
    cases = load_cbf_cases()
    assert len(cases) >= MIN_HELD_OUT_NOMINAL
    assert len(held_out_nominal_cases()) >= MIN_HELD_OUT_NOMINAL

    # Regenerating to a temp root is deterministic for the same seed
    m1 = generate_cbf_corpus(root=tmp_path / "a", seed=0)
    m2 = generate_cbf_corpus(root=tmp_path / "b", seed=0)
    assert m1["generation_commit"] == m2["generation_commit"]
    assert m1["case_count"] == m2["case_count"]


def test_held_out_nominal_margins_finite() -> None:
    ev = evaluate_held_out_nominal()
    assert ev["n_held_out"] >= MIN_HELD_OUT_NOMINAL
    assert ev["infeasible_count"] == 0
    assert ev["min_safety_margin"] >= -1e-4


def test_infeasibility_taxonomy_classifies_demo() -> None:
    from conicshield.experimental.domains.cbf_2d import demo_stage1_scenario

    c = classify_filter_result(demo_stage1_scenario(), case_id="demo")
    assert c.taxonomy_class in {
        InfeasibilityClass.FEASIBLE_OPTIMAL,
        InfeasibilityClass.FEASIBLE_INACCURATE,
    }
    assert c.explained is True


def test_infeasibility_audit_unexplained_rate(tmp_path: Path) -> None:
    from conicshield.experimental.domains.cbf_corpus import probe_cbf_filter_bank
    from conicshield.experimental.domains.infeasibility_taxonomy import write_infeasibility_audit

    report = audit_infeasibility(probe_cbf_filter_bank())
    assert report.n_probes > 0
    assert report.unexplained_rate <= 0.05
    assert report.n_unexplained == 0
    path = write_infeasibility_audit(tmp_path / "audit.json", report)
    assert path.is_file()

def test_stage4_checklist_green_experimental_rh_available(tmp_path: Path) -> None:
    ev = evaluate_stage4_gate(evidence_dir=tmp_path)
    d = ev.as_dict()
    assert d["rh_mpc_implemented"] is False
    assert d["experimental_rh_implemented"] is True
    assert d["passed_count"] == d["required_count"]
    assert d["pending_count"] == 0
    assert d["failed_count"] == 0
    assert d["all_required_passed"] is True
    assert d["stage4_status"] == "experimental_rh_available"
    assert d["unblock_allowed"] is True
    assert (tmp_path / "stage4_gate_evaluation.json").is_file()
    assert (tmp_path / "cbf_infeasibility_audit.json").is_file()
    for c in d["criteria"]:
        assert c["status"] == CriterionStatus.PASS.value
