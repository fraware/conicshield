"""Versioned solver-disagreement corpus export (deliverable §1 packaging).

Packages shadow-harness disagreement records into a versioned research artifact
with explicit schema. Does not alter production disagreement APIs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from conicshield.experimental.corpus.paths import CORPUS_VERSION, RESEARCH_ROOT
from conicshield.experimental.provenance import begin_experiment_provenance, finalize_experiment_provenance
from conicshield.experimental.solver_assurance.disagreement import (
    summarize_by_family,
    summarize_disagreements,
)
from conicshield.experimental.solver_assurance.sampling import SamplingPolicyId
from conicshield.experimental.solver_assurance.shadow_harness import run_shadow_harness

DISAGREEMENT_CORPUS_VERSION = "sdc-v0.1.0"
DISAGREEMENT_CORPUS_SCHEMA_ID = "research.solver_disagreement_corpus.v0"
DISAGREEMENT_CORPUS_ID = "research.solver_disagreement.corpus"


@dataclass(slots=True)
class DisagreementCorpusRecord:
    scenario_id: str
    family: str
    expected_regime: str
    shadowed: bool
    disagreement: dict[str, Any]
    primary_status: str
    shadow_status: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "family": self.family,
            "expected_regime": self.expected_regime,
            "shadowed": self.shadowed,
            "disagreement": dict(self.disagreement),
            "primary_status": self.primary_status,
            "shadow_status": self.shadow_status,
        }


@dataclass(slots=True)
class SolverDisagreementCorpus:
    schema_id: str = DISAGREEMENT_CORPUS_SCHEMA_ID
    corpus_id: str = DISAGREEMENT_CORPUS_ID
    disagreement_corpus_version: str = DISAGREEMENT_CORPUS_VERSION
    scenario_corpus_version: str = CORPUS_VERSION
    primary_backend: str = "cvxpy_clarabel"
    shadow_backend: str = "cvxpy_scs"
    records: list[DisagreementCorpusRecord] = field(default_factory=list)
    distribution: dict[str, Any] = field(default_factory=dict)
    family_summaries: list[dict[str, Any]] = field(default_factory=list)
    negative_results: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    promotion_status: str = "experimental"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "corpus_id": self.corpus_id,
            "disagreement_corpus_version": self.disagreement_corpus_version,
            "scenario_corpus_version": self.scenario_corpus_version,
            "primary_backend": self.primary_backend,
            "shadow_backend": self.shadow_backend,
            "n_records": len(self.records),
            "n_shadowed": sum(1 for r in self.records if r.shadowed),
            "records": [r.as_dict() for r in self.records],
            "distribution": dict(self.distribution),
            "family_summaries": list(self.family_summaries),
            "negative_results": list(self.negative_results),
            "provenance": dict(self.provenance),
            "promotion_status": self.promotion_status,
            "note": (
                "Public Clarabel/SCS disagreement packaging only. "
                "Not a governed production corpus; Moreau sidecar disagreements absent."
            ),
        }


def build_disagreement_corpus(
    *,
    primary_backend: str = "cvxpy_clarabel",
    shadow_backend: str = "cvxpy_scs",
    budget_fraction: float = 1.0,
    output_dir: Path | None = None,
    exact_command: str = "python -m conicshield.experimental.solver_assurance.disagreement_corpus",
) -> SolverDisagreementCorpus:
    """Run full-budget shadow harness and package disagreement records."""

    prov = begin_experiment_provenance(
        scenario_corpus_version=CORPUS_VERSION,
        backend=f"{primary_backend}|{shadow_backend}",
        exact_command=exact_command,
        random_seeds={"disagreement_corpus": 0},
        solver_settings={"budget_fraction": budget_fraction},
        tolerances={},
        warm_start_policy="cold",
        fallback_policy="record_only",
        solver_distribution="cvxpy",
        batch_size=1,
    )
    summary = run_shadow_harness(
        primary_backend=primary_backend,
        shadow_backend=shadow_backend,
        sampling_policy=SamplingPolicyId.RANDOM,
        budget_fraction=budget_fraction,
        exact_command=exact_command,
    )
    cases = list(summary.get("cases") or [])
    records: list[DisagreementCorpusRecord] = []
    from conicshield.experimental.solver_assurance.disagreement import SolverDisagreement

    disagreements = []
    for case in cases:
        raw = case.get("disagreement") or {}
        primary = case.get("primary") or {}
        shadow = case.get("shadow") or {}
        records.append(
            DisagreementCorpusRecord(
                scenario_id=str(case["scenario_id"]),
                family=str(case.get("family") or ""),
                expected_regime=str(case.get("expected_regime") or ""),
                shadowed=bool(case.get("shadowed")),
                disagreement=dict(raw),
                primary_status=str(primary.get("solver_status") or ""),
                shadow_status=str(shadow.get("solver_status") or ""),
            )
        )
        if case.get("shadowed") and raw:
            disagreements.append(
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

    dist = summarize_disagreements(disagreements)
    family = summarize_by_family(cases)
    negative = [f.notes for f in family if f.notes.startswith("negative_result")]
    corpus = SolverDisagreementCorpus(
        scenario_corpus_version=str(summary.get("corpus_version") or CORPUS_VERSION),
        primary_backend=primary_backend,
        shadow_backend=shadow_backend,
        records=records,
        distribution=dist.as_dict(),
        family_summaries=[f.as_dict() for f in family],
        negative_results=negative,
        provenance=finalize_experiment_provenance(prov).as_dict(),
    )

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        out = output_dir / "solver_disagreement_corpus.json"
        out.write_text(json.dumps(corpus.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        # Slim index without full action payloads for fixture retention
        index = {
            "schema_id": DISAGREEMENT_CORPUS_SCHEMA_ID,
            "disagreement_corpus_version": DISAGREEMENT_CORPUS_VERSION,
            "scenario_corpus_version": corpus.scenario_corpus_version,
            "n_records": len(records),
            "distribution": corpus.distribution,
            "family_summaries": corpus.family_summaries,
            "negative_results": corpus.negative_results,
            "promotion_status": corpus.promotion_status,
        }
        (output_dir / "solver_disagreement_corpus_index.json").write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        prov2 = finalize_experiment_provenance(prov, artifact_paths=[out])
        corpus.provenance = prov2.as_dict()
        out.write_text(json.dumps(corpus.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return corpus


def write_disagreement_corpus_fixture(*, path: Path | None = None) -> Path:
    """Write a slim index fixture under research/fixtures (not full corpus)."""

    corpus = build_disagreement_corpus(output_dir=None)
    index = {
        "schema_id": DISAGREEMENT_CORPUS_SCHEMA_ID,
        "disagreement_corpus_version": DISAGREEMENT_CORPUS_VERSION,
        "scenario_corpus_version": corpus.scenario_corpus_version,
        "n_records": len(corpus.records),
        "n_shadowed": sum(1 for r in corpus.records if r.shadowed),
        "distribution": corpus.distribution,
        "family_summaries": corpus.family_summaries,
        "negative_results": corpus.negative_results,
        "promotion_status": corpus.promotion_status,
    }
    out = path or (RESEARCH_ROOT / "fixtures" / "solver_disagreement_corpus_index.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Package solver-disagreement corpus")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/research/disagreement_corpus"),
    )
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args()
    corpus = build_disagreement_corpus(output_dir=args.output_dir)
    if args.write_fixture:
        fixture = write_disagreement_corpus_fixture()
        print(f"wrote fixture {fixture}")
    print(
        f"disagreement corpus {corpus.disagreement_corpus_version} "
        f"n={len(corpus.records)} consequential_rate="
        f"{(corpus.distribution or {}).get('consequential_rate')}"
    )


if __name__ == "__main__":
    main()
