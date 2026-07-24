"""Solver disagreement record, taxonomy, and corpus-level analysis (R1)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np

from conicshield.experimental.adapters.projection import ResearchProjectionResult


class DisagreementTaxonomy(StrEnum):
    """Hard taxonomy for solver disagreements — keep labels mutually exclusive where possible."""

    NONE = "none"
    STATUS_ONLY = "status_only"
    ACTION_DIFF_SMALL = "action_diff_small"
    ACTION_DIFF_LARGE = "action_diff_large"
    RESIDUAL_DOMINANCE = "residual_dominance"
    ACTIVE_SET_MISMATCH = "active_set_mismatch"
    TIMEOUT_ASYMMETRY = "timeout_asymmetry"
    FAILURE_ASYMMETRY = "failure_asymmetry"
    OBJECTIVE_GAP = "objective_gap"
    COMPOUND = "compound"


# Thresholds are research defaults; record them in every summary for reproducibility.
ACTION_L2_SMALL = 1e-6
ACTION_L2_LARGE = 1e-2
RESIDUAL_GAP_DOMINANT = 1e-4
OBJECTIVE_GAP_REL_MATERIAL = 1e-3


@dataclass(slots=True)
class SolverDisagreement:
    """Exact disagreement record required by Track 2 R1."""

    status_disagreement: bool
    release_disagreement: bool
    corrected_action_l2: float
    corrected_action_linf: float
    objective_gap_abs: float | None
    objective_gap_rel: float | None
    equality_residual_gap: float
    inequality_residual_gap: float
    active_set_symmetric_difference: tuple[str, ...]
    iteration_ratio: float | None
    timeout_asymmetry: bool
    warm_cold_disagreement: float | None
    taxonomy_labels: tuple[str, ...] = ()
    residual_dominance_side: str | None = None  # "primary" | "shadow" | "tie" | None
    consequential: bool = False
    negative_result_note: str | None = None

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["active_set_symmetric_difference"] = list(self.active_set_symmetric_difference)
        d["taxonomy_labels"] = list(self.taxonomy_labels)
        return d


def _obj_gaps(a: float | None, b: float | None) -> tuple[float | None, float | None]:
    if a is None or b is None:
        return None, None
    abs_gap = abs(float(a) - float(b))
    denom = max(abs(float(a)), abs(float(b)), 1e-16)
    return abs_gap, abs_gap / denom


def _residual_dominance(eq_p: float, ineq_p: float, eq_s: float, ineq_s: float) -> str | None:
    rp = abs(eq_p) + abs(ineq_p)
    rs = abs(eq_s) + abs(ineq_s)
    gap = abs(rp - rs)
    if gap < RESIDUAL_GAP_DOMINANT:
        return "tie" if max(rp, rs) > 0.0 else None
    return "primary" if rp > rs else "shadow"


def classify_disagreement(d: SolverDisagreement) -> tuple[str, ...]:
    """Assign taxonomy labels from a filled SolverDisagreement."""

    labels: list[str] = []
    if d.timeout_asymmetry:
        labels.append(DisagreementTaxonomy.TIMEOUT_ASYMMETRY.value)
    if d.status_disagreement and not d.timeout_asymmetry:
        # Failure asymmetry: one optimal-ish, one failing
        labels.append(DisagreementTaxonomy.STATUS_ONLY.value)
    if d.active_set_symmetric_difference:
        labels.append(DisagreementTaxonomy.ACTIVE_SET_MISMATCH.value)
    if d.residual_dominance_side in {"primary", "shadow"}:
        labels.append(DisagreementTaxonomy.RESIDUAL_DOMINANCE.value)
    if d.objective_gap_rel is not None and d.objective_gap_rel >= OBJECTIVE_GAP_REL_MATERIAL:
        labels.append(DisagreementTaxonomy.OBJECTIVE_GAP.value)
    if d.corrected_action_l2 >= ACTION_L2_LARGE:
        labels.append(DisagreementTaxonomy.ACTION_DIFF_LARGE.value)
    elif d.corrected_action_l2 >= ACTION_L2_SMALL:
        labels.append(DisagreementTaxonomy.ACTION_DIFF_SMALL.value)

    material = [
        DisagreementTaxonomy.ACTION_DIFF_LARGE.value,
        DisagreementTaxonomy.RESIDUAL_DOMINANCE.value,
        DisagreementTaxonomy.TIMEOUT_ASYMMETRY.value,
        DisagreementTaxonomy.ACTIVE_SET_MISMATCH.value,
        DisagreementTaxonomy.FAILURE_ASYMMETRY.value,
    ]
    if len([x for x in labels if x in material]) >= 2:
        labels.append(DisagreementTaxonomy.COMPOUND.value)
    if not labels:
        labels.append(DisagreementTaxonomy.NONE.value)
    # Deduplicate preserving order
    seen: set[str] = set()
    out: list[str] = []
    for lab in labels:
        if lab not in seen:
            seen.add(lab)
            out.append(lab)
    return tuple(out)


def is_consequential(d: SolverDisagreement) -> bool:
    """Consequential = likely to affect released action or feasibility claims."""

    if d.corrected_action_l2 >= ACTION_L2_LARGE:
        return True
    if d.timeout_asymmetry or d.status_disagreement:
        return True
    residual_gap = d.equality_residual_gap + d.inequality_residual_gap
    return d.residual_dominance_side in {"primary", "shadow"} and residual_gap >= RESIDUAL_GAP_DOMINANT


def compare_projections(
    primary: ResearchProjectionResult,
    shadow: ResearchProjectionResult,
    *,
    release_disagreement: bool = False,
    warm_cold_disagreement: float | None = None,
    timeout_statuses: frozenset[str] | None = None,
    negative_result_note: str | None = None,
) -> SolverDisagreement:
    """Compute SolverDisagreement between primary and shadow results."""

    timeouts = timeout_statuses or frozenset({"time_limit", "iteration_limit", "TIME_LIMIT", "ITERATION_LIMIT"})
    p = np.asarray(primary.corrected_action, dtype=np.float64).reshape(-1)
    s = np.asarray(shadow.corrected_action, dtype=np.float64).reshape(-1)
    if p.shape != s.shape:
        n = max(p.size, s.size)
        pp = np.zeros(n, dtype=np.float64)
        ss = np.zeros(n, dtype=np.float64)
        pp[: p.size] = p
        ss[: s.size] = s
        p, s = pp, ss

    # NaN-safe diffs
    if not (np.all(np.isfinite(p)) and np.all(np.isfinite(s))):
        diff = np.full_like(p, np.nan, dtype=np.float64)
        l2 = float("nan")
        linf = float("nan")
        neg: str | None = negative_result_note or "non_finite_corrected_action"
    else:
        diff = p - s
        l2 = float(np.linalg.norm(diff))
        linf = float(np.max(np.abs(diff))) if diff.size else 0.0
        neg = negative_result_note

    abs_gap, rel_gap = _obj_gaps(primary.objective_value, shadow.objective_value)
    eq_p = float(primary.equality_residual or 0.0)
    eq_s = float(shadow.equality_residual or 0.0)
    ineq_p = float(primary.inequality_residual or 0.0)
    ineq_s = float(shadow.inequality_residual or 0.0)

    a_set = set(primary.active_constraints)
    b_set = set(shadow.active_constraints)
    sym = tuple(sorted(a_set.symmetric_difference(b_set)))

    iter_ratio: float | None = None
    if primary.iterations and shadow.iterations and primary.iterations > 0:
        iter_ratio = float(shadow.iterations) / float(primary.iterations)

    p_to = primary.canonical_status.value in timeouts or primary.solver_status in timeouts
    s_to = shadow.canonical_status.value in timeouts or shadow.solver_status in timeouts

    status_disagreement = (
        primary.canonical_status != shadow.canonical_status or primary.solver_status != shadow.solver_status
    )
    residual_side = _residual_dominance(eq_p, ineq_p, eq_s, ineq_s)

    d = SolverDisagreement(
        status_disagreement=status_disagreement,
        release_disagreement=bool(release_disagreement),
        corrected_action_l2=l2,
        corrected_action_linf=linf,
        objective_gap_abs=abs_gap,
        objective_gap_rel=rel_gap,
        equality_residual_gap=abs(eq_p - eq_s),
        inequality_residual_gap=abs(ineq_p - ineq_s),
        active_set_symmetric_difference=sym,
        iteration_ratio=iter_ratio,
        timeout_asymmetry=bool(p_to) != bool(s_to),
        warm_cold_disagreement=warm_cold_disagreement,
        residual_dominance_side=residual_side,
        negative_result_note=neg,
    )
    if status_disagreement and (
        p_to != s_to or "unavailable" in (primary.solver_status + shadow.solver_status).lower()
    ):
        # Annotate failure asymmetry before taxonomy
        labels = list(classify_disagreement(d))
        if DisagreementTaxonomy.FAILURE_ASYMMETRY.value not in labels:
            labels = [DisagreementTaxonomy.FAILURE_ASYMMETRY.value, *labels]
            if DisagreementTaxonomy.NONE.value in labels and len(labels) > 1:
                labels = [x for x in labels if x != DisagreementTaxonomy.NONE.value]
        d.taxonomy_labels = tuple(dict.fromkeys(labels))
    else:
        d.taxonomy_labels = classify_disagreement(d)
    d.consequential = is_consequential(d)
    return d


@dataclass(slots=True)
class DisagreementDistribution:
    """Empirical distribution summary over a set of disagreements."""

    count: int
    mean_l2: float
    median_l2: float
    p95_l2: float
    mean_linf: float
    status_disagreement_rate: float
    consequential_rate: float
    taxonomy_counts: dict[str, int] = field(default_factory=dict)
    residual_dominance_counts: dict[str, int] = field(default_factory=dict)
    negative_result_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_disagreements(items: list[SolverDisagreement]) -> DisagreementDistribution:
    if not items:
        return DisagreementDistribution(
            count=0,
            mean_l2=0.0,
            median_l2=0.0,
            p95_l2=0.0,
            mean_linf=0.0,
            status_disagreement_rate=0.0,
            consequential_rate=0.0,
        )
    l2s = np.asarray(
        [d.corrected_action_l2 if np.isfinite(d.corrected_action_l2) else np.nan for d in items],
        dtype=np.float64,
    )
    finite = l2s[np.isfinite(l2s)]
    linfs = np.asarray(
        [d.corrected_action_linf if np.isfinite(d.corrected_action_linf) else np.nan for d in items],
        dtype=np.float64,
    )
    finite_linf = linfs[np.isfinite(linfs)]
    tax_counts: dict[str, int] = {}
    res_counts: dict[str, int] = {}
    for d in items:
        for lab in d.taxonomy_labels:
            tax_counts[lab] = tax_counts.get(lab, 0) + 1
        if d.residual_dominance_side:
            res_counts[d.residual_dominance_side] = res_counts.get(d.residual_dominance_side, 0) + 1
    n = len(items)
    return DisagreementDistribution(
        count=n,
        mean_l2=float(np.mean(finite)) if finite.size else float("nan"),
        median_l2=float(np.median(finite)) if finite.size else float("nan"),
        p95_l2=float(np.percentile(finite, 95)) if finite.size else float("nan"),
        mean_linf=float(np.mean(finite_linf)) if finite_linf.size else float("nan"),
        status_disagreement_rate=float(sum(1 for d in items if d.status_disagreement) / n),
        consequential_rate=float(sum(1 for d in items if d.consequential) / n),
        taxonomy_counts=dict(sorted(tax_counts.items())),
        residual_dominance_counts=dict(sorted(res_counts.items())),
        negative_result_count=sum(1 for d in items if d.negative_result_note),
    )


@dataclass(slots=True)
class FamilyDisagreementSummary:
    family: str
    n_cases: int
    n_shadowed: int
    distribution: DisagreementDistribution
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "n_cases": self.n_cases,
            "n_shadowed": self.n_shadowed,
            "distribution": self.distribution.as_dict(),
            "notes": self.notes,
        }


def summarize_by_family(
    cases: list[dict[str, Any]],
    *,
    disagreement_key: str = "disagreement",
    family_key: str = "family",
    shadowed_key: str = "shadowed",
) -> list[FamilyDisagreementSummary]:
    """Family-level summaries from shadow-harness case dicts or equivalent."""

    by_family: dict[str, list[tuple[bool, SolverDisagreement | None]]] = {}
    for case in cases:
        fam = str(case[family_key])
        shadowed = bool(case.get(shadowed_key, True))
        raw = case.get(disagreement_key)
        d: SolverDisagreement | None
        if raw is None:
            d = None
        elif isinstance(raw, SolverDisagreement):
            d = raw
        else:
            d = SolverDisagreement(
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
            if not d.taxonomy_labels:
                d.taxonomy_labels = classify_disagreement(d)
                d.consequential = is_consequential(d)
        by_family.setdefault(fam, []).append((shadowed, d))

    out: list[FamilyDisagreementSummary] = []
    for fam in sorted(by_family):
        rows = by_family[fam]
        shadowed_ds = [d for shadowed, d in rows if shadowed and d is not None]
        note = ""
        if shadowed_ds and all(not d.consequential for d in shadowed_ds):
            note = "negative_result: no consequential disagreement in this family under recorded settings"
        out.append(
            FamilyDisagreementSummary(
                family=fam,
                n_cases=len(rows),
                n_shadowed=sum(1 for shadowed, _ in rows if shadowed),
                distribution=summarize_disagreements(shadowed_ds),
                notes=note,
            )
        )
    return out
