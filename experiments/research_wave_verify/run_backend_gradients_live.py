"""Live WSL verification for exact + smoothed backend gradients.

Writes JSON artifacts under output/research/. Run with the Moreau WSL venv:

  .venv-wsl-moreau/bin/python experiments/research_wave_verify/run_backend_gradients_live.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conicshield.experimental.corpus.generate import load_all_scenarios
from conicshield.experimental.gradients.exact_backend import (
    _probe_vendor_compiled_backward,
    exact_backend_gradient,
)
from conicshield.experimental.gradients.smoothed_backend import smoothed_backend_gradient
from conicshield.specs.schema import SafetySpec

OUT = ROOT / "output" / "research" / "backend_gradients_live"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    caps = _probe_vendor_compiled_backward()
    (OUT / "probe_capabilities.json").write_text(
        json.dumps(caps, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not caps.get("vendor_compiled_backward_api"):
        print("FAIL: CompiledSolver.backward unavailable", caps)
        sys.exit(2)

    scenario = next(s for s in load_all_scenarios() if s["family"] == "interior_feasible")
    spec = SafetySpec.model_validate(scenario["spec"])
    u = np.asarray(scenario["proposed_action"], dtype=np.float64)
    prev = np.asarray(scenario["previous_action"], dtype=np.float64)
    ref = np.asarray(scenario["reference_action"], dtype=np.float64)

    exact = exact_backend_gradient(
        spec=spec,
        proposed_action=u,
        previous_action=prev,
        reference_action=ref,
        compare_central_fd=True,
    )
    (OUT / "exact_backend_gradient.json").write_text(
        json.dumps(exact.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    smoothed = smoothed_backend_gradient(
        spec=spec,
        proposed_action=u,
        previous_action=prev,
        reference_action=ref,
        smoothing_parameter=1e-2,
        compare_central_fd=True,
        compare_exact_backend=True,
    )
    (OUT / "smoothed_backend_gradient.json").write_text(
        json.dumps(smoothed.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    summary = {
        "scenario_id": scenario["scenario_id"],
        "exact_available": exact.available,
        "exact_status": str(exact.status),
        "exact_fd_agree": exact.agreement_vs_central_fd,
        "smoothed_available": smoothed.available,
        "smoothed_status": str(smoothed.status),
        "smoothed_epsilon": smoothed.smoothing_parameter,
        "smoothed_fd_agree": smoothed.agreement_vs_smoothed_central_fd,
        "smoothed_vs_exact": smoothed.agreement_vs_exact_backend,
        "research_differentiation_surface": caps.get("research_differentiation_surface"),
        "production_differentiation_api": caps.get("differentiation_api"),
        "artifacts": {
            "probe": str(OUT / "probe_capabilities.json"),
            "exact": str(OUT / "exact_backend_gradient.json"),
            "smoothed": str(OUT / "smoothed_backend_gradient.json"),
        },
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not exact.available or not smoothed.available:
        sys.exit(1)


if __name__ == "__main__":
    main()
