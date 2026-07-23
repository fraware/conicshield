"""Risk-based shadow sampling: detection-rate vs cost study (R1).

Compares sampling policies against a 100% shadow baseline on the versioned corpus.
Emits machine-readable results suitable for ``output/research/`` and CI fixtures.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from conicshield.experimental.corpus.paths import CORPUS_VERSION
from conicshield.experimental.provenance import begin_experiment_provenance, finalize_experiment_provenance
from conicshield.experimental.solver_assurance.disagreement import (
    ACTION_L2_LARGE,
    summarize_by_family,
    summarize_disagreements,
)
from conicshield.experimental.solver_assurance.sampling import SamplingPolicyId
from conicshield.experimental.solver_assurance.shadow_harness import run_shadow_harness

# Schema id for committed CI-small fixtures and full study outputs
SAMPLING_STUDY_SCHEMA_ID = "research.sampling_study.v0"
DEFAULT_BUDGET_FRACTIONS: tuple[float, ...] = (0.25, 0.5, 0.75, 1.0)


@dataclass(slots=True)
class PolicyBudgetResult:
    policy: str
    budget_fraction: float
    shadowed_count: int
    scenario_count: int
    shadow_cost_relative: float
    consequential_detected: int
    consequential_baseline: int
    detection_rate: float
    false_skip_rate: float
    mean_l2_when_shadowed: float
    status_disagreement_count: int
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _wilson_interval(successes: int, n: int, *, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (publication-oriented CI)."""

    if n <= 0:
        return (float("nan"), float("nan"))
    phat = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (phat + z2 / (2.0 * n)) / denom
    half = (z / denom) * ((phat * (1.0 - phat) / n + z2 / (4.0 * n * n)) ** 0.5)
    return (float(max(0.0, center - half)), float(min(1.0, center + half)))


@dataclass(slots=True)
class CostDetectionPoint:
    policy: str
    budget_fraction: float
    shadow_cost_relative: float
    detection_rate: float
    detection_ci_low: float
    detection_ci_high: float
    false_skip_rate: float
    consequential_detected: int
    consequential_baseline: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SamplingStudyReport:
    schema_id: str = SAMPLING_STUDY_SCHEMA_ID
    corpus_version: str = CORPUS_VERSION
    primary_backend: str = "cvxpy_clarabel"
    shadow_backend: str = "cvxpy_scs"
    baseline_policy: str = SamplingPolicyId.RANDOM.value
    baseline_budget_fraction: float = 1.0
    consequential_l2_threshold: float = ACTION_L2_LARGE
    results: list[PolicyBudgetResult] = field(default_factory=list)
    family_summaries_baseline: list[dict[str, Any]] = field(default_factory=list)
    negative_results: list[str] = field(default_factory=list)
    cost_detection_curve: list[CostDetectionPoint] = field(default_factory=list)
    statistical_summary: dict[str, Any] = field(default_factory=dict)
    promotion_gate: str = (
        "Advanced sampling may enter production only when mandatory verification remains "
        "complete and sampling affects only the optional secondary solve."
    )
    provenance: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "corpus_version": self.corpus_version,
            "primary_backend": self.primary_backend,
            "shadow_backend": self.shadow_backend,
            "baseline_policy": self.baseline_policy,
            "baseline_budget_fraction": self.baseline_budget_fraction,
            "consequential_l2_threshold": self.consequential_l2_threshold,
            "results": [r.as_dict() for r in self.results],
            "family_summaries_baseline": list(self.family_summaries_baseline),
            "negative_results": list(self.negative_results),
            "cost_detection_curve": [p.as_dict() for p in self.cost_detection_curve],
            "statistical_summary": dict(self.statistical_summary),
            "promotion_gate": self.promotion_gate,
            "provenance": dict(self.provenance),
            "publication_ready_machine_readable": True,
        }


