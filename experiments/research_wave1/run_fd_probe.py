#!/usr/bin/env python3
"""Wave 1 entry: finite-difference observatory probe on first corpus scenario."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from conicshield.experimental.corpus.generate import load_all_scenarios
from conicshield.experimental.gradients.observatory import observe_proposed_action_fd
from conicshield.experimental.provenance import begin_experiment_provenance, finalize_experiment_provenance
from conicshield.specs.schema import SafetySpec


def main() -> None:
    scenarios = load_all_scenarios()
    scenario = next(s for s in scenarios if s["family"] == "interior_feasible")
    spec = SafetySpec.model_validate(scenario["spec"])
    prov = begin_experiment_provenance(
        scenario_corpus_version=str(scenario.get("corpus_version", "unknown")),
        backend="cvxpy_clarabel",
        exact_command="python experiments/research_wave1/run_fd_probe.py",
        random_seeds={"fd": int(scenario["seed"])},
        tolerances={"h": 1e-5},
    )
    report = observe_proposed_action_fd(
        spec=spec,
        proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
        previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
        reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
        scenario_id=str(scenario["scenario_id"]),
    )
    out = Path("output/research/fd_probe")
    out.mkdir(parents=True, exist_ok=True)
    path = out / "fd_report.json"
    path.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    finalize_experiment_provenance(prov, artifact_paths=[path]).to_json(out / "provenance.json")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
