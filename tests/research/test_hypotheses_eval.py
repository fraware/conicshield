"""Formal hypothesis evaluation tests."""

from __future__ import annotations

import numpy as np

from conicshield.experimental.solver_assurance.hypotheses_eval import (
    HypothesisVerdict,
    build_evaluation_report,
    ci_small_fixture_report,
    evaluate_r1_h1_from_features,
    evaluate_r2_h3_from_jac_trajectory,
)


def test_ci_small_fixture_is_deterministic() -> None:
    a = ci_small_fixture_report().as_dict()
    b = ci_small_fixture_report().as_dict()
    assert a == b
    verdicts = {e["hypothesis_id"]: e["verdict"] for e in a["evaluations"]}
    assert verdicts["R6.H1"] == "blocked"
    assert verdicts["R1.H1"] in {"pass", "fail", "inconclusive"}
    assert verdicts["R2.H3"] in {"pass", "fail", "inconclusive"}


def test_r1_h1_protocol_scoring() -> None:
    n = 20
    active = np.array([1.0] * 10 + [0.0] * 10)
    proposal = np.linspace(0.0, 1.0, n)
    disagree = active + 0.01 * proposal
    ev = evaluate_r1_h1_from_features(
        active_set_changed=active,
        proposal_distance=proposal,
        disagreement_l2=disagree,
    )
    assert ev.verdict == HypothesisVerdict.PASS
    assert ev.protocol is not None


def test_r2_h3_negative_and_pass() -> None:
    # Fail: pre-transition norms lower
    fail = evaluate_r2_h3_from_jac_trajectory(
        jac_norms=np.array([1.0] * 4 + [3.0] * 4),
        pre_transition=np.array([True] * 4 + [False] * 4),
    )
    assert fail.verdict == HypothesisVerdict.FAIL
    assert fail.negative_result is True
    # Pass: pre-transition norms higher
    ok = evaluate_r2_h3_from_jac_trajectory(
        jac_norms=np.array([3.0] * 4 + [1.0] * 4),
        pre_transition=np.array([True] * 4 + [False] * 4),
    )
    assert ok.verdict == HypothesisVerdict.PASS


def test_build_report_retains_blocked_r6() -> None:
    report = build_evaluation_report()
    r6 = next(e for e in report.evaluations if e.hypothesis_id == "R6.H1")
    assert r6.verdict == HypothesisVerdict.BLOCKED
