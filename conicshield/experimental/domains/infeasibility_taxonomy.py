"""Machine-checkable unexplained-infeasibility taxonomy for CBF / filter probes (R5).

Classifies solver failures, infeasible, and near-infeasible outcomes with explicit
evidence fields. Cases that cannot be classified are labeled ``unexplained``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np

from conicshield.experimental.adapters.track1_protocols import CanonicalSolverStatus

INFEASIBILITY_TAXONOMY_SCHEMA_ID = "research.cbf_infeasibility_taxonomy.v0"
INFEASIBILITY_AUDIT_SCHEMA_ID = "research.cbf_infeasibility_audit.v0"


class InfeasibilityClass(StrEnum):
    FEASIBLE_OPTIMAL = "feasible_optimal"
    FEASIBLE_INACCURATE = "feasible_inaccurate"
    DECLARED_INFEASIBLE = "declared_infeasible"
    NEAR_INFEASIBLE_GEOMETRY = "near_infeasible_geometry"
    NUMERICAL_FAILURE = "numerical_failure"
    TIMEOUT_OR_ITERATION_LIMIT = "timeout_or_iteration_limit"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    NON_FINITE_ACTION = "non_finite_action"
    UNEXPLAINED = "unexplained"


@dataclass(slots=True)
class InfeasibilityClassification:
    case_id: str
    taxonomy_class: InfeasibilityClass
    is_failure: bool
    explained: bool
    evidence: dict[str, Any] = field(default_factory=dict)
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "taxonomy_class": str(self.taxonomy_class),
            "is_failure": self.is_failure,
            "explained": self.explained,
            "evidence": dict(self.evidence),
            "detail": self.detail,
        }


@dataclass(slots=True)
class InfeasibilityAuditReport:
    schema_id: str = INFEASIBILITY_AUDIT_SCHEMA_ID
    taxonomy_schema_id: str = INFEASIBILITY_TAXONOMY_SCHEMA_ID
    classifications: list[InfeasibilityClassification] = field(default_factory=list)
    n_probes: int = 0
    n_failures: int = 0
    n_unexplained: int = 0
    unexplained_rate: float = 0.0
    failure_rate: float = 0.0
    class_counts: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "taxonomy_schema_id": self.taxonomy_schema_id,
            "n_probes": self.n_probes,
            "n_failures": self.n_failures,
            "n_unexplained": self.n_unexplained,
            "unexplained_rate": self.unexplained_rate,
            "failure_rate": self.failure_rate,
            "class_counts": dict(self.class_counts),
            "classifications": [c.as_dict() for c in self.classifications],
            "notes": list(self.notes),
            "promotion_claim": False,
        }


def _status_str(result: Any) -> str:
    return str(getattr(result, "solver_status", "") or "")


def _canonical(result: Any) -> str:
    cs = getattr(result, "canonical_status", None)
    if cs is None:
        return ""
    return str(cs.value if hasattr(cs, "value") else cs)


def _barrier(result: Any) -> float:
    return float(getattr(result, "barrier_value", float("nan")))


def _u_safe(result: Any) -> np.ndarray:
    return np.asarray(result.u_safe, dtype=np.float64).reshape(-1)


def classify_filter_result(
    result: Any,
    *,
    case_id: str | None = None,
    near_infeasible_barrier_threshold: float = 0.05,
) -> InfeasibilityClassification:
    """Classify a single CBFFilterResult-like object into the taxonomy."""

    cid = case_id or str(getattr(result, "agent_id", "unknown"))
    status = _status_str(result).lower()
    canon = _canonical(result).lower()
    u = _u_safe(result)
    finite = bool(np.all(np.isfinite(u)))
    barrier = _barrier(result)
    meta = dict(getattr(result, "metadata", None) or {})

    evidence: dict[str, Any] = {
        "solver_status": _status_str(result),
        "canonical_status": _canonical(result),
        "barrier_value": barrier,
        "safety_margin": float(getattr(result, "safety_margin", float("nan"))),
        "u_finite": finite,
        "fallback": bool(getattr(result, "fallback", False)),
        "stage": str(getattr(result, "stage", "")),
        "baseline": str(getattr(result, "baseline", "")),
    }

    # Feasible paths
    if finite and ("optimal" in status or canon == CanonicalSolverStatus.OPTIMAL.value):
        if "inaccurate" in status:
            return InfeasibilityClassification(
                cid,
                InfeasibilityClass.FEASIBLE_INACCURATE,
                is_failure=False,
                explained=True,
                evidence=evidence,
                detail="solver returned optimal_inaccurate with finite action",
            )
        return InfeasibilityClassification(
            cid,
            InfeasibilityClass.FEASIBLE_OPTIMAL,
            is_failure=False,
            explained=True,
            evidence=evidence,
            detail="solver returned optimal with finite action",
        )

    # Backend unavailable
    if (
        "unavailable" in status
        or canon == CanonicalSolverStatus.UNAVAILABLE.value
        or meta.get("stub") is True
        or meta.get("unavailable") is True
    ):
        return InfeasibilityClassification(
            cid,
            InfeasibilityClass.BACKEND_UNAVAILABLE,
            is_failure=True,
            explained=True,
            evidence={**evidence, "metadata": meta},
            detail="backend unavailable or fail-closed filter path",
        )

    # Timeout / iteration
    if (
        "time" in status
        or "iter" in status
        or canon
        in {
            CanonicalSolverStatus.TIME_LIMIT.value,
            CanonicalSolverStatus.ITERATION_LIMIT.value,
        }
    ):
        return InfeasibilityClassification(
            cid,
            InfeasibilityClass.TIMEOUT_OR_ITERATION_LIMIT,
            is_failure=True,
            explained=True,
            evidence=evidence,
            detail="timeout or iteration limit",
        )

    # Declared infeasible
    if "infeas" in status or canon == CanonicalSolverStatus.INFEASIBLE.value:
        near = np.isfinite(barrier) and barrier < near_infeasible_barrier_threshold
        cls = (
            InfeasibilityClass.NEAR_INFEASIBLE_GEOMETRY
            if near
            else InfeasibilityClass.DECLARED_INFEASIBLE
        )
        return InfeasibilityClassification(
            cid,
            cls,
            is_failure=True,
            explained=True,
            evidence={**evidence, "near_infeasible_geometry": near},
            detail="solver declared infeasible" + (" (near-boundary geometry)" if near else ""),
        )

    # Numerical failure
    if (
        "error" in status
        or "numeric" in status
        or canon == CanonicalSolverStatus.NUMERICAL_FAILURE.value
    ):
        return InfeasibilityClassification(
            cid,
            InfeasibilityClass.NUMERICAL_FAILURE,
            is_failure=True,
            explained=True,
            evidence=evidence,
            detail="numerical failure or solver error",
        )

    # Non-finite action without other classification
    if not finite:
        # If barrier strongly negative, treat as near-infeasible geometry evidence
        if np.isfinite(barrier) and barrier < 0.0:
            return InfeasibilityClassification(
                cid,
                InfeasibilityClass.NEAR_INFEASIBLE_GEOMETRY,
                is_failure=True,
                explained=True,
                evidence={**evidence, "inferred_from": "non_finite_action_and_negative_barrier"},
                detail="non-finite action with negative barrier (near/inside obstacle)",
            )
        return InfeasibilityClassification(
            cid,
            InfeasibilityClass.NON_FINITE_ACTION,
            is_failure=True,
            explained=True,
            evidence=evidence,
            detail="non-finite corrected action",
        )

    # Residual catch: status not optimal but finite action — still a failure path
    if status not in {"optimal", "optimal_inaccurate", "no_filter"}:
        return InfeasibilityClassification(
            cid,
            InfeasibilityClass.UNEXPLAINED,
            is_failure=True,
            explained=False,
            evidence=evidence,
            detail=f"unclassified failure status={status!r}",
        )

    # Finite action with unexpected path → unexplained only if we cannot assert feasibility
    return InfeasibilityClassification(
        cid,
        InfeasibilityClass.UNEXPLAINED,
        is_failure=True,
        explained=False,
        evidence=evidence,
        detail="could not assign taxonomy class",
    )


def audit_infeasibility(
    results: list[Any],
    *,
    case_ids: list[str] | None = None,
) -> InfeasibilityAuditReport:
    """Classify a probe bank and compute unexplained-infeasibility rate."""

    classifications: list[InfeasibilityClassification] = []
    for i, r in enumerate(results):
        cid = case_ids[i] if case_ids and i < len(case_ids) else None
        classifications.append(classify_filter_result(r, case_id=cid))

    n = len(classifications)
    failures = [c for c in classifications if c.is_failure]
    unexplained = [c for c in classifications if c.taxonomy_class == InfeasibilityClass.UNEXPLAINED]
    counts: dict[str, int] = {}
    for c in classifications:
        key = str(c.taxonomy_class)
        counts[key] = counts.get(key, 0) + 1

    notes = [
        "Taxonomy is research-local and machine-checkable; not a production safety certificate.",
        "Unexplained rate uses all probes as denominator (failures without taxonomy class).",
    ]
    if unexplained:
        notes.append(f"{len(unexplained)} unexplained failure(s) require investigation before stage-4 unblock.")

    return InfeasibilityAuditReport(
        classifications=classifications,
        n_probes=n,
        n_failures=len(failures),
        n_unexplained=len(unexplained),
        unexplained_rate=float(len(unexplained) / max(n, 1)),
        failure_rate=float(len(failures) / max(n, 1)),
        class_counts=dict(sorted(counts.items())),
        notes=notes,
    )


def write_infeasibility_audit(path: Path, report: InfeasibilityAuditReport) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main() -> None:
    from conicshield.experimental.domains.cbf_corpus import probe_cbf_filter_bank

    probes = probe_cbf_filter_bank()
    report = audit_infeasibility(probes)
    out = Path("output/research/cbf_infeasibility_audit.json")
    write_infeasibility_audit(out, report)
    print(
        f"infeasibility audit n={report.n_probes} failures={report.n_failures} "
        f"unexplained_rate={report.unexplained_rate:.4f} classes={report.class_counts}"
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
