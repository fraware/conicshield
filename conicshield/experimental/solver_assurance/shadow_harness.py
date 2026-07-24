"""Public-solver shadow harness for Track 2 R10 shadow-sampling science."""

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
    compute_boundary_features,
    scenario_seed_from_master,
    select_for_shadow_detailed,
)
from conicshield.specs.shield_qp import parse_safety_spec_for_shield


@dataclass(slots=True)
class ShadowCaseResult:
    scenario_id: str
    family: str
    primary_backend: str
    shadow_backend: str
    primary: ResearchProjectionResult
    shadow: ResearchProjectionResult | None
    disagreement: SolverDisagreement | None
    shadowed: bool
    sampling_status: str = "selected"
    boundary_features: dict[str, Any] | None = None
    fault_injection: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "family": self.family,
            "primary_backend": self.primary_backend,
            "shadow_backend": self.shadow_backend,
            "shadowed": self.shadowed,
            "sampling_status": self.sampling_status,
            "primary": self.primary.as_dict(),
            # Skipped shadow must be absent — never a copied primary payload.
            "shadow": None if self.shadow is None else self.shadow.as_dict(),
            "disagreement": None if self.disagreement is None else self.disagreement.as_dict(),
            "boundary_features": None if self.boundary_features is None else dict(self.boundary_features),
            "fault_injection": None if self.fault_injection is None else dict(self.fault_injection),
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


def _merge_solver_extras(scenario: dict[str, Any], *, role: str) -> dict[str, Any]:
    """Merge base extras with optional primary/shadow overrides (fault-injection aware)."""

    extras = dict(scenario.get("extras") or {})
    role_key = "primary_overrides" if role == "primary" else "shadow_overrides"
    overrides = extras.get(role_key)
    if isinstance(overrides, dict):
        extras = {**extras, **overrides}
    return extras


def _fault_injection_meta(scenario: dict[str, Any]) -> dict[str, Any] | None:
    extras = scenario.get("extras") or {}
    if not extras.get("fault_injection"):
        return None
    return {
        "fault_injection": True,
        "fault_injection_kind": extras.get("fault_injection_kind"),
        "fault_injection_label": extras.get("fault_injection_label")
        or extras.get("fault_injection_kind"),
        "notes": extras.get("fault_injection_notes"),
    }


def _projector_kwargs(extras: dict[str, Any]) -> dict[str, Any]:
    return {
        "max_iter": extras.get("suggested_max_iter"),
        "time_limit": extras.get("suggested_time_limit"),
        "warm_start": bool(extras.get("warm_start", False)),
    }


