#!/usr/bin/env python3
"""Layer C (minimal): compare CVXPY+MOREAU vs native on the same shield QP spec; write JSON + MD."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions
from conicshield.core.solver_factory import Backend, create_projector
from conicshield.specs.compiler import SolverOptions
from conicshield.specs.schema import (
    BoxConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)


def _spec() -> SafetySpec:
    return SafetySpec(
        spec_id="refcheck/minimal",
        version="0.1.0",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[0, 1, 2, 3]),
            BoxConstraint(lower=[0.0] * 4, upper=[1.0] * 4),
            RateConstraint(max_delta=[0.9] * 4),
        ],
    )


def _compare() -> dict[str, Any]:
    proposed = np.array([0.65, 0.2, 0.1, 0.05], dtype=np.float64)
    prev = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64)
    spec = _spec()
    out: dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "shield_qp_minimal",
        "reference": None,
        "native": None,
        "deltas": None,
        "status": "skipped",
        "errors": [],
    }
    try:
        ref_proj = create_projector(
            spec=spec,
            backend=Backend.CVXPY_MOREAU,
            cvxpy_options=SolverOptions(device="cpu", max_iter=800, verbose=False),
        )
        r_ref = ref_proj.project(proposed, prev, policy_weight=1.0, reference_weight=0.0)
        out["reference"] = {
            "corrected": r_ref.corrected_action.tolist(),
            "intervention_norm": r_ref.intervention_norm,
        }
    except Exception as exc:
        out["errors"].append({"arm": "cvxpy_moreau", "error": str(exc)})
        return out

    try:
        nat_proj = create_projector(
            spec=spec,
            backend=Backend.NATIVE_MOREAU,
            native_options=NativeMoreauCompiledOptions(device="cpu", max_iter=800, verbose=False),
        )
        r_nat = nat_proj.project(proposed, prev, policy_weight=1.0, reference_weight=0.0)
        out["native"] = {
            "corrected": r_nat.corrected_action.tolist(),
            "intervention_norm": r_nat.intervention_norm,
        }
    except Exception as exc:
        out["errors"].append({"arm": "native", "error": str(exc)})
        out["status"] = "partial"
        return out

    a = np.asarray(r_ref.corrected_action, dtype=np.float64)
    b = np.asarray(r_nat.corrected_action, dtype=np.float64)
    linf = float(np.max(np.abs(a - b)))
    l2 = float(np.linalg.norm(a - b))
    out["deltas"] = {
        "linf": linf,
        "l2": l2,
        "intervention_norm_abs_diff": abs(float(r_ref.intervention_norm) - float(r_nat.intervention_norm)),
    }
    tol_linf = 1e-4
    tol_l2 = 1e-4
    out["tolerances"] = {"linf": tol_linf, "l2": tol_l2}
    out["within_tolerance"] = linf <= tol_linf and l2 <= tol_l2
    out["status"] = "ok" if out["within_tolerance"] else "fail"
    return out


def _write_md(path: Path, data: dict[str, Any]) -> None:
    lines = [
        "# Reference correctness (minimal shield QP)",
        "",
        f"Generated: {data.get('generated_at_utc', '')}",
        f"**Status:** {data.get('status')}",
        "",
        "| Metric | Value |",
        "|--------|-------|",
    ]
    if data.get("deltas"):
        for k, v in data["deltas"].items():
            lines.append(f"| {k} | {v} |")
    if data.get("errors"):
        lines.extend(["", "## Errors", "", "```json", json.dumps(data["errors"], indent=2), "```"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Write reference_correctness_summary under output/.")
    p.add_argument("--out-dir", type=Path, default=None)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    out_dir = args.out_dir or (root / "output")
    out_dir.mkdir(parents=True, exist_ok=True)
    data = _compare()
    (out_dir / "reference_correctness_summary.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    _write_md(out_dir / "reference_correctness_table.md", data)
    # Plan §21 deliverable name alias (same content as the table).
    _write_md(out_dir / "reference_correctness_report.md", data)
    print(out_dir / "reference_correctness_summary.json")
    if data.get("status") == "fail":
        return 1
    if any(e.get("arm") == "cvxpy_moreau" for e in data.get("errors", [])):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
