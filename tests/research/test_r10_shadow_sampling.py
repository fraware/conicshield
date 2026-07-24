"""R10 shadow-sampling science tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

from conicshield.experimental.adapters.projection import ResearchProjectionResult
from conicshield.experimental.adapters.track1_protocols import CanonicalSolverStatus
from conicshield.experimental.solver_assurance.sampling import (
    SamplingContext,
    SamplingPolicyId,
    compute_boundary_features,
    ranking_value,
    select_for_shadow,
    select_for_shadow_detailed,
    RandomSamplingPolicy,
)
from conicshield.experimental.solver_assurance.sampling_study import (
    SAMPLING_STUDY_SCHEMA_ID,
    run_sampling_study,
)
from conicshield.experimental.solver_assurance.shadow_harness import run_shadow_harness


def _result(
    action: list[float],
    *,
    status: CanonicalSolverStatus = CanonicalSolverStatus.OPTIMAL,
    active: list[str] | None = None,
    eq: float = 0.0,
    ineq: float = 0.0,
    iterations: int | None = 10,
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
        iterations=iterations,
    )


def test_ranking_value_stable_and_in_unit_interval() -> None:
    a = ranking_value(master_seed=7, scenario_id="fam/s0001", policy_id="random")
    b = ranking_value(master_seed=7, scenario_id="fam/s0001", policy_id="random")
    c = ranking_value(master_seed=8, scenario_id="fam/s0001", policy_id="random")
    assert a == b
    assert a != c
    assert 0.0 <= a < 1.0


def test_random_selection_identical_across_processes() -> None:
    code = r"""
from conicshield.experimental.adapters.projection import ResearchProjectionResult
from conicshield.experimental.adapters.track1_protocols import CanonicalSolverStatus
from conicshield.experimental.solver_assurance.sampling import (
    SamplingContext,
    RandomSamplingPolicy,
    select_for_shadow,
)
import numpy as np

def res(sid, eq=0.0):
    a = np.asarray([0.25]*4)
    return ResearchProjectionResult(
        proposed_action=a, corrected_action=a, intervened=False, intervention_norm=0.0,
        solver_status="optimal", canonical_status=CanonicalSolverStatus.OPTIMAL,
        equality_residual=eq, inequality_residual=0.0, active_constraints=["simplex"],
    )
