"""Formal hypothesis evaluation with pre-registered protocols (Track 2).

Verdicts: pass / fail / inconclusive / blocked / not_evaluated.
Negative and inconclusive results are retained honestly.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np

from conicshield.experimental.corpus.paths import CORPUS_VERSION


class HypothesisVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    BLOCKED = "blocked"
    NOT_EVALUATED = "not_evaluated"


@dataclass(slots=True)
class EvaluationProtocol:
    """Pre-registered evaluation protocol (metrics, thresholds, sample, multiplicity)."""

    hypothesis_id: str
    metrics: tuple[str, ...]
    thresholds: dict[str, float]
    sample_definition: str
    multiplicity_handling: str
    primary_alpha: float = 0.05
    minimum_n: int = 8
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class HypothesisEvaluation:
    hypothesis_id: str
    statement: str
    track: str  # R1..R6
    verdict: HypothesisVerdict
    evidence_pointers: list[str] = field(default_factory=list)
    rationale: str = ""
    negative_result: bool = False
    protocol: EvaluationProtocol | None = None
    statistics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["verdict"] = str(self.verdict)
        if self.protocol is not None:
            d["protocol"] = self.protocol.as_dict()
        return d


@dataclass(slots=True)
class HypothesisEvaluationReport:
    schema_id: str = "research.hypothesis_evaluation.v1"
    corpus_version: str = CORPUS_VERSION
    evaluations: list[HypothesisEvaluation] = field(default_factory=list)
    notes: str = (
        "Verdicts are research-local and falsifiable. "
        "INCONCLUSIVE is preferred over overclaim when evidence is thin. "
        "Negative results are retained."
    )
    multiplicity_family_note: str = (
        "Within a track, primary hypotheses use Bonferroni-adjusted alpha = "
        "primary_alpha / n_primary when scoring pass/fail jointly."
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "corpus_version": self.corpus_version,
            "notes": self.notes,
            "multiplicity_family_note": self.multiplicity_family_note,
            "evaluations": [e.as_dict() for e in self.evaluations],
        }

    def to_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _protocol_r1_h1() -> EvaluationProtocol:
    return EvaluationProtocol(
        hypothesis_id="R1.H1",
        metrics=("abs_pearson_active_set_vs_disagreement", "abs_pearson_proposal_distance_vs_disagreement"),
        thresholds={
            "min_delta_abs_corr": 0.05,
            "min_active_set_abs_corr": 0.15,
        },
        sample_definition="Corpus cases with primary+shadow solves; active-set change indicator vs proposal L2.",
        multiplicity_handling="Bonferroni within R1 primary set {H1,H2,H4}: alpha/3",
        primary_alpha=0.05,
        minimum_n=8,
        notes=(
            "Pass if active-set |corr| exceeds proposal-distance |corr| by min_delta "
            "and clears min_active_set_abs_corr."
        ),
    )


def _protocol_r1_h2() -> EvaluationProtocol:
    return EvaluationProtocol(
        hypothesis_id="R1.H2",
        metrics=("residual_detection_rate", "random_detection_rate", "residual_shadow_cost", "random_shadow_cost"),
        thresholds={"min_detection": 0.5, "fail_gap": 0.05},
        sample_definition="Sampling study budget cells with budget_fraction < 1.",
        multiplicity_handling="Bonferroni within R1 primary set",
        minimum_n=2,
    )


def _protocol_r2_h2() -> EvaluationProtocol:
    return EvaluationProtocol(
        hypothesis_id="R2.H2",
        metrics=("abs_pearson_raw_dual_vs_intervention", "abs_pearson_normalized_dual_vs_intervention"),
        thresholds={"raw_weak_max": 0.35, "normalized_gain_min": 0.05},
        sample_definition="Dual-pressure correlation study rows (synthetic or observed).",
        multiplicity_handling="Descriptive; inconclusive preferred when duals unavailable.",
        minimum_n=5,
        notes="Pass if raw dual |corr| is weak (<raw_weak_max) OR normalization improves |corr| by gain_min.",
    )


def _protocol_r2_h3() -> EvaluationProtocol:
    return EvaluationProtocol(
        hypothesis_id="R2.H3",
        metrics=("mean_jac_norm_pre_transition", "mean_jac_norm_stable", "lift_ratio"),
        thresholds={"min_lift": 1.15, "min_pre": 3, "min_stable": 3},
        sample_definition=(
            "Active-set transition neighborhood trajectories: Jacobian Frobenius from central FD "
            "on 'pre-transition' sides vs stable interior/far sides."
        ),
        multiplicity_handling="Bonferroni within R2 evaluable set {H2,H3}",
        minimum_n=6,
        notes="Pass if mean jac norm before discrete transitions is >= min_lift times stable mean.",
    )


def default_hypothesis_catalog() -> list[HypothesisEvaluation]:
    """Catalog aligned with HYPOTHESES.md — evaluations filled by runners."""

    return [
        HypothesisEvaluation(
            hypothesis_id="R1.H1",
            statement="Active-set changes predict solver disagreement better than raw proposal distance.",
            track="R1",
            verdict=HypothesisVerdict.NOT_EVALUATED,
            protocol=_protocol_r1_h1(),
            rationale="Requires paired feature analysis on shadowed corpus cases.",
        ),
        HypothesisEvaluation(
            hypothesis_id="R1.H2",
            statement=(
                "Residual-based sampling detects most consequential disagreements at substantially "
                "lower shadow cost than uniform sampling."
            ),
            track="R1",
            verdict=HypothesisVerdict.NOT_EVALUATED,
            evidence_pointers=["research.sampling_study.v0"],
            protocol=_protocol_r1_h2(),
        ),
        HypothesisEvaluation(
            hypothesis_id="R1.H3",
            statement="Warm-start anomalies are early signals of solver instability.",
            track="R1",
            verdict=HypothesisVerdict.NOT_EVALUATED,
            rationale="Warm-start anomaly instrumentation not yet sufficient for a formal test.",
        ),
        HypothesisEvaluation(
            hypothesis_id="R1.H4",
            statement="Cross-platform disagreement is dominated by a small number of conditioning regimes.",
            track="R1",
            verdict=HypothesisVerdict.NOT_EVALUATED,
            evidence_pointers=["research.candidate_stack_promotion.v0"],
            rationale="Requires soak across platforms; public Clarabel/SCS only is insufficient for pass.",
        ),
        HypothesisEvaluation(
            hypothesis_id="R2.H1",
            statement="Exact, smoothed, and finite-difference modes disagree most near active-set transitions.",
            track="R2",
            verdict=HypothesisVerdict.INCONCLUSIVE,
            rationale=(
                "Native exact/smoothed backends exist but disagreement claims remain "
                "inconclusive without multi-host live Moreau coverage. Research "
                "KKT/smoothed adapters exist but do not substitute for native Moreau "
                "exact/smoothed disagreement claims."
            ),
            evidence_pointers=["GRADIENT_OBSERVATORY_REPORT", "exact_research_kkt", "smoothed_research_projection"],
        ),
        HypothesisEvaluation(
            hypothesis_id="R2.H2",
            statement=(
                "Dual magnitude alone is a weak predictor of causal sensitivity without normalization and validation."
            ),
            track="R2",
            verdict=HypothesisVerdict.NOT_EVALUATED,
            evidence_pointers=["dual_pressure_correlations"],
            protocol=_protocol_r2_h2(),
        ),
        HypothesisEvaluation(
            hypothesis_id="R2.H3",
            statement="Local Jacobian norms rise before discrete active-set changes in bound-neighborhood corpora.",
            track="R2",
            verdict=HypothesisVerdict.NOT_EVALUATED,
            protocol=_protocol_r2_h3(),
            evidence_pointers=["observatory", "active_set_transition_neighborhoods"],
        ),
        HypothesisEvaluation(
            hypothesis_id="R3.H1",
            statement=(
                "Local gradient predictions of nearby frontier movement fail precisely where active sets change."
            ),
            track="R3",
            verdict=HypothesisVerdict.NOT_EVALUATED,
        ),
        HypothesisEvaluation(
            hypothesis_id="R3.H2",
            statement=(
                "Pareto-efficient safety-parameter choices are concentrated in a small number of conditioning regimes."
            ),
            track="R3",
            verdict=HypothesisVerdict.NOT_EVALUATED,
        ),
        HypothesisEvaluation(
            hypothesis_id="R4.H1",
            statement=(
                "Evidence levels L0–L4 communicate assurance strength without implying universal safety guarantees."
            ),
            track="R4",
            verdict=HypothesisVerdict.NOT_EVALUATED,
            evidence_pointers=["ASSURANCE_SEMANTICS.md", "assurance_bundle.schema.json"],
        ),
        HypothesisEvaluation(
            hypothesis_id="R4.H2",
            statement="Corruption and missing-evidence tests catch overstated proof-carrying claims.",
            track="R4",
            verdict=HypothesisVerdict.NOT_EVALUATED,
            evidence_pointers=["tests/research/test_evidence_corruption.py"],
        ),
        HypothesisEvaluation(
            hypothesis_id="R6.H1",
            statement=(
                "Reducing intervention rate on the training distribution does not imply "
                "improved held-out safety margin."
            ),
            track="R6",
            verdict=HypothesisVerdict.BLOCKED,
            rationale="R6 blocked until R2 and R4 promotion gates pass.",
            evidence_pointers=["R6_TRAINING_BLOCKED.md"],
            negative_result=False,
        ),
    ]


def _mean(xs: list[float]) -> float:
    return float(sum(xs) / max(len(xs), 1))


def _pearson(a: np.ndarray, b: np.ndarray) -> float | None:
    if a.size < 3 or b.size < 3:
        return None
    if float(np.std(a)) < 1e-15 or float(np.std(b)) < 1e-15:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def evaluate_r1_h1_from_features(
    *,
    active_set_changed: np.ndarray,
    proposal_distance: np.ndarray,
    disagreement_l2: np.ndarray,
    protocol: EvaluationProtocol | None = None,
) -> HypothesisEvaluation:
    """Score R1.H1: active-set change vs proposal distance as predictors of disagreement."""

    proto = protocol or _protocol_r1_h1()
    base = next(e for e in default_hypothesis_catalog() if e.hypothesis_id == "R1.H1")
    a = np.asarray(active_set_changed, dtype=np.float64).reshape(-1)
    d = np.asarray(proposal_distance, dtype=np.float64).reshape(-1)
    y = np.asarray(disagreement_l2, dtype=np.float64).reshape(-1)
    n = int(min(a.size, d.size, y.size))
    stats: dict[str, Any] = {"n": n}
    if n < proto.minimum_n:
        return HypothesisEvaluation(
            hypothesis_id="R1.H1",
            statement=base.statement,
            track="R1",
            verdict=HypothesisVerdict.INCONCLUSIVE,
            evidence_pointers=["r1_h1_feature_table"],
            rationale=f"n={n} < minimum_n={proto.minimum_n}",
            protocol=proto,
            statistics=stats,
        )
    a, d, y = a[:n], d[:n], y[:n]
    c_as = _pearson(a, y)
    c_pd = _pearson(d, y)
    stats["pearson_active_set"] = c_as
    stats["pearson_proposal_distance"] = c_pd
    if c_as is None or c_pd is None:
        return HypothesisEvaluation(
            hypothesis_id="R1.H1",
            statement=base.statement,
            track="R1",
            verdict=HypothesisVerdict.INCONCLUSIVE,
            evidence_pointers=["r1_h1_feature_table"],
            rationale="Insufficient variance for Pearson correlation.",
            protocol=proto,
            statistics=stats,
        )
    abs_as, abs_pd = abs(c_as), abs(c_pd)
    delta = abs_as - abs_pd
    stats["delta_abs_corr"] = delta
    thr = proto.thresholds
    if abs_as >= thr["min_active_set_abs_corr"] and delta >= thr["min_delta_abs_corr"]:
        return HypothesisEvaluation(
            hypothesis_id="R1.H1",
            statement=base.statement,
            track="R1",
            verdict=HypothesisVerdict.PASS,
            evidence_pointers=["r1_h1_feature_table", f"corpus:{CORPUS_VERSION}"],
            rationale=f"|corr_as|={abs_as:.3f} |corr_pd|={abs_pd:.3f} delta={delta:.3f}",
            protocol=proto,
            statistics=stats,
        )
    if abs_pd > abs_as + thr["min_delta_abs_corr"]:
        return HypothesisEvaluation(
            hypothesis_id="R1.H1",
            statement=base.statement,
            track="R1",
            verdict=HypothesisVerdict.FAIL,
            evidence_pointers=["r1_h1_feature_table", f"corpus:{CORPUS_VERSION}"],
            rationale=f"proposal distance stronger: |corr_pd|={abs_pd:.3f} > |corr_as|={abs_as:.3f}",
            negative_result=True,
            protocol=proto,
            statistics=stats,
        )
    return HypothesisEvaluation(
        hypothesis_id="R1.H1",
        statement=base.statement,
        track="R1",
        verdict=HypothesisVerdict.INCONCLUSIVE,
        evidence_pointers=["r1_h1_feature_table", f"corpus:{CORPUS_VERSION}"],
        rationale=f"|corr_as|={abs_as:.3f} |corr_pd|={abs_pd:.3f} delta={delta:.3f} below pass thresholds",
        protocol=proto,
        statistics=stats,
    )


def evaluate_r1_h2_from_sampling_study(study: dict[str, Any]) -> HypothesisEvaluation:
    """Score R1.H2 from a sampling study report dict."""

    proto = _protocol_r1_h2()
    rows = [r for r in study.get("results") or [] if float(r.get("budget_fraction", 1.0)) < 1.0]
    residual = [r for r in rows if r.get("policy") == "residual"]
    random = [r for r in rows if r.get("policy") == "random"]
    base = next(
        (e for e in default_hypothesis_catalog() if e.hypothesis_id == "R1.H2"),
        None,
    )
    statement = base.statement if base else "Residual-based sampling..."
    if not residual or not random:
        return HypothesisEvaluation(
            hypothesis_id="R1.H2",
            statement=statement,
            track="R1",
            verdict=HypothesisVerdict.INCONCLUSIVE,
            evidence_pointers=["research.sampling_study.v0"],
            rationale="Missing residual/random budget cells.",
            protocol=proto,
        )
    res_det = _mean([float(r["detection_rate"]) for r in residual])
    rand_det = _mean([float(r["detection_rate"]) for r in random])
    res_cost = _mean([float(r["shadow_cost_relative"]) for r in residual])
    rand_cost = _mean([float(r["shadow_cost_relative"]) for r in random])
    pointers = ["research.sampling_study.v0", f"corpus:{study.get('corpus_version')}"]
    stats = {
        "residual_detection_rate": res_det,
        "random_detection_rate": rand_det,
        "residual_shadow_cost": res_cost,
        "random_shadow_cost": rand_cost,
    }
    if res_det >= rand_det and res_cost <= rand_cost + 1e-9 and res_det >= proto.thresholds["min_detection"]:
        return HypothesisEvaluation(
            hypothesis_id="R1.H2",
            statement=statement,
            track="R1",
            verdict=HypothesisVerdict.PASS,
            evidence_pointers=pointers,
            rationale=(
                f"residual det={res_det:.3f} cost={res_cost:.3f} vs random det={rand_det:.3f} cost={rand_cost:.3f}"
            ),
            protocol=proto,
            statistics=stats,
        )
    if res_det + proto.thresholds["fail_gap"] < rand_det:
        return HypothesisEvaluation(
            hypothesis_id="R1.H2",
            statement=statement,
            track="R1",
            verdict=HypothesisVerdict.FAIL,
            evidence_pointers=pointers,
            rationale=f"residual det={res_det:.3f} worse than random det={rand_det:.3f}",
            negative_result=True,
            protocol=proto,
            statistics=stats,
        )
    return HypothesisEvaluation(
        hypothesis_id="R1.H2",
        statement=statement,
        track="R1",
        verdict=HypothesisVerdict.INCONCLUSIVE,
        evidence_pointers=pointers,
        rationale=f"residual det={res_det:.3f} cost={res_cost:.3f}; random det={rand_det:.3f} cost={rand_cost:.3f}",
        protocol=proto,
        statistics=stats,
    )


def evaluate_r2_h2_from_dual_study(study: dict[str, Any]) -> HypothesisEvaluation:
    """Score R2.H2 from dual-pressure correlation dict."""

    proto = _protocol_r2_h2()
    base = next(e for e in default_hypothesis_catalog() if e.hypothesis_id == "R2.H2")
    pearson = dict(study.get("pearson") or {})
    raw = pearson.get("intervention_size_raw")
    norm = pearson.get("intervention_size")
    notes = list(study.get("notes") or [])
    n = int(study.get("n_samples") or 0)
    stats = {"n": n, "pearson_raw": raw, "pearson_normalized": norm, "notes": notes}
    if n < proto.minimum_n or (raw is None and norm is None):
        return HypothesisEvaluation(
            hypothesis_id="R2.H2",
            statement=base.statement,
            track="R2",
            verdict=HypothesisVerdict.INCONCLUSIVE,
            evidence_pointers=["dual_pressure_correlations"],
            rationale="Insufficient dual-pressure samples or missing correlations (common on public path).",
            protocol=proto,
            statistics=stats,
        )
    abs_raw = abs(float(raw)) if raw is not None else None
    abs_norm = abs(float(norm)) if norm is not None else None
    if abs_raw is not None and abs_raw < proto.thresholds["raw_weak_max"]:
        return HypothesisEvaluation(
            hypothesis_id="R2.H2",
            statement=base.statement,
            track="R2",
            verdict=HypothesisVerdict.PASS,
            evidence_pointers=["dual_pressure_correlations"],
            rationale=f"raw |corr|={abs_raw:.3f} < {proto.thresholds['raw_weak_max']} (weak predictor)",
            protocol=proto,
            statistics=stats,
        )
    if abs_raw is not None and abs_norm is not None and (abs_norm - abs_raw) >= proto.thresholds["normalized_gain_min"]:
        return HypothesisEvaluation(
            hypothesis_id="R2.H2",
            statement=base.statement,
            track="R2",
            verdict=HypothesisVerdict.PASS,
            evidence_pointers=["dual_pressure_correlations"],
            rationale=f"normalization gain {abs_norm - abs_raw:.3f}",
            protocol=proto,
            statistics=stats,
        )
    if abs_raw is not None and abs_raw >= 0.7 and (abs_norm is None or abs_norm <= abs_raw):
        return HypothesisEvaluation(
            hypothesis_id="R2.H2",
            statement=base.statement,
            track="R2",
            verdict=HypothesisVerdict.FAIL,
            evidence_pointers=["dual_pressure_correlations"],
            rationale=f"raw dual |corr|={abs_raw:.3f} strong without normalization benefit",
            negative_result=True,
            protocol=proto,
            statistics=stats,
        )
    return HypothesisEvaluation(
        hypothesis_id="R2.H2",
        statement=base.statement,
        track="R2",
        verdict=HypothesisVerdict.INCONCLUSIVE,
        evidence_pointers=["dual_pressure_correlations"],
        rationale="Correlations present but neither clearly weak nor normalization-dominant.",
        protocol=proto,
        statistics=stats,
    )


def evaluate_r2_h3_from_jac_trajectory(
    *,
    jac_norms: np.ndarray,
    pre_transition: np.ndarray,
    protocol: EvaluationProtocol | None = None,
) -> HypothesisEvaluation:
    """Score R2.H3: Jacobian norms elevate before active-set transitions."""

    proto = protocol or _protocol_r2_h3()
    base = next(e for e in default_hypothesis_catalog() if e.hypothesis_id == "R2.H3")
    j = np.asarray(jac_norms, dtype=np.float64).reshape(-1)
    pre = np.asarray(pre_transition, dtype=bool).reshape(-1)
    n = int(min(j.size, pre.size))
    j, pre = j[:n], pre[:n]
    pre_vals = j[pre]
    stable_vals = j[~pre]
    stats: dict[str, Any] = {
        "n": n,
        "n_pre": int(pre_vals.size),
        "n_stable": int(stable_vals.size),
    }
    if (
        pre_vals.size < int(proto.thresholds["min_pre"])
        or stable_vals.size < int(proto.thresholds["min_stable"])
        or n < proto.minimum_n
    ):
        return HypothesisEvaluation(
            hypothesis_id="R2.H3",
            statement=base.statement,
            track="R2",
            verdict=HypothesisVerdict.INCONCLUSIVE,
            evidence_pointers=["observatory", "active_set_transition_neighborhoods"],
            rationale="Insufficient pre-transition / stable samples.",
            protocol=proto,
            statistics=stats,
        )
    mean_pre = float(np.mean(pre_vals))
    mean_stable = float(np.mean(stable_vals))
    lift = mean_pre / max(mean_stable, 1e-15)
    stats.update({"mean_jac_norm_pre_transition": mean_pre, "mean_jac_norm_stable": mean_stable, "lift_ratio": lift})
    if lift >= proto.thresholds["min_lift"]:
        return HypothesisEvaluation(
            hypothesis_id="R2.H3",
            statement=base.statement,
            track="R2",
            verdict=HypothesisVerdict.PASS,
            evidence_pointers=["observatory", f"corpus:{CORPUS_VERSION}"],
            rationale=f"lift_ratio={lift:.3f} (pre={mean_pre:.3g}, stable={mean_stable:.3g})",
            protocol=proto,
            statistics=stats,
        )
    if lift < 1.0:
        return HypothesisEvaluation(
            hypothesis_id="R2.H3",
            statement=base.statement,
            track="R2",
            verdict=HypothesisVerdict.FAIL,
            evidence_pointers=["observatory", f"corpus:{CORPUS_VERSION}"],
            rationale=f"lift_ratio={lift:.3f} < 1 (norms do not rise before transitions)",
            negative_result=True,
            protocol=proto,
            statistics=stats,
        )
    return HypothesisEvaluation(
        hypothesis_id="R2.H3",
        statement=base.statement,
        track="R2",
        verdict=HypothesisVerdict.INCONCLUSIVE,
        evidence_pointers=["observatory", f"corpus:{CORPUS_VERSION}"],
        rationale=f"lift_ratio={lift:.3f} below min_lift={proto.thresholds['min_lift']}",
        protocol=proto,
        statistics=stats,
    )


def evaluate_r3_h1_from_local_global(result: dict[str, Any]) -> HypothesisEvaluation:
    """Score R3.H1 from local-global consistency flags."""

    base = next(e for e in default_hypothesis_catalog() if e.hypothesis_id == "R3.H1")
    flags = list(result.get("flags") or [])
    if not flags:
        return HypothesisEvaluation(
            hypothesis_id="R3.H1",
            statement=base.statement,
            track="R3",
            verdict=HypothesisVerdict.INCONCLUSIVE,
            rationale="No local-global flags.",
            evidence_pointers=["local_global_consistency"],
        )
    changed = [f for f in flags if f.get("active_set_changed")]
    fail_flags = {"active_set_change", "nonlinearity", "unreliable_sensitivity"}
    changed_fail = [f for f in changed if f.get("flag") in fail_flags]
    stable_ok = [f for f in flags if not f.get("active_set_changed") and f.get("flag") == "ok"]
    stats = {
        "n_flags": len(flags),
        "n_active_set_changed": len(changed),
        "n_changed_flagged": len(changed_fail),
        "n_stable_ok": len(stable_ok),
    }
    if changed and len(changed_fail) / max(len(changed), 1) >= 0.7:
        return HypothesisEvaluation(
            hypothesis_id="R3.H1",
            statement=base.statement,
            track="R3",
            verdict=HypothesisVerdict.PASS,
            evidence_pointers=["local_global_consistency"],
            rationale="Most active-set-change neighbors carry failure flags.",
            statistics=stats,
        )
    if changed and len(changed_fail) == 0:
        return HypothesisEvaluation(
            hypothesis_id="R3.H1",
            statement=base.statement,
            track="R3",
            verdict=HypothesisVerdict.FAIL,
            evidence_pointers=["local_global_consistency"],
            rationale="Active-set changes did not produce prediction failures.",
            negative_result=True,
            statistics=stats,
        )
    return HypothesisEvaluation(
        hypothesis_id="R3.H1",
        statement=base.statement,
        track="R3",
        verdict=HypothesisVerdict.INCONCLUSIVE,
        evidence_pointers=["local_global_consistency"],
        rationale="Mixed local-global flags.",
        statistics=stats,
    )


def evaluate_r4_h2_from_tests(*, missing_evidence_caught: bool, corruption_caught: bool) -> HypothesisEvaluation:
    base = next(e for e in default_hypothesis_catalog() if e.hypothesis_id == "R4.H2")
    if missing_evidence_caught and corruption_caught:
        return HypothesisEvaluation(
            hypothesis_id="R4.H2",
            statement=base.statement,
            track="R4",
            verdict=HypothesisVerdict.PASS,
            evidence_pointers=["tests/research/test_evidence_corruption.py", "tests/research/test_assurance_replay.py"],
            rationale="Missing-evidence and corruption checks fail closed as required.",
            statistics={"missing_evidence_caught": True, "corruption_caught": True},
        )
    verdict = (
        HypothesisVerdict.FAIL
        if not (missing_evidence_caught and corruption_caught)
        else HypothesisVerdict.INCONCLUSIVE
    )
    return HypothesisEvaluation(
        hypothesis_id="R4.H2",
        statement=base.statement,
        track="R4",
        verdict=verdict,
        evidence_pointers=["tests/research/test_evidence_corruption.py"],
        rationale="Coverage gap in missing-evidence or corruption detection.",
        negative_result=not (missing_evidence_caught and corruption_caught),
        statistics={
            "missing_evidence_caught": missing_evidence_caught,
            "corruption_caught": corruption_caught,
        },
    )


def build_evaluation_report(
    *,
    sampling_study: dict[str, Any] | None = None,
    r1_h1_features: dict[str, Any] | None = None,
    dual_study: dict[str, Any] | None = None,
    r2_h3_trajectory: dict[str, Any] | None = None,
    local_global: dict[str, Any] | None = None,
    r4_h2: dict[str, bool] | None = None,
    overrides: list[HypothesisEvaluation] | None = None,
    corpus_version: str | None = None,
) -> HypothesisEvaluationReport:
    catalog = {e.hypothesis_id: e for e in default_hypothesis_catalog()}
    if sampling_study is not None:
        catalog["R1.H2"] = evaluate_r1_h2_from_sampling_study(sampling_study)
    if r1_h1_features is not None:
        catalog["R1.H1"] = evaluate_r1_h1_from_features(
            active_set_changed=np.asarray(r1_h1_features["active_set_changed"], dtype=np.float64),
            proposal_distance=np.asarray(r1_h1_features["proposal_distance"], dtype=np.float64),
            disagreement_l2=np.asarray(r1_h1_features["disagreement_l2"], dtype=np.float64),
        )
    if dual_study is not None:
        catalog["R2.H2"] = evaluate_r2_h2_from_dual_study(dual_study)
    if r2_h3_trajectory is not None:
        catalog["R2.H3"] = evaluate_r2_h3_from_jac_trajectory(
            jac_norms=np.asarray(r2_h3_trajectory["jac_norms"], dtype=np.float64),
            pre_transition=np.asarray(r2_h3_trajectory["pre_transition"], dtype=bool),
        )
    if local_global is not None:
        catalog["R3.H1"] = evaluate_r3_h1_from_local_global(local_global)
    if r4_h2 is not None:
        catalog["R4.H2"] = evaluate_r4_h2_from_tests(
            missing_evidence_caught=bool(r4_h2.get("missing_evidence_caught")),
            corruption_caught=bool(r4_h2.get("corruption_caught")),
        )
    for ov in overrides or []:
        catalog[ov.hypothesis_id] = ov
    return HypothesisEvaluationReport(
        evaluations=[catalog[k] for k in sorted(catalog)],
        corpus_version=corpus_version or CORPUS_VERSION,
    )


def ci_small_fixture_report() -> HypothesisEvaluationReport:
    """Deterministic CI-small fixture exercising formal scorers without full corpus sweeps."""

    rng = np.random.default_rng(0)
    n = 16
    # Construct a world where active-set change correlates more with disagreement than proposal distance.
    active = (rng.random(n) > 0.5).astype(np.float64)
    proposal = rng.random(n)
    disagree = 0.8 * active + 0.1 * proposal + 0.05 * rng.standard_normal(n)
    disagree = np.abs(disagree)

    sampling_study = {
        "corpus_version": CORPUS_VERSION,
        "results": [
            {"policy": "residual", "budget_fraction": 0.25, "detection_rate": 0.7, "shadow_cost_relative": 0.25},
            {"policy": "residual", "budget_fraction": 0.5, "detection_rate": 0.85, "shadow_cost_relative": 0.5},
            {"policy": "random", "budget_fraction": 0.25, "detection_rate": 0.4, "shadow_cost_relative": 0.25},
            {"policy": "random", "budget_fraction": 0.5, "detection_rate": 0.55, "shadow_cost_relative": 0.5},
        ],
    }
    dual_study = {
        "n_samples": 10,
        "pearson": {"intervention_size_raw": 0.2, "intervention_size": 0.45},
        "notes": ["fixture"],
    }
    # Pre-transition norms higher
    jac = np.concatenate([rng.normal(3.0, 0.2, 6), rng.normal(1.5, 0.2, 6)])
    pre = np.array([True] * 6 + [False] * 6)
    local_global = {
        "flags": [
            {"active_set_changed": True, "flag": "active_set_change"},
            {"active_set_changed": True, "flag": "nonlinearity"},
            {"active_set_changed": True, "flag": "active_set_change"},
            {"active_set_changed": False, "flag": "ok"},
            {"active_set_changed": False, "flag": "ok"},
        ]
    }
    return build_evaluation_report(
        sampling_study=sampling_study,
        r1_h1_features={
            "active_set_changed": active,
            "proposal_distance": proposal,
            "disagreement_l2": disagree,
        },
        dual_study=dual_study,
        r2_h3_trajectory={"jac_norms": jac, "pre_transition": pre},
        local_global=local_global,
        r4_h2={"missing_evidence_caught": True, "corruption_caught": True},
    )


def main() -> None:
    report = ci_small_fixture_report()
    out = Path("output/research/hypothesis_eval/ci_small.json")
    report.to_json(out)
    print(f"wrote {out} corpus={report.corpus_version}")
    for e in report.evaluations:
        print(f"  {e.hypothesis_id}: {e.verdict}")


if __name__ == "__main__":
    main()
