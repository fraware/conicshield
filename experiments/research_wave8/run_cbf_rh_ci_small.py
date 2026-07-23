"""Wave 8 CI-small: experimental CBF short-horizon RH + Track 1 probe attestation."""

from __future__ import annotations

import json
from pathlib import Path

from conicshield.experimental.adapters.track1_probe import write_track1_probe_attestation
from conicshield.experimental.domains.cbf_rh import (
    RH_EXPERIMENT_VERSION,
    demo_rh_scenario,
    demo_rh_soc_robust,
    describe_rh_capability,
)
from conicshield.experimental.domains.stage4_gate import evaluate_stage4_gate
from conicshield.experimental.training.r6_decision_scaffold import write_r6_decision_scaffold


def main() -> None:
    out = Path("output/research/wave8")
    out.mkdir(parents=True, exist_ok=True)

    gate = evaluate_stage4_gate(evidence_dir=out / "stage4_gate")
    gate_d = gate.as_dict()
    (out / "stage4_gate_summary.json").write_text(
        json.dumps(gate_d, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    rh = demo_rh_scenario(require_gate=True)
    (out / "cbf_rh_ci_small.json").write_text(
        json.dumps(rh.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    rh_r = demo_rh_soc_robust(require_gate=True)
    (out / "cbf_rh_soc_robust_ci_small.json").write_text(
        json.dumps(rh_r.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "cbf_rh_capability.json").write_text(
        json.dumps(describe_rh_capability(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    write_track1_probe_attestation(path=out / "track1_probe_attestation.json")
    write_r6_decision_scaffold(path=out / "R6_DECISION_REPORT_SCAFFOLD.json")

    summary = {
        "wave": 8,
        "rh_experiment_version": RH_EXPERIMENT_VERSION,
        "stage4_status": gate_d["stage4_status"],
        "rh_ran": rh.ran,
        "rh_soc_ran": rh_r.ran,
        "rh_mpc_implemented": gate_d["rh_mpc_implemented"],
        "experimental_rh_implemented": gate_d["experimental_rh_implemented"],
    }
    (out / "wave8_ci_small_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"wave8 ci-small stage4={gate_d['stage4_status']} "
        f"rh_ran={rh.ran} version={RH_EXPERIMENT_VERSION}"
    )


if __name__ == "__main__":
    main()
