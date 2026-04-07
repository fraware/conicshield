from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from conicshield.adapters.inter_sim_rl.shield import InterSimConicShield
from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions
from conicshield.core.solver_factory import Backend
from conicshield.parity.gates import enforce_default_parity_gates
from conicshield.parity.replay import compare_against_reference


def _load_json(path: str | Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(Path(path).read_text(encoding="utf-8")))


def _extract_native_arm(config: dict[str, Any]) -> dict[str, Any]:
    for arm in config.get("arms", []):
        if arm["label"] == "shielded-native-moreau":
            return cast(dict[str, Any], arm)
    raise ValueError("No 'shielded-native-moreau' arm found in config.json")


def build_native_candidate_from_config(config: dict[str, Any]) -> InterSimConicShield:
    arm = _extract_native_arm(config)
    solver = dict(arm.get("solver", {}))
    return InterSimConicShield(
        backend=Backend.NATIVE_MOREAU,
        native_options=NativeMoreauCompiledOptions(
            device=solver.get("device") or "cpu",
            auto_tune=False,
            verbose=False,
            persist_warm_start=bool(arm.get("warm_start", True)),
            max_iter=solver.get("max_iter") or 200,
            time_limit=(float(solver["time_limit_sec"]) if solver.get("time_limit_sec") is not None else float("inf")),
            policy_weight=(float(solver["policy_weight"]) if solver.get("policy_weight") is not None else 1.0),
            reference_weight=(float(solver["reference_weight"]) if solver.get("reference_weight") is not None else 0.0),
        ),
        use_geometry_prior=bool(arm.get("use_geometry_prior", True)),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run native Moreau parity check.")
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--reference-arm-label", type=str, default="shielded-rules-plus-geometry")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    config = _load_json(args.reference_dir / "config.json")
    candidate = build_native_candidate_from_config(config)

    step_results, summary = compare_against_reference(
        episodes_jsonl=args.reference_dir / "episodes.jsonl",
        candidate_shield=candidate,
        reference_arm_label=args.reference_arm_label,
    )
    (args.out_dir / "parity_summary.json").write_text(json.dumps(summary.as_dict(), indent=2), encoding="utf-8")
    with (args.out_dir / "parity_steps.jsonl").open("w", encoding="utf-8") as fh:
        for row in step_results:
            fh.write(json.dumps(row.as_dict(), sort_keys=True))
            fh.write("\n")
    enforce_default_parity_gates(summary)
    print(args.out_dir / "parity_summary.json")


if __name__ == "__main__":
    main()
