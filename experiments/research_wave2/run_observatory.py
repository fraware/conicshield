#!/usr/bin/env python3
"""Wave 2: Safety-Gradient Observatory over active-set transition corpus."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from conicshield.experimental.corpus.generate import load_all_scenarios, load_manifest
from conicshield.experimental.corpus.paths import RESEARCH_ROOT
from conicshield.experimental.gradients.dual_pressure import correlate_dual_pressure, normalize_dual_pressure
from conicshield.experimental.gradients.observatory import (
    observe_proposed_action_fd,
    render_observatory_report_markdown,
)
from conicshield.specs.schema import SafetySpec

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "research" / "wave2" / "observatory"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    corpus_version = str(manifest.get("corpus_version"))
    reports = []
    pressures = []
    interventions = []
    transitions = []
    for scenario in load_all_scenarios():
        if scenario["family"] != "active_set_transition_neighborhoods":
            continue
        spec = SafetySpec.model_validate(scenario["spec"])
        report = observe_proposed_action_fd(
            spec=spec,
            proposed_action=np.asarray(scenario["proposed_action"], dtype=np.float64),
            previous_action=np.asarray(scenario["previous_action"], dtype=np.float64),
            reference_action=np.asarray(scenario["reference_action"], dtype=np.float64),
            scenario_id=str(scenario["scenario_id"]),
            corpus_version=corpus_version,
        )
        reports.append(report)
        # Duals often unavailable from public CVXPY path; use residual proxy pressure for correlation scaffold
        central = report.metrics[0]
        pressures.append(float(central.jacobian_norm))
        interventions.append(float(np.linalg.norm(np.asarray(scenario["proposed_action"], dtype=np.float64))))
        side = (scenario.get("extras") or {}).get("side", "")
        transitions.append(1.0 if side in {"at", "drop23", "corner"} else 0.0)

    dual_study = correlate_dual_pressure(
        max_abs_normalized_pressure=np.asarray(pressures, dtype=np.float64),
        intervention_size=np.asarray(interventions, dtype=np.float64),
        active_set_transition=np.asarray(transitions, dtype=np.float64),
    )
    # Keep dual normalizer exercised
    if pressures:
        normalize_dual_pressure(
            constraint_ids=tuple(f"proxy{i}" for i in range(min(3, len(pressures)))),
            dual_values=np.asarray(pressures[:3], dtype=np.float64),
        )

    payload = {
        "corpus_version": corpus_version,
        "reports": [r.as_dict() for r in reports],
        "dual_pressure_correlations": dual_study.as_dict(),
    }
    (OUT / "observatory.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    template = RESEARCH_ROOT / "reports" / "templates" / "GRADIENT_OBSERVATORY_REPORT.md"
    md = render_observatory_report_markdown(reports, template_path=template)
    (OUT / "GRADIENT_OBSERVATORY_REPORT.md").write_text(md, encoding="utf-8")
    print(f"observatory scenarios={len(reports)} wrote {OUT}")


if __name__ == "__main__":
    main()
