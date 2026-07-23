"""Candidate-stack promotion research protocol (R1) — runnable experiment."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from conicshield.experimental.corpus.paths import CORPUS_VERSION
from conicshield.experimental.provenance import begin_experiment_provenance, finalize_experiment_provenance
from conicshield.experimental.solver_assurance.disagreement import (
    summarize_by_family,
    summarize_disagreements,
)
from conicshield.experimental.solver_assurance.sampling import SamplingPolicyId
from conicshield.experimental.solver_assurance.shadow_harness import run_shadow_harness

PROMOTION_PROTOCOL_SCHEMA_ID = "research.candidate_stack_promotion.v1"
PROMOTION_PROTOCOL_VERSION = "csp-v0.2.0"


@dataclass(slots=True)
class CandidateStackPromotionProtocol:
    """Research protocol: candidate stack runs in shadow against approved stack."""

    approved_backend: str
    candidate_backend: str
    protocol_version: str = PROMOTION_PROTOCOL_VERSION
    metrics_required: tuple[str, ...] = (
        "disagreement_frequency",
        "action_difference_distribution",
        "residual_dominance",
        "performance_changes",
        "failure_asymmetry",
        "affected_scenario_families",
        "taxonomy_counts",
        "per_family_consequential_rates",
        "retained_artifact_paths",
    )
    promotion_gate: str = (
        "Advanced sampling may enter production only when mandatory verification "
        "remains complete and sampling affects only the optional secondary solve. "
        "Candidate stacks are not promoted without disagreement frequency, "
        "action-diff distributions, residual dominance, failure asymmetry, "
        "and affected-family evidence."
    )
    notes: str = (
        "Public Clarabel vs SCS comparison is the default runnable experiment. "
        "Native/vendor candidate stacks are exercised when available; otherwise recorded as unavailable."
    )
    hypotheses: tuple[str, ...] = (
        "Active-set changes predict solver disagreement better than raw proposal distance.",
        "Residual-based sampling detects most consequential disagreements at substantially "
        "lower shadow cost than uniform sampling.",
        "Warm-start anomalies are early signals of solver instability.",
        "Cross-platform disagreement is dominated by a small number of conditioning regimes.",
    )
    results: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": PROMOTION_PROTOCOL_SCHEMA_ID,
            "protocol_version": self.protocol_version,
            "approved_backend": self.approved_backend,
            "candidate_backend": self.candidate_backend,
            "metrics_required": list(self.metrics_required),
            "promotion_gate": self.promotion_gate,
            "notes": self.notes,
            "hypotheses": list(self.hypotheses),
            "results": dict(self.results),
            "production_promotion_claimed": False,
        }


def _action_diff_distribution(cases: list[dict[str, Any]]) -> dict[str, float]:
    l2s = [
        float(c["disagreement"]["corrected_action_l2"])
        for c in cases
        if c.get("shadowed") and np.isfinite(float(c["disagreement"]["corrected_action_l2"]))
    ]
    if not l2s:
        return {"count": 0.0, "mean": 0.0, "median": 0.0, "p95": 0.0, "max": 0.0}
    arr = np.asarray(l2s, dtype=np.float64)
    return {
        "count": float(arr.size),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "p95": float(np.percentile(arr, 95)),
        "max": float(np.max(arr)),
    }


def run_candidate_stack_promotion(
    *,
    approved_backend: str = "cvxpy_clarabel",
    candidate_backend: str = "cvxpy_scs",
    output_dir: Path | None = None,
    exact_command: str = "python -m conicshield.experimental.solver_assurance.promotion_protocol",
) -> CandidateStackPromotionProtocol:
    """Compare candidate vs approved public stacks with required promotion metrics."""

    provenance = begin_experiment_provenance(
        scenario_corpus_version=CORPUS_VERSION,
        backend=f"{approved_backend}|{candidate_backend}",
        exact_command=exact_command,
        random_seeds={"promotion": 0},
        solver_settings={"budget_fraction": 1.0},
        tolerances={},
        warm_start_policy="cold",
        fallback_policy="record_only",
        solver_distribution="cvxpy",
        batch_size=1,
    )

    summary = run_shadow_harness(
        primary_backend=approved_backend,
        shadow_backend=candidate_backend,
        sampling_policy=SamplingPolicyId.RANDOM,
        budget_fraction=1.0,
        exact_command=exact_command,
    )
    cases = list(summary.get("cases") or [])
    shadowed = [c for c in cases if c.get("shadowed")]
    n = max(len(shadowed), 1)

    from conicshield.experimental.solver_assurance.disagreement import SolverDisagreement

    disagreements = []
    failure_asymmetry = 0
    for c in shadowed:
        raw = c["disagreement"]
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
        disagreements.append(d)
        labels = set(d.taxonomy_labels)
        if "failure_asymmetry" in labels or d.timeout_asymmetry:
            failure_asymmetry += 1

    dist = summarize_disagreements(disagreements)
    family = summarize_by_family(cases)
    affected = [
        f.family for f in family if f.distribution.consequential_rate > 0 or f.distribution.status_disagreement_rate > 0
    ]

    # Performance proxy: iteration ratio when available
    iter_ratios = [d.iteration_ratio for d in disagreements if d.iteration_ratio is not None]
    performance = {
        "mean_iteration_ratio_candidate_over_approved": float(np.mean(iter_ratios)) if iter_ratios else None,
        "note": "Proxy only; wall-clock not claimed as production SLA.",
    }

    per_family_rates = {f.family: float(f.distribution.consequential_rate) for f in family}
    results = {
        "corpus_version": summary.get("corpus_version"),
        "protocol_version": PROMOTION_PROTOCOL_VERSION,
        "disagreement_frequency": {
            "status_disagreement_rate": dist.status_disagreement_rate,
            "consequential_rate": dist.consequential_rate,
            "n_shadowed": len(shadowed),
        },
        "action_difference_distribution": _action_diff_distribution(cases),
        "residual_dominance": dist.residual_dominance_counts,
        "performance_changes": performance,
        "failure_asymmetry": {
            "count": failure_asymmetry,
            "rate": float(failure_asymmetry / n),
        },
        "affected_scenario_families": affected,
        "family_summaries": [f.as_dict() for f in family],
        "taxonomy_counts": dist.taxonomy_counts,
        "per_family_consequential_rates": per_family_rates,
        "backend_capabilities": summary.get("backend_capabilities"),
        "negative_results": [f.notes for f in family if f.notes.startswith("negative_result")],
        "retained_artifact_paths": [],
    }

    provenance = finalize_experiment_provenance(provenance)
    results["provenance"] = provenance.as_dict()

    protocol = CandidateStackPromotionProtocol(
        approved_backend=approved_backend,
        candidate_backend=candidate_backend,
        results=results,
    )

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "candidate_stack_promotion.json"
        # Retain denser artifacts for nightly / publication packaging
        family_path = output_dir / "candidate_stack_family_summaries.json"
        tax_path = output_dir / "candidate_stack_taxonomy_counts.json"
        family_path.write_text(
            json.dumps([f.as_dict() for f in family], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tax_path.write_text(
            json.dumps(dist.taxonomy_counts, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        retained = [
            str(out_path.as_posix()),
            str(family_path.as_posix()),
            str(tax_path.as_posix()),
            str((output_dir / "provenance.json").as_posix()),
        ]
        protocol.results["retained_artifact_paths"] = retained
        out_path.write_text(json.dumps(protocol.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        provenance = finalize_experiment_provenance(provenance, artifact_paths=[out_path, family_path, tax_path])
        provenance.to_json(output_dir / "provenance.json")
        protocol.results["provenance"] = provenance.as_dict()
        protocol.results["retained_artifact_paths"] = retained
        out_path.write_text(json.dumps(protocol.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return protocol


def main() -> None:
    out = Path("output/research/candidate_stack_promotion")
    protocol = run_candidate_stack_promotion(output_dir=out)
    freq = protocol.results.get("disagreement_frequency") or {}
    print(
        f"promotion protocol: {protocol.approved_backend} vs {protocol.candidate_backend}; "
        f"status_rate={freq.get('status_disagreement_rate')}; "
        f"consequential_rate={freq.get('consequential_rate')}"
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
