#!/usr/bin/env python3
"""Layer C: conic suite (Moreau vs CLARABEL/SCS) + minimal shield QP (CVXPY vs native); write JSON + MD."""

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


def _shield_spec() -> SafetySpec:
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


def _compare_shield_qp() -> dict[str, Any]:
    proposed = np.array([0.65, 0.2, 0.1, 0.05], dtype=np.float64)
    prev = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64)
    spec = _shield_spec()
    out: dict[str, Any] = {
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


def _run_conic_rows(*, profile: str) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    try:
        import cvxpy as cp
    except Exception as exc:
        return [], [f"cvxpy import: {exc}"]
    from conicshield.reference_correctness.conic_suite import moreau_installed, run_full_conic_suite

    if not moreau_installed(cp):
        return [], ["MOREAU backend not installed; skipping conic vs public solver suite"]
    rows = run_full_conic_suite(cp, profile=profile)
    for r in rows:
        if r.get("status") != "ok":
            errors.append(f"{r.get('case_id', '?')}: {r.get('error', r.get('status'))}")
    return rows, errors


def _write_md(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Reference correctness report",
        "",
        f"Generated: {payload.get('generated_at_utc', '')}",
        "",
        "## Conic suite (Moreau vs trusted public solver)",
        "",
        "Deltas are **Moreau vs CLARABEL** when CLARABEL is installed, otherwise **Moreau vs SCS**.",
        "",
        "| case_id | trusted | family | n | density | cond | status | primal_linf | obj_abs | obj_rel | iters T/M |",
        "|---------|---------|--------|---|---------|------|--------|-------------|---------|---------|-----------|",
    ]
    for r in payload.get("conic_rows", []):
        it_t = r.get("trusted_num_iters", "")
        it_m = r.get("moreau_num_iters", "")
        iters = f"{it_t}/{it_m}" if it_t != "" or it_m != "" else ""
        lines.append(
            f"| {r.get('case_id', '')} | {r.get('trusted_solver', '')} | {r.get('family', '')} | {r.get('n', '')} | "
            f"{r.get('density', '')} | {r.get('conditioning', '')} | {r.get('status', '')} | "
            f"{r.get('primal_linf_delta', '')} | {r.get('objective_abs_delta', '')} | "
            f"{r.get('objective_rel_delta', '')} | {iters} |"
        )
    if payload.get("conic_errors"):
        lines.extend(["", "### Conic errors", "", "\n".join(f"- {e}" for e in payload["conic_errors"])])

    sq = payload.get("shield_qp_minimal", {})
    lines.extend(
        [
            "",
            "## Shield QP minimal (CVXPY Moreau vs native)",
            "",
            f"**Status:** {sq.get('status', '')}",
        ]
    )
    if sq.get("deltas"):
        lines.extend(["", "| Metric | Value |", "|--------|-------|"])
        for k, v in sq["deltas"].items():
            lines.append(f"| {k} | {v} |")
    if sq.get("errors"):
        lines.extend(["", "```json", json.dumps(sq["errors"], indent=2), "```"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Write reference_correctness_summary under output/.")
    p.add_argument("--out-dir", type=Path, default=None)
    p.add_argument("--skip-conic", action="store_true", help="Only run shield QP minimal block.")
    p.add_argument("--skip-shield", action="store_true", help="Only run conic vs public solver suite.")
    p.add_argument(
        "--suite-profile",
        type=str,
        default="standard",
        choices=("smoke", "standard", "stress"),
        help="Conic-suite profile size.",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Fail when conic suite is skipped or shield status is partial/skipped.",
    )
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    out_dir = args.out_dir or (root / "output")
    out_dir.mkdir(parents=True, exist_ok=True)

    conic_rows: list[dict[str, Any]] = []
    conic_errors: list[str] = []
    if not args.skip_conic:
        conic_rows, conic_errors = _run_conic_rows(profile=args.suite_profile)

    shield: dict[str, Any] = {}
    if not args.skip_shield:
        shield = _compare_shield_qp()

    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "conic_rows": conic_rows,
        "conic_errors": conic_errors,
        "shield_qp_minimal": shield,
        "suite_profile": args.suite_profile,
        "strict_mode": bool(args.strict),
    }
    if args.skip_conic:
        conic_ok = True
    elif conic_errors and len(conic_errors) == 1 and "MOREAU backend not installed" in conic_errors[0]:
        conic_ok = True
        payload["conic_skipped_reason"] = conic_errors[0]
    else:
        conic_ok = not conic_errors and all(r.get("status") == "ok" for r in conic_rows)
    shield_ok = True
    if not args.skip_shield:
        shield_ok = shield.get("status") in ("ok", "skipped", "partial") and not any(
            e.get("arm") == "cvxpy_moreau" for e in shield.get("errors", [])
        )
        if shield.get("status") == "fail":
            shield_ok = False
    if args.strict:
        if payload.get("conic_skipped_reason"):
            conic_ok = False
        if not args.skip_shield and shield.get("status") != "ok":
            shield_ok = False
    payload["summary_status"] = "ok" if (conic_ok and shield_ok) else "fail"

    (out_dir / "reference_correctness_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_md(out_dir / "reference_correctness_table.md", payload)
    _write_md(out_dir / "reference_correctness_report.md", payload)
    print(out_dir / "reference_correctness_summary.json")
    return 0 if payload["summary_status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
