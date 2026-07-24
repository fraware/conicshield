"""R15 intervention-aware training decision: flagship-gate wiring + harness."""

from __future__ import annotations

import pytest

from conicshield.experimental.training.comparison_harness import (
    COMPARISON_ARMS,
    CRITICAL_PROMOTION_RULE,
    HELD_OUT_EVAL_FIELDS,
    build_controlled_comparison_harness,
    probe_flagship_gate_for_training,
    r6_execution_authorized,
    run_controlled_comparison,
)
from conicshield.experimental.training.intervention_aware_stub import (
    InterventionAwareTrainingPlan,
    train_intervention_aware_policy,
)
from conicshield.experimental.training.r6_decision_scaffold import (
    R6_DECISION_DOC_VERSION,
    build_r6_decision_report_scaffold,
)
from conicshield.platform.sidecar_protocol import PROTOCOL_VERSION


def test_flagship_gate_probe_fail_closed() -> None:
    gate = probe_flagship_gate_for_training()
    assert gate["passed"] is False
    assert gate["r6_execution_authorized"] is False
    assert gate["production_claim"] is False
    assert gate["blockers"]
    assert r6_execution_authorized() is False
    # Protocol v2 wire is present; training remains blocked on live Moreau / multi-host.
    assert PROTOCOL_VERSION >= 2
    assert any("moreau" in b or "multi_host" in b or "missing_proof" in b for b in gate["blockers"])
    assert gate["predicates"].get("sidecar_protocol_v2_complete") is True


def test_comparison_harness_structure_blocked() -> None:
    harness = build_controlled_comparison_harness()
    d = harness.as_dict()
    assert d["status"] == "BLOCKED"
    assert d["execution_authorized"] is False
    assert d["results"] is None
    assert [a["arm_id"] for a in d["comparison_arms"]] == list(COMPARISON_ARMS)
    assert set(d["held_out_eval"]["required_field_ids"]) == set(HELD_OUT_EVAL_FIELDS)
    assert all(d["held_out_eval"]["fields"][k] is None for k in HELD_OUT_EVAL_FIELDS)
    assert "NOT evidence of a safer policy" in CRITICAL_PROMOTION_RULE or "NOT evidence" in CRITICAL_PROMOTION_RULE
    assert "intervention frequency" in d["critical_rule"].lower()
    assert all(a["status"] == "blocked" for a in d["comparison_arms"])


def test_run_controlled_comparison_raises_while_blocked() -> None:
    with pytest.raises(RuntimeError, match="flagship"):
        run_controlled_comparison()


def test_train_intervention_aware_policy_raises_while_blocked() -> None:
    with pytest.raises(RuntimeError, match="flagship"):
        train_intervention_aware_policy()


def test_training_plan_includes_held_out_fields() -> None:
    plan = InterventionAwareTrainingPlan().as_dict()
    assert plan["status"] == "BLOCKED"
    assert plan["execution_authorized"] is False
    assert plan["comparisons"] == list(COMPARISON_ARMS)
    assert plan["held_out_eval_fields"] == list(HELD_OUT_EVAL_FIELDS)
    assert "intervention frequency" in plan["critical_rule"].lower()
    assert "not system" in plan["public_claim_binding"].lower() or "not system-level" in plan[
        "public_claim_binding"
    ].lower()


def test_r6_scaffold_wires_flagship_gate() -> None:
    report = build_r6_decision_report_scaffold()
    d = report.as_dict()
    assert d["decision_status"] == "BLOCKED"
    assert d["document_version"] == R6_DECISION_DOC_VERSION
    assert d["document_version"].startswith("r6-decision-v0.3")
    assert d["results"] is None
    assert d["execution_authorized"] is False
    assert "flagship_promotion_gate" in d["blocked_until"]
    assert d["flagship_gate"]["passed"] is False
    ids = {e["evidence_id"] for e in d["required_evidence"]}
    assert "flagship_promotion_gate" in ids
    assert "comparison_battery" in ids
    flagship = next(e for e in d["required_evidence"] if e["evidence_id"] == "flagship_promotion_gate")
    assert flagship["status"] == "blocked_dependency"
    assert d["comparison_harness"]["status"] == "BLOCKED"
    assert set(d["comparison_harness"]["held_out_eval"]["required_field_ids"]) == set(HELD_OUT_EVAL_FIELDS)
    assert any("intervention frequency" in x.lower() for x in d["decision_logic"])
    assert any("not system-level safety proof" in x.lower() for x in d["non_claims"])
    assert "Numerical evidence" in d["note"] or "numerical evidence" in d["note"].lower()


def test_training_package_lazy_exports() -> None:
    import conicshield.experimental.training as training

    assert training.COMPARISON_ARMS == COMPARISON_ARMS
    assert training.HELD_OUT_EVAL_FIELDS == HELD_OUT_EVAL_FIELDS
    assert training.r6_execution_authorized() is False
