"""Public-solver shadow harness for Track 2 R1 wave 1."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from conicshield.experimental.adapters.projection import ResearchProjectionResult
from conicshield.experimental.corpus.generate import load_all_scenarios, load_manifest
from conicshield.experimental.corpus.paths import CORPUS_VERSION
from conicshield.experimental.corpus.spec_load import load_research_safety_spec
from conicshield.experimental.provenance import (
    begin_experiment_provenance,
    finalize_experiment_provenance,
)
from conicshield.experimental.solver_assurance.backends import (
    create_research_projector,
    probe_backend_capabilities,
)
from conicshield.experimental.solver_assurance.disagreement import (
    SolverDisagreement,
    compare_projections,
    summarize_by_family,
    summarize_disagreements,
)
from conicshield.experimental.solver_assurance.sampling import (
    SamplingContext,
    SamplingPolicyId,
    all_sampling_policies,
    select_for_shadow,
)


@dataclass(slots=True)
class ShadowCaseResult:
    scenario_id: str
    family: str
    primary_backend: str
    shadow_backend: str
    primary: ResearchProjectionResult
    shadow: ResearchProjectionResult
    disagreement: SolverDisagreement
    shadowed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "family": self.family,
            "primary_backend": self.primary_backend,
            "shadow_backend": self.shadow_backend,
            "shadowed": self.shadowed,
            "primary": self.primary.as_dict(),
            "shadow": self.shadow.as_dict(),
            "disagreement": self.disagreement.as_dict(),
        }


def _spec_from_scenario(scenario: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    spec, meta = load_research_safety_spec(scenario)
    return spec, meta


def _fingerprint(scenario: dict[str, Any]) -> str:
    payload = json.dumps(
        {
            "family": scenario["family"],
            "spec": scenario["spec"],
            "expected_regime": scenario["expected_regime"],
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def run_shadow_harness(
    *,
    primary_backend: str = "cvxpy_clarabel",
    shadow_backend: str = "cvxpy_scs",
    sampling_policy: SamplingPolicyId | str = SamplingPolicyId.RESIDUAL,
    budget_fraction: float = 1.0,
    output_dir: Path | None = None,
    exact_command: str = "python -m conicshield.experimental.solver_assurance.shadow_harness",
) -> dict[str, Any]:
    """Run primary vs shadow comparison over the versioned corpus."""

    manifest = load_manifest()
    scenarios = load_all_scenarios()
    caps = [c.as_dict() for c in probe_backend_capabilities()]

    provenance = begin_experiment_provenance(
        scenario_corpus_version=str(manifest.get("corpus_version", CORPUS_VERSION)),
        backend=f"{primary_backend}|{shadow_backend}",
        exact_command=exact_command,
        random_seeds={"harness": 0},
        solver_settings={"budget_fraction": budget_fraction, "sampling_policy": str(sampling_policy)},
        tolerances={"action_l2": 1e-6},
        warm_start_policy="cold",
        fallback_policy="record_stub",
        solver_distribution="cvxpy",
        batch_size=1,
    )

    # First pass: primary solves for sampling scores
    primary_results: dict[str, ResearchProjectionResult] = {}
    contexts: list[SamplingContext] = []
    for scenario in scenarios:
        spec, load_meta = _spec_from_scenario(scenario)
        extras = scenario.get("extras") or {}
        max_iter = extras.get("suggested_max_iter")
        time_limit = extras.get("suggested_time_limit")
        projector = create_research_projector(
            backend_id=primary_backend,
            spec=spec,
            max_iter=max_iter,
            time_limit=time_limit,
        )
        weights = scenario.get("weights") or {}
        primary = projector.project(
            np.asarray(scenario["proposed_action"], dtype=np.float64),
            np.asarray(scenario["previous_action"], dtype=np.float64),
            reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
            policy_weight=float(weights.get("policy_weight", 1.0)),
            reference_weight=float(weights.get("reference_weight", 0.0)),
            metadata={"scenario_id": scenario["scenario_id"], "spec_load": load_meta},
        )
        sid = str(scenario["scenario_id"])
        primary_results[sid] = primary
        contexts.append(
            SamplingContext(
                scenario_id=sid,
                structural_fingerprint=_fingerprint(scenario),
                primary=primary,
                boundary_distance=float(primary.inequality_residual or 0.0),
                recent_failure_count=1 if primary.canonical_status.value in {"numerical_failure", "unavailable"} else 0,
                upgrade_event=str(scenario["family"]) == "backend_version_changes",
                warm_start_rejected=str(scenario.get("expected_regime", "")).endswith("failure"),
            )
        )

    policies = {str(p.policy_id): p for p in all_sampling_policies()}
    policy = policies[str(sampling_policy)]
    selected = set(select_for_shadow(contexts, policy, budget_fraction=budget_fraction))

    case_results: list[ShadowCaseResult] = []
    for scenario in scenarios:
        sid = str(scenario["scenario_id"])
        primary = primary_results[sid]
        shadowed = sid in selected
        if shadowed:
            spec, load_meta = _spec_from_scenario(scenario)
            extras = scenario.get("extras") or {}
            shadow_proj = create_research_projector(
                backend_id=shadow_backend,
                spec=spec,
                max_iter=extras.get("suggested_max_iter"),
                time_limit=extras.get("suggested_time_limit"),
            )
            weights = scenario.get("weights") or {}
            shadow = shadow_proj.project(
                np.asarray(scenario["proposed_action"], dtype=np.float64),
                np.asarray(scenario["previous_action"], dtype=np.float64),
                reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
                policy_weight=float(weights.get("policy_weight", 1.0)),
                reference_weight=float(weights.get("reference_weight", 0.0)),
                metadata={"scenario_id": sid, "role": "shadow", "spec_load": load_meta},
            )
        else:
            # Placeholder: sampling skipped optional secondary solve
            shadow = ResearchProjectionResult(
                proposed_action=primary.proposed_action.copy(),
                corrected_action=primary.corrected_action.copy(),
                intervened=primary.intervened,
                intervention_norm=primary.intervention_norm,
                solver_status="skipped_by_sampling",
                canonical_status=primary.canonical_status,
                metadata={"shadowed": False},
            )
        disagreement = compare_projections(primary, shadow)
        case_results.append(
            ShadowCaseResult(
                scenario_id=sid,
                family=str(scenario["family"]),
                primary_backend=primary_backend,
                shadow_backend=shadow_backend,
                primary=primary,
                shadow=shadow,
                disagreement=disagreement,
                shadowed=shadowed,
            )
        )

    shadowed_disagreements = [c.disagreement for c in case_results if c.shadowed]
    case_dicts = [c.as_dict() for c in case_results]
    family_summaries = [s.as_dict() for s in summarize_by_family(case_dicts)]
    overall = summarize_disagreements(shadowed_disagreements)
    negative_notes = [
        f"{c.scenario_id}: {c.disagreement.negative_result_note}"
        for c in case_results
        if c.shadowed and c.disagreement.negative_result_note
    ]
    negative_notes.extend(s["notes"] for s in family_summaries if s.get("notes"))

    summary = {
        "corpus_version": manifest.get("corpus_version"),
        "primary_backend": primary_backend,
        "shadow_backend": shadow_backend,
        "sampling_policy": str(sampling_policy),
        "budget_fraction": budget_fraction,
        "scenario_count": len(case_results),
        "shadowed_count": sum(1 for c in case_results if c.shadowed),
        "status_disagreement_count": sum(1 for c in case_results if c.shadowed and c.disagreement.status_disagreement),
        "consequential_count": sum(1 for c in case_results if c.shadowed and c.disagreement.consequential),
        "mean_l2_when_shadowed": float(
            np.nanmean([c.disagreement.corrected_action_l2 for c in case_results if c.shadowed] or [0.0])
        ),
        "disagreement_distribution": overall.as_dict(),
        "family_summaries": family_summaries,
        "negative_results": sorted({n for n in negative_notes if n}),
        "backend_capabilities": caps,
        "promotion_note": (
            "Sampling affects only the optional secondary (shadow) solve; "
            "primary verification remains complete for every scenario."
        ),
        "cases": case_dicts,
    }

    provenance = finalize_experiment_provenance(provenance)
    summary["provenance"] = provenance.as_dict()

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "shadow_harness_results.json"
        out_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        provenance.to_json(output_dir / "provenance.json")
        finalize_experiment_provenance(provenance, artifact_paths=[out_path])
        provenance.to_json(output_dir / "provenance.json")

    return summary


def main() -> None:
    out = Path("output/research/shadow_harness")
    summary = run_shadow_harness(output_dir=out)
    print(
        f"shadow harness: {summary['shadowed_count']}/{summary['scenario_count']} shadowed; "
        f"status disagreements={summary['status_disagreement_count']}"
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
