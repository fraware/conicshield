"""Sampling study and disagreement analysis tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from conicshield.experimental.adapters.projection import ResearchProjectionResult
from conicshield.experimental.adapters.track1_protocols import CanonicalSolverStatus
from conicshield.experimental.solver_assurance.disagreement import (
    DisagreementTaxonomy,
    classify_disagreement,
    compare_projections,
    summarize_by_family,
    summarize_disagreements,
)
from conicshield.experimental.solver_assurance.hypotheses_eval import (
    HypothesisVerdict,
    build_evaluation_report,
    evaluate_r1_h2_from_sampling_study,
)
from conicshield.experimental.solver_assurance.sampling import SamplingPolicyId
from conicshield.experimental.solver_assurance.sampling_study import (
    SAMPLING_STUDY_SCHEMA_ID,
    run_sampling_study,
)


def _result(
    action: list[float],
    *,
    status: CanonicalSolverStatus = CanonicalSolverStatus.OPTIMAL,
    active: list[str] | None = None,
    eq: float = 0.0,
    ineq: float = 0.0,
) -> ResearchProjectionResult:
    a = np.asarray(action, dtype=np.float64)
    return ResearchProjectionResult(
        proposed_action=a,
        corrected_action=a,
        intervened=False,
        intervention_norm=0.0,
        solver_status=str(status),
        canonical_status=status,
        objective_value=1.0,
        active_constraints=active or ["simplex"],
        equality_residual=eq,
        inequality_residual=ineq,
        iterations=10,
    )


def test_taxonomy_labels_large_action_diff() -> None:
    d = compare_projections(_result([0.0, 0.0, 0.0, 0.0]), _result([1.0, 0.0, 0.0, 0.0]))
    assert DisagreementTaxonomy.ACTION_DIFF_LARGE.value in d.taxonomy_labels
    assert d.consequential is True


def test_family_summary_negative_result_note() -> None:
    cases = [
        {
            "family": "interior_feasible",
            "shadowed": True,
            "disagreement": compare_projections(
                _result([0.25] * 4),
                _result([0.25] * 4),
            ).as_dict(),
        }
    ]
    summaries = summarize_by_family(cases)
    assert summaries[0].family == "interior_feasible"
    assert "negative_result" in summaries[0].notes


def test_sampling_study_ci_small(tmp_path: Path) -> None:
    report = run_sampling_study(
        output_dir=tmp_path,
        ci_small=True,
        exact_command="pytest:test_sampling_study_ci_small",
    )
    assert report.schema_id == SAMPLING_STUDY_SCHEMA_ID
    assert report.results
    assert report.cost_detection_curve
    assert report.statistical_summary.get("confidence_method") == "wilson_score_interval_95"
    assert report.production_recommendation_blocked is True
    assert report.as_dict()["publication_ready_machine_readable"] is True
    policies = {r.policy for r in report.results}
    assert SamplingPolicyId.RESIDUAL.value in policies
    assert (tmp_path / "sampling_study_ci_small.json").is_file()
    # Hypothesis evaluation consumes the study
    hyp = evaluate_r1_h2_from_sampling_study(report.as_dict())
    assert hyp.hypothesis_id == "R1.H2"
    assert hyp.verdict in {
        HypothesisVerdict.PASS,
        HypothesisVerdict.FAIL,
        HypothesisVerdict.INCONCLUSIVE,
    }
    catalog = build_evaluation_report(sampling_study=report.as_dict())
    assert any(e.track == "R6" and e.verdict == HypothesisVerdict.BLOCKED for e in catalog.evaluations)


def test_classify_none() -> None:
    d = compare_projections(_result([0.25] * 4), _result([0.25] * 4))
    labels = classify_disagreement(d)
    assert DisagreementTaxonomy.NONE.value in labels
    dist = summarize_disagreements([d])
    assert dist.count == 1
    assert dist.consequential_rate == 0.0
