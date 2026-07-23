#!/usr/bin/env python3
"""Clean-environment AssuranceBundle reproduction soak (R4).

Rebuilds an AssuranceBundle from committed corpus inputs and verifies
hashes / machine checks. Intended to run in a fresh venv:

  python -m venv .venv-research-soak
  .venv-research-soak/Scripts/python -m pip install -e ".[dev]"   # Windows
  .venv-research-soak/Scripts/python experiments/research_wave5/run_clean_env_soak.py

Or on Unix:
  python -m venv .venv-research-soak
  .venv-research-soak/bin/python -m pip install -e ".[dev]"
  .venv-research-soak/bin/python experiments/research_wave5/run_clean_env_soak.py

This script does not claim R4 production promotion; it exercises the
independent reproduction path required by the gate.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "research" / "wave5" / "clean_env_soak"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> int:
    from conicshield.experimental.assurance.builder import build_assurance_bundle
    from conicshield.experimental.assurance.checks import run_machine_checks
    from conicshield.experimental.assurance.migration import normalize_bundle_dict
    from conicshield.experimental.assurance.replay import bundle_from_dict, bundle_to_json, replay_bundle
    from conicshield.experimental.corpus.generate import load_all_scenarios, load_manifest
    from conicshield.experimental.corpus.paths import CORPUS_VERSION
    from conicshield.experimental.provenance import (
        audit_provenance_completeness,
        begin_experiment_provenance,
        finalize_experiment_provenance,
    )
    from conicshield.experimental.solver_assurance.disagreement import compare_projections
    from conicshield.experimental.solver_assurance.shadow_harness import run_shadow_harness

    OUT.mkdir(parents=True, exist_ok=True)
    prov = begin_experiment_provenance(
        scenario_corpus_version=CORPUS_VERSION,
        backend="cvxpy_clarabel",
        exact_command="python experiments/research_wave5/run_clean_env_soak.py",
        random_seeds={"soak": 0},
        solver_distribution="cvxpy",
        tolerances={"residual": 1e-8},
    )

    manifest = load_manifest()
    if manifest.get("corpus_version") != CORPUS_VERSION:
        print("corpus version mismatch", file=sys.stderr)
        return 2

    summary = run_shadow_harness(
        budget_fraction=1.0,
        exact_command="python experiments/research_wave5/run_clean_env_soak.py",
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
        extras={"corpus_version": CORPUS_VERSION, "soak": True},
    )
    bundle_path = OUT / "assurance_bundle.json"
    bundle_to_json(bundle, bundle_path)
    sealed = bundle.corrected_action_digest()
    replay = replay_bundle(bundle_path, expected_spec_digest=bundle.specification_digest)
    checks = run_machine_checks(bundle, sealed_corrected_action_digest=sealed)

    # Fixture migration: v0_legacy -> v0
    legacy = {
        "schema_id": "research.assurance_bundle.v0_legacy",
        "action": bundle.as_dict()["corrected_action"],
        "level": str(bundle.evidence_level),
        **{k: v for k, v in bundle.as_dict().items() if k not in {"corrected_action", "evidence_level", "schema_id"}},
    }
    migrated = normalize_bundle_dict(legacy)
    migrated_bundle = bundle_from_dict(migrated)
    migrated_checks = run_machine_checks(migrated_bundle)

    finalize_experiment_provenance(prov, artifact_paths=[bundle_path])
    audit = audit_provenance_completeness(prov)
    prov.to_json(OUT / "provenance.json")

    payload = {
        "corpus_version": CORPUS_VERSION,
        "bundle_sha256": _sha256(bundle_path),
        "sealed_corrected_action_digest": sealed,
        "replay": replay,
        "checks": checks,
        "migration_fixture": {
            "from": "research.assurance_bundle.v0_legacy",
            "to": migrated.get("schema_id"),
            "checks": migrated_checks,
            "all_passed": all(migrated_checks.values()),
        },
        "provenance_audit": audit,
        "r4_gate_note": (
            "Clean-env soak path exercised. Prefer experiments/research_wave6/run_platform_soak.py "
            "for OS/Python/CPU/GPU/solver/commit/dirty/artifact-hash matrix recording and multi-host "
            "aggregation. R4 production/public flagship promotion still requires broader independent "
            "soak evidence and must not overclaim universal safety."
        ),
        "all_passed": bool(replay.get("all_passed")) and all(checks.values()) and audit["complete"],
    }
    out_path = OUT / "clean_env_soak.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out_path} all_passed={payload['all_passed']}")
    return 0 if payload["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
