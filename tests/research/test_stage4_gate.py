"""Update stage-4 expectations: checklist green enables experimental RH (not full MPC)."""

from __future__ import annotations

from pathlib import Path

from conicshield.experimental.domains.cbf_2d import STAGE4_VALIDATION_CHECKLIST, CBF2DDomain
from conicshield.experimental.domains.stage4_gate import (
    STAGE4_GATE_SCHEMA_ID,
    CriterionStatus,
    evaluate_stage4_gate,
)


def test_stage4_evaluator_experimental_rh_when_green(tmp_path: Path) -> None:
    ev = evaluate_stage4_gate(evidence_dir=tmp_path)
    d = ev.as_dict()
    assert d["schema_id"] == STAGE4_GATE_SCHEMA_ID
    assert d["rh_mpc_implemented"] is False
    assert d["experimental_rh_implemented"] is True
    assert d["stage4_status"] in {
        "blocked",
        "checklist_green_rh_not_implemented",
        "experimental_rh_available",
    }
    ids = {c["criterion_id"] for c in d["criteria"]}
    for req in STAGE4_VALIDATION_CHECKLIST:
        assert req in ids
    for c in d["criteria"]:
        assert c["status"] in {
            CriterionStatus.PASS.value,
            CriterionStatus.FAIL.value,
            CriterionStatus.PENDING.value,
        }
        assert isinstance(c["evidence_pointers"], list)
    domain = CBF2DDomain()
    assert domain.stage4.status == "experimental_rh_available"
    assert domain.stage4.rh_mpc_full is False
    assert (tmp_path / "stage4_gate_evaluation.json").is_file()
    if d["all_required_passed"]:
        assert d["stage4_status"] == "experimental_rh_available"
        assert d["unblock_allowed"] is True


def test_stage4_statuses_are_explicit() -> None:
    ev = evaluate_stage4_gate()
    for c in ev.criteria:
        assert c.status in {CriterionStatus.PASS, CriterionStatus.FAIL, CriterionStatus.PENDING}
        assert isinstance(c.evidence_pointers, list)
