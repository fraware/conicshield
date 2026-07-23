#!/usr/bin/env python3
"""Wave 4: AssuranceBundle construction, replay, CBF domain stages 1–2."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from conicshield.experimental.assurance.builder import build_assurance_bundle
from conicshield.experimental.assurance.checks import corrupt_bundle_action, run_machine_checks
from conicshield.experimental.assurance.migration import migration_doc
from conicshield.experimental.assurance.replay import bundle_to_json, replay_bundle
from conicshield.experimental.corpus.generate import load_all_scenarios, load_manifest
from conicshield.experimental.domains.cbf_2d import (
    CBF2DDomain,
    compute_cbf_metrics,
    demo_stage1_scenario,
    demo_stage2_batch,
)
from conicshield.experimental.solver_assurance.disagreement import compare_projections
from conicshield.experimental.solver_assurance.shadow_harness import run_shadow_harness

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "research" / "wave4"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ASSURANCE_MIGRATION.txt").write_text(migration_doc(), encoding="utf-8")

    # Use one shadowed corpus case to build a real bundle
    summary = run_shadow_harness(
        budget_fraction=1.0,
        exact_command="python experiments/research_wave4/run_assurance_and_cbf.py",
    )
    case = next(c for c in summary["cases"] if c["shadowed"])
    from conicshield.experimental.adapters.projection import ResearchProjectionResult
    from conicshield.experimental.adapters.track1_protocols import CanonicalSolverStatus, SolverProvenance

    def _to_result(d: dict) -> ResearchProjectionResult:
        return ResearchProjectionResult(
            proposed_action=np.asarray(d["proposed_action"], dtype=np.float64),
            corrected_action=np.asarray(d["corrected_action"], dtype=np.float64),
            intervened=bool(d["intervened"]),
            intervention_norm=float(d["intervention_norm"]),
            solver_status=str(d["solver_status"]),
            canonical_status=CanonicalSolverStatus(str(d["canonical_status"])),
            objective_value=d.get("objective_value"),
            active_constraints=list(d.get("active_constraints") or []),
            equality_residual=d.get("equality_residual"),
            inequality_residual=d.get("inequality_residual"),
            iterations=d.get("iterations"),
            provenance=SolverProvenance(
                backend_id=str((d.get("provenance") or {}).get("backend_id", "unknown")),
                solver_name=str((d.get("provenance") or {}).get("solver_name", "unknown")),
                solver_version=(d.get("provenance") or {}).get("solver_version"),
                package_distribution=(d.get("provenance") or {}).get("package_distribution"),
                package_version=(d.get("provenance") or {}).get("package_version"),
            )
            if d.get("provenance")
            else None,
        )

    primary = _to_result(case["primary"])
    shadow = _to_result(case["shadow"])
    disagreement = compare_projections(primary, shadow)
    scenario = next(s for s in load_all_scenarios() if s["scenario_id"] == case["scenario_id"])
    bundle = build_assurance_bundle(
        primary=primary,
        specification=scenario["spec"],
        shadow=shadow,
        disagreement=disagreement,
        shadow_backend=str(case["shadow_backend"]),
        sensitivity_mode="central_finite_difference",
        jacobian_norm=1.0,
        agreement_metric=0.0,
        extras={"corpus_version": load_manifest().get("corpus_version")},
    )
    bundle_path = OUT / "assurance_bundle.json"
    bundle_to_json(bundle, bundle_path)
    replay = replay_bundle(bundle_path, expected_spec_digest=bundle.specification_digest)
    corrupted = corrupt_bundle_action(bundle)
    corrupt_checks = run_machine_checks(corrupted)

    domain = CBF2DDomain()
    stage1 = demo_stage1_scenario()
    stage2 = demo_stage2_batch()
    metrics = compute_cbf_metrics(stage2)

    payload = {
        "corpus_version": load_manifest().get("corpus_version"),
        "assurance_replay": replay,
        "corrupt_checks": corrupt_checks,
        "evidence_level": str(bundle.evidence_level),
        "cbf_domain": domain.as_dict(),
        "cbf_stage1": stage1.as_dict(),
        "cbf_stage2": [r.as_dict() for r in stage2],
        "cbf_metrics": metrics.as_dict(),
    }
    (OUT / "assurance_and_cbf.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"bundle_level={bundle.evidence_level} replay_ok={replay['all_passed']} "
        f"cbf_intervention_freq={metrics.intervention_frequency}"
    )


if __name__ == "__main__":
    main()