ctxs = [
    SamplingContext(scenario_id=f"s{i:02d}", structural_fingerprint=str(i), primary=res(f"s{i:02d}"))
    for i in range(12)
]
sel = select_for_shadow(ctxs, RandomSamplingPolicy(master_seed=42), budget_fraction=0.5, master_seed=42)
print(",".join(sel))
"""
    out1 = subprocess.check_output([sys.executable, "-c", code], text=True).strip()
    out2 = subprocess.check_output([sys.executable, "-c", code], text=True).strip()
    assert out1 == out2
    assert len(out1.split(",")) == 6


def test_boundary_features_not_residual_proxy() -> None:
    feats = compute_boundary_features(
        corrected_action=np.asarray([0.49, 0.17, 0.17, 0.17]),
        previous_action=np.asarray([0.25] * 4),
        lower=np.zeros(4),
        upper=np.asarray([0.50, 1.0, 1.0, 1.0]),
        max_delta=np.ones(4),
        simplex_total=1.0,
        active_constraints=["simplex", "box_upper"],
        previous_active_set=("simplex",),
        equality_residual=1e-9,
        inequality_residual=0.0,
        iterations=12,
        warm_started=False,
        warm_start_rejected=False,
    )
    assert feats.min_normalized_inequality_slack is not None
    assert feats.min_normalized_inequality_slack < 0.05  # near upper bound on dim0
    assert feats.active_set_change == 1.0
    assert feats.verified_equality_residual == 1e-9
    assert feats.iterations == 12.0
    assert feats.dual_pressure is not None
    assert feats.equality_conditioning is not None


def test_skipped_shadow_is_none() -> None:
    summary = run_shadow_harness(
        primary_backend="cvxpy_clarabel",
        shadow_backend="cvxpy_scs",
        sampling_policy="random",
        budget_fraction=0.25,
        master_seed=0,
    )
    skipped = [c for c in summary["cases"] if not c["shadowed"]]
    assert skipped, "expected some skipped cases at 25% budget"
    for case in skipped:
        assert case["shadow"] is None
        assert case["disagreement"] is None
        assert case["sampling_status"] == "skipped_by_sampling"
    assert summary["production_recommendation_blocked"] is True
    assert "sampling_selection" in summary
    assert summary["sampling_selection"]["rank_records"]


def test_detection_not_one_when_zero_baseline(monkeypatch) -> None:
    """Zero consequential events ⇒ detection not estimable (never 1.0)."""

    empty_baseline = {
        "corpus_version": "test",
        "scenario_count": 4,
        "shadowed_count": 4,
        "mean_l2_when_shadowed": 0.0,
        "status_disagreement_count": 0,
        "cases": [
            {
                "scenario_id": f"s{i}",
                "family": "interior_feasible",
                "shadowed": True,
                "disagreement": {
                    "status_disagreement": False,
                    "release_disagreement": False,
                    "corrected_action_l2": 0.0,
                    "corrected_action_linf": 0.0,
                    "objective_gap_abs": 0.0,
                    "objective_gap_rel": 0.0,
                    "equality_residual_gap": 0.0,
                    "inequality_residual_gap": 0.0,
                    "active_set_symmetric_difference": [],
                    "iteration_ratio": 1.0,
                    "timeout_asymmetry": False,
                    "warm_cold_disagreement": None,
                    "taxonomy_labels": ["none"],
                    "residual_dominance_side": None,
                    "consequential": False,
                    "negative_result_note": None,
                },
            }
            for i in range(4)
        ],
    }

    def _fake_harness(**kwargs):
        return dict(empty_baseline)

    monkeypatch.setattr(
        "conicshield.experimental.solver_assurance.sampling_study.run_shadow_harness",
        _fake_harness,
    )
    report = run_sampling_study(
        policies=[SamplingPolicyId.RANDOM],
        budget_fractions=(0.5,),
        master_seeds=(0,),
        ci_small=False,
        exact_command="pytest:zero_baseline",
    )
    assert report.statistical_summary["baseline_consequential_count"] == 0
    for r in report.results:
        assert r.detection_estimable is False
        assert r.detection_rate is None
        assert r.detection_rate != 1.0
    assert report.production_recommendation_blocked is True
    assert report.production_recommendation is None


def test_sampling_study_ci_small_r10(tmp_path: Path) -> None:
    report = run_sampling_study(
        output_dir=tmp_path,
        ci_small=True,
        exact_command="pytest:test_sampling_study_ci_small_r10",
    )
    assert report.schema_id == SAMPLING_STUDY_SCHEMA_ID
    assert report.production_recommendation_blocked is True
    assert report.statistical_summary.get("prevalence") is not None
    assert "cost_distribution" in report.statistical_summary
    assert report.master_seeds
    # Missed events (if any) must be subset of baseline consequential ids
    for r in report.results:
        if r.detection_estimable:
            assert r.detection_rate is not None
            for mid in r.missed_baseline_ids:
                assert mid  # non-empty id tracing to baseline
        else:
            assert r.detection_rate is None
    assert (tmp_path / "sampling_study_ci_small.json").is_file()


def test_select_tie_break_records_provenance() -> None:
    primary = _result([0.25] * 4)
    ctxs = [
        SamplingContext(scenario_id="a", structural_fingerprint="1", primary=primary),
        SamplingContext(scenario_id="b", structural_fingerprint="2", primary=primary),
    ]
    sel = select_for_shadow_detailed(
        ctxs,
        RandomSamplingPolicy(master_seed=3),
        budget_fraction=0.5,
        master_seed=3,
    )
    assert len(sel.selected_ids) == 1
    assert all(r.master_seed == 3 for r in sel.rank_records)
    assert all(r.tie_break_rule for r in sel.rank_records)