def run_shadow_harness(
    *,
    primary_backend: str = "cvxpy_clarabel",
    shadow_backend: str = "cvxpy_scs",
    sampling_policy: SamplingPolicyId | str = SamplingPolicyId.RESIDUAL,
    budget_fraction: float = 1.0,
    master_seed: int = 0,
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
        random_seeds={"harness_master_seed": int(master_seed)},
        solver_settings={
            "budget_fraction": budget_fraction,
            "sampling_policy": str(sampling_policy),
            "master_seed": int(master_seed),
            "tie_break_rule": "score_desc_then_ranking_value_desc_then_scenario_id_asc",
        },
        tolerances={"action_l2": 1e-6},
        warm_start_policy="cold",
        fallback_policy="record_stub",
        solver_distribution="cvxpy",
        batch_size=1,
    )

    # First pass: primary solves for sampling scores
    primary_results: dict[str, ResearchProjectionResult] = {}
    boundary_by_id: dict[str, dict[str, Any]] = {}
    contexts: list[SamplingContext] = []
    # Track prior active set within each family (corpus order) for change features.
    previous_active_by_family: dict[str, tuple[str, ...]] = {}
    for scenario in scenarios:
        spec, load_meta = _spec_from_scenario(scenario)
        extras = _merge_solver_extras(scenario, role="primary")
        projector = create_research_projector(
            backend_id=primary_backend,
            spec=spec,
            **_projector_kwargs(extras),
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
        family = str(scenario["family"])
        primary_results[sid] = primary
        data = parse_safety_spec_for_shield(spec)
        prev_active = previous_active_by_family.get(family)
        warm_rejected = str(scenario.get("expected_regime", "")).endswith("failure") or bool(
            extras.get("warm_start_rejected")
        )
        feats = compute_boundary_features(
            corrected_action=primary.corrected_action,
            previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
            lower=np.asarray(data.lower, dtype=np.float64),
            upper=np.asarray(data.upper, dtype=np.float64),
            max_delta=np.asarray(data.max_delta, dtype=np.float64),
            simplex_total=float(data.simplex_total),
            active_constraints=primary.active_constraints,
            previous_active_set=prev_active,
            equality_residual=primary.equality_residual,
            inequality_residual=primary.inequality_residual,
            iterations=primary.iterations,
            warm_started=bool(primary.warm_started),
            warm_start_rejected=warm_rejected,
            policy_weight=float(weights.get("policy_weight", 1.0)),
            reference_weight=float(weights.get("reference_weight", 0.0)),
        )
        boundary_by_id[sid] = feats.as_dict()
        previous_active_by_family[family] = tuple(primary.active_constraints)
        contexts.append(
            SamplingContext(
                scenario_id=sid,
                structural_fingerprint=_fingerprint(scenario),
                primary=primary,
                previous_active_set=prev_active,
                boundary_features=feats,
                recent_failure_count=1
                if primary.canonical_status.value in {"numerical_failure", "unavailable"}
                else 0,
                upgrade_event=str(scenario["family"]) == "backend_version_changes",
                warm_start_rejected=warm_rejected,
                scenario_seed=scenario_seed_from_master(master_seed=master_seed, scenario_id=sid),
            )
        )

    policies = {str(p.policy_id): p for p in all_sampling_policies(master_seed=master_seed)}
    policy = policies[str(sampling_policy)]
    selection = select_for_shadow_detailed(
        contexts,
        policy,
        budget_fraction=budget_fraction,
        master_seed=master_seed,
    )
    selected = set(selection.selected_ids)

    case_results: list[ShadowCaseResult] = []
    for scenario in scenarios:
        sid = str(scenario["scenario_id"])
        primary = primary_results[sid]
        shadowed = sid in selected
        fault_meta = _fault_injection_meta(scenario)
        if shadowed:
            spec, load_meta = _spec_from_scenario(scenario)
            extras = _merge_solver_extras(scenario, role="shadow")
            shadow_proj = create_research_projector(
                backend_id=shadow_backend,
                spec=spec,
                **_projector_kwargs(extras),
            )
            weights = scenario.get("weights") or {}
            shadow: ResearchProjectionResult | None = shadow_proj.project(
                np.asarray(scenario["proposed_action"], dtype=np.float64),
                np.asarray(scenario["previous_action"], dtype=np.float64),
                reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
                policy_weight=float(weights.get("policy_weight", 1.0)),
                reference_weight=float(weights.get("reference_weight", 0.0)),
                metadata={
                    "scenario_id": sid,
                    "role": "shadow",
                    "spec_load": load_meta,
                    "fault_injection": fault_meta,
                },
            )
            disagreement: SolverDisagreement | None = compare_projections(primary, shadow)
            sampling_status = "selected"
        else:
            # Sampling skipped optional secondary solve — leave shadow evidence absent.
            shadow = None
            disagreement = None
            sampling_status = "skipped_by_sampling"
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
                sampling_status=sampling_status,
                boundary_features=boundary_by_id.get(sid),
                fault_injection=fault_meta,
            )
        )

    shadowed_disagreements = [c.disagreement for c in case_results if c.shadowed and c.disagreement is not None]
    case_dicts = [c.as_dict() for c in case_results]
    family_summaries = [s.as_dict() for s in summarize_by_family(case_dicts)]
    overall = summarize_disagreements(shadowed_disagreements)
    negative_notes = [
        f"{c.scenario_id}: {c.disagreement.negative_result_note}"
        for c in case_results
        if c.shadowed and c.disagreement is not None and c.disagreement.negative_result_note
    ]
    negative_notes.extend(s["notes"] for s in family_summaries if s.get("notes"))

    summary = {
        "corpus_version": manifest.get("corpus_version"),
        "primary_backend": primary_backend,
        "shadow_backend": shadow_backend,
        "sampling_policy": str(sampling_policy),
        "budget_fraction": budget_fraction,
        "master_seed": int(master_seed),
        "scenario_count": len(case_results),
        "shadowed_count": sum(1 for c in case_results if c.shadowed),
        "status_disagreement_count": sum(
            1 for c in case_results if c.shadowed and c.disagreement is not None and c.disagreement.status_disagreement
        ),
        "consequential_count": sum(
            1 for c in case_results if c.shadowed and c.disagreement is not None and c.disagreement.consequential
        ),
        "mean_l2_when_shadowed": float(
            np.nanmean(
                [
                    c.disagreement.corrected_action_l2
                    for c in case_results
                    if c.shadowed and c.disagreement is not None
                ]
                or [0.0]
            )
        ),
        "disagreement_distribution": overall.as_dict(),
        "family_summaries": family_summaries,
        "negative_results": sorted({n for n in negative_notes if n}),
        "backend_capabilities": caps,
        "sampling_selection": selection.as_dict(),
        "promotion_note": (
            "Sampling affects only the optional secondary (shadow) solve; "
            "primary verification remains complete for every scenario. "
            "Production recommendation remains blocked until real deployment distributions."
        ),
        "production_recommendation_blocked": True,
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
