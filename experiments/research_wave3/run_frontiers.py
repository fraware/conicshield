#!/usr/bin/env python3
"""Wave 3: frontier sweeps + local-global consistency."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from conicshield.experimental.corpus.generate import load_all_scenarios, load_manifest
from conicshield.experimental.frontiers.local_global import run_local_global_consistency
from conicshield.experimental.frontiers.sweeps import run_frontier_sweep, run_frontier_sweep_scaffold
from conicshield.specs.schema import SafetySpec

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "research" / "wave3"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scenario = load_all_scenarios()[0]
    spec = SafetySpec.model_validate(scenario["spec"])
    proposed = np.asarray(scenario["proposed_action"], dtype=np.float64)
    previous = np.asarray(scenario["previous_action"], dtype=np.float64)
    reference = np.asarray(scenario["reference_action"], dtype=np.float64)

    # CI-friendly small sweep
    small = run_frontier_sweep_scaffold(
        spec=spec,
        proposed_action=proposed,
        previous_action=previous,
        reference_action=reference,
    )
    (OUT / "frontier_ci_small.json").write_text(
        json.dumps(small.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # Broader sweep (still bounded for local runs)
    full = run_frontier_sweep(
        spec=spec,
        proposed_action=proposed,
        previous_action=previous,
        reference_action=reference,
        grid={
            "policy_weight": [1.0, 2.0],
            "reference_weight": [0.0, 0.5],
            "rate_limit": [0.5, 1.0],
            "hazard_multiplier": [1.0],
            "geometry_prior_weight": [0.0],
            "bound_margins": [0.0],
            "robustness_margins": [0.0, 0.05],
            "fallback_thresholds": [0.5],
        },
    )
    (OUT / "frontier.json").write_text(json.dumps(full.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    base = {"policy_weight": 1.0, "rate_limit": 1.0, "reference_weight": 0.0}
    neighbors = [
        {"policy_weight": 1.1, "rate_limit": 1.0},
        {"policy_weight": 1.0, "rate_limit": 0.8},
    ]
    lg = run_local_global_consistency(
        spec=spec,
        proposed_action=proposed,
        previous_action=previous,
        reference_action=reference,
        base_params=base,
        neighbor_params=neighbors,
    )
    (OUT / "local_global.json").write_text(json.dumps(lg.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"corpus={load_manifest().get('corpus_version')} "
        f"pareto={len(full.pareto_indices)}/{len(full.points)} "
        f"local_global_flags={len(lg.flags)}"
    )


if __name__ == "__main__":
    main()