def _consequential_ids(summary: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for case in summary.get("cases") or []:
        if not case.get("shadowed"):
            continue
        d = case.get("disagreement") or {}
        consequential = bool(d.get("consequential"))
        if not consequential:
            # Fallback for older records without the flag
            consequential = bool(d.get("status_disagreement")) or (
                float(d.get("corrected_action_l2") or 0.0) >= ACTION_L2_LARGE
            )
        if consequential:
            ids.add(str(case["scenario_id"]))
    return ids


def run_sampling_study(
    *,
    policies: list[SamplingPolicyId | str] | None = None,
    budget_fractions: tuple[float, ...] = DEFAULT_BUDGET_FRACTIONS,
    primary_backend: str = "cvxpy_clarabel",
    shadow_backend: str = "cvxpy_scs",
    output_dir: Path | None = None,
    ci_small: bool = False,
    exact_command: str = "python -m conicshield.experimental.solver_assurance.sampling_study",
) -> SamplingStudyReport:
    """Compare detection rate vs shadow cost against 100% shadow baseline."""

    if ci_small:
        policies = policies or [
            SamplingPolicyId.RESIDUAL,
            SamplingPolicyId.RANDOM,
            SamplingPolicyId.ACTIVE_SET_CHANGE,
        ]
        budget_fractions = (0.5, 1.0)
    else:
        policies = policies or list(SamplingPolicyId)

    provenance = begin_experiment_provenance(
        scenario_corpus_version=CORPUS_VERSION,
        backend=f"{primary_backend}|{shadow_backend}",
        exact_command=exact_command,
        random_seeds={"sampling_study": 0},
        solver_settings={
            "policies": [str(p) for p in policies],
            "budget_fractions": list(budget_fractions),
            "ci_small": ci_small,
        },
        tolerances={"action_l2_consequential": ACTION_L2_LARGE},
        warm_start_policy="cold",
        fallback_policy="record_only",
        solver_distribution="cvxpy",
        batch_size=1,
    )

    baseline = run_shadow_harness(
        primary_backend=primary_backend,
        shadow_backend=shadow_backend,
        sampling_policy=SamplingPolicyId.RANDOM,
        budget_fraction=1.0,
        exact_command=f"{exact_command}::baseline_100pct",
    )
    baseline_ids = _consequential_ids(baseline)
    n_base = len(baseline_ids)
    n_scenarios = int(baseline["scenario_count"])

    family_summaries = [s.as_dict() for s in summarize_by_family(list(baseline.get("cases") or []))]
    # Attach overall distribution for baseline
    shadowed_disagreements = []
    from conicshield.experimental.solver_assurance.disagreement import SolverDisagreement

    for case in baseline.get("cases") or []:
        if not case.get("shadowed"):
            continue
        raw = case["disagreement"]
        shadowed_disagreements.append(
            SolverDisagreement(
                status_disagreement=bool(raw["status_disagreement"]),
                release_disagreement=bool(raw.get("release_disagreement", False)),
                corrected_action_l2=float(raw["corrected_action_l2"]),
                corrected_action_linf=float(raw["corrected_action_linf"]),
                objective_gap_abs=raw.get("objective_gap_abs"),
                objective_gap_rel=raw.get("objective_gap_rel"),
                equality_residual_gap=float(raw["equality_residual_gap"]),
                inequality_residual_gap=float(raw["inequality_residual_gap"]),
                active_set_symmetric_difference=tuple(raw.get("active_set_symmetric_difference") or ()),
                iteration_ratio=raw.get("iteration_ratio"),
                timeout_asymmetry=bool(raw.get("timeout_asymmetry", False)),
                warm_cold_disagreement=raw.get("warm_cold_disagreement"),
                taxonomy_labels=tuple(raw.get("taxonomy_labels") or ()),
                residual_dominance_side=raw.get("residual_dominance_side"),
                consequential=bool(raw.get("consequential", False)),
                negative_result_note=raw.get("negative_result_note"),
            )
        )
    _ = summarize_disagreements(shadowed_disagreements)

    results: list[PolicyBudgetResult] = []
    negative: list[str] = []
    if n_base == 0:
        negative.append(
            "baseline_100pct_shadow found zero consequential disagreements; "
            "detection_rate is undefined and reported as 1.0 with note"
        )

    for policy in policies:
        for frac in budget_fractions:
            summary = run_shadow_harness(
                primary_backend=primary_backend,
                shadow_backend=shadow_backend,
                sampling_policy=policy,
                budget_fraction=float(frac),
                exact_command=f"{exact_command}::{policy}@{frac}",
            )
            detected = _consequential_ids(summary)
            shadowed_count = int(summary["shadowed_count"])
            if n_base == 0:
                detection_rate = 1.0
                false_skip = 0.0
                note = "no_baseline_consequential; detection_rate set to 1.0 by convention"
            else:
                detection_rate = float(len(detected & baseline_ids) / n_base)
                missed = baseline_ids - detected
                false_skip = float(len(missed) / n_base)
                note = ""
                if float(frac) < 1.0 and detection_rate < 0.5:
                    negative.append(
                        f"policy={policy} budget={frac}: detection_rate={detection_rate:.3f} "
                        f"(below 0.5 vs 100% shadow consequential set)"
                    )
            results.append(
                PolicyBudgetResult(
                    policy=str(policy),
                    budget_fraction=float(frac),
                    shadowed_count=shadowed_count,
                    scenario_count=n_scenarios,
                    shadow_cost_relative=float(shadowed_count / max(n_scenarios, 1)),
                    consequential_detected=len(detected & baseline_ids) if n_base else len(detected),
                    consequential_baseline=n_base,
                    detection_rate=detection_rate,
                    false_skip_rate=false_skip if n_base else 0.0,
                    mean_l2_when_shadowed=float(summary.get("mean_l2_when_shadowed") or 0.0),
                    status_disagreement_count=int(summary.get("status_disagreement_count") or 0),
                    notes=note,
                )
            )

    provenance = finalize_experiment_provenance(provenance)
    curve: list[CostDetectionPoint] = []
    for r in results:
        # Binomial CI over baseline consequential set size (detection among known positives).
        lo, hi = _wilson_interval(r.consequential_detected, max(r.consequential_baseline, 1))
        if r.consequential_baseline == 0:
            lo, hi = float("nan"), float("nan")
        curve.append(
            CostDetectionPoint(
                policy=r.policy,
                budget_fraction=r.budget_fraction,
                shadow_cost_relative=r.shadow_cost_relative,
                detection_rate=r.detection_rate,
                detection_ci_low=lo,
                detection_ci_high=hi,
                false_skip_rate=r.false_skip_rate,
                consequential_detected=r.consequential_detected,
                consequential_baseline=r.consequential_baseline,
            )
        )
    # Prefer residual@mid-budget when present for a compact summary cell.
    residual_mid = next(
        (p for p in curve if p.policy == SamplingPolicyId.RESIDUAL.value and abs(p.budget_fraction - 0.5) < 1e-12),
        curve[0] if curve else None,
    )
    statistical_summary = {
        "confidence_method": "wilson_score_interval_95",
        "baseline_consequential_count": n_base,
        "n_scenarios": n_scenarios,
        "ci_small": ci_small,
        "highlight_policy_budget": None
        if residual_mid is None
        else {
            "policy": residual_mid.policy,
            "budget_fraction": residual_mid.budget_fraction,
            "detection_rate": residual_mid.detection_rate,
            "detection_ci_95": [residual_mid.detection_ci_low, residual_mid.detection_ci_high],
            "shadow_cost_relative": residual_mid.shadow_cost_relative,
        },
        "pareto_note": (
            "cost_detection_curve lists all policy/budget cells; select operating points "
            "by inspection — no automatic production recommendation."
        ),
    }
    report = SamplingStudyReport(
        corpus_version=str(baseline.get("corpus_version") or CORPUS_VERSION),
        primary_backend=primary_backend,
        shadow_backend=shadow_backend,
        results=results,
        family_summaries_baseline=family_summaries,
        negative_results=sorted(set(negative)),
        cost_detection_curve=curve,
        statistical_summary=statistical_summary,
        provenance=provenance.as_dict(),
    )

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / ("sampling_study_ci_small.json" if ci_small else "sampling_study.json")
        out_path.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        provenance = finalize_experiment_provenance(provenance, artifact_paths=[out_path])
        provenance.to_json(output_dir / "provenance.json")
        report.provenance = provenance.as_dict()
        out_path.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return report


def load_sampling_study(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError(f"sampling study must be an object: {path}")
    return raw


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Risk-based shadow sampling study")
    parser.add_argument("--ci-small", action="store_true", help="Deterministic small study for public CI")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/research/sampling_study"),
    )
    args = parser.parse_args()
    report = run_sampling_study(output_dir=args.output_dir, ci_small=args.ci_small)
    best = max(report.results, key=lambda r: (r.detection_rate, -r.shadow_cost_relative))
    print(
        f"sampling study: {len(report.results)} cells; "
        f"best detection/cost={best.policy}@{best.budget_fraction} "
        f"det={best.detection_rate:.3f} cost={best.shadow_cost_relative:.3f}"
    )
    if report.negative_results:
        print(f"negative_results={len(report.negative_results)}")
    print(f"wrote {args.output_dir}")


if __name__ == "__main__":
    main()
