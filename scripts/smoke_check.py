#!/usr/bin/env python3
"""Layer B: run public and optional vendor smoke checks; write output/smoke_check.{json,md}."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from conicshield.artifacts.validator import validate_run_bundle


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _public_cvxpy_solver_smoke() -> dict[str, Any]:
    """Tiny QP with CLARABEL if available, else SCS (vendor-independent)."""
    out: dict[str, Any] = {"ok": False}
    try:
        import cvxpy as cp

        x = cp.Variable(3)
        prob = cp.Problem(
            cp.Minimize(cp.sum_squares(x - np.array([0.2, 0.3, 0.5]))),
            [x >= 0, cp.sum(x) == 1.0],
        )
        solver = None
        name = None
        if hasattr(cp, "CLARABEL"):
            solver = cp.CLARABEL
            name = "CLARABEL"
        elif hasattr(cp, "SCS"):
            solver = cp.SCS
            name = "SCS"
        else:
            out["error"] = "No CLARABEL or SCS solver in cvxpy"
            return out
        prob.solve(solver=solver, verbose=False)
        st = str(prob.status)
        ok_status = st.lower() in ("optimal", "optimal_inaccurate") or st == str(getattr(cp, "OPTIMAL", "optimal"))
        if not ok_status:
            out["status"] = st
            out["solver"] = name
            return out
        out["ok"] = True
        out["solver"] = name
        out["status"] = str(prob.status)
        out["objective"] = float(prob.value) if prob.value is not None else None
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:400]
    return out


def _artifact_bundle_smoke(root: Path) -> dict[str, Any]:
    ref = root / "tests" / "fixtures" / "parity_reference"
    out: dict[str, Any] = {"path": str(ref), "ok": False}
    try:
        validate_run_bundle(ref)
        out["ok"] = True
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:500]
    return out


def _audit_smoke(root: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": False}
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "conicshield.governance.audit_cli", "--strict"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        out["returncode"] = proc.returncode
        out["ok"] = proc.returncode == 0
        if not out["ok"]:
            out["stderr_tail"] = (proc.stderr or "")[-600:]
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:400]
    return out


def _vendor_smoke(skip_native: bool) -> dict[str, Any]:
    from conicshield.core.solver_smoke_cli import run_solver_smoke_dict

    return run_solver_smoke_dict(skip_native=skip_native)


def _collect(root: Path, *, vendor: bool, skip_native: bool) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    steps.append({"name": "public_cvxpy_qp", "result": _public_cvxpy_solver_smoke()})
    steps.append({"name": "artifact_bundle_parity_reference", "result": _artifact_bundle_smoke(root)})
    steps.append({"name": "governance_audit_strict", "result": _audit_smoke(root)})

    vendor_block: dict[str, Any] | None = None
    if vendor:
        vendor_block = _vendor_smoke(skip_native=skip_native)
        steps.append({"name": "vendor_solver_smoke", "result": vendor_block})

    ok_public = steps[0]["result"].get("ok") and steps[1]["result"].get("ok") and steps[2]["result"].get("ok")
    ok_vendor = True
    if vendor_block is not None:
        ok_vendor = not vendor_block.get("errors")

    return {
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ok" if (ok_public and ok_vendor) else "fail",
        "public_ok": ok_public,
        "vendor_ok": ok_vendor if vendor else None,
        "vendor_included": vendor,
        "steps": steps,
    }


def _write_md(path: Path, data: dict[str, Any]) -> None:
    lines = [
        "# Smoke check",
        "",
        f"Generated: {data.get('generated_at_utc', '')}",
        f"**Overall status:** {data.get('status')}",
        "",
        "## Steps",
        "",
    ]
    for s in data.get("steps", []):
        lines.append(f"### {s.get('name')}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(s.get("result"), indent=2))
        lines.append("```")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Write smoke_check artifacts under output/.")
    p.add_argument("--out-dir", type=Path, default=None)
    p.add_argument("--vendor", action="store_true", help="Include vendor Moreau smoke (requires license).")
    p.add_argument("--skip-native", action="store_true", help="With --vendor: only CVXPY reference arm.")
    args = p.parse_args()
    root = _repo_root()
    out_dir = args.out_dir or (root / "output")
    out_dir.mkdir(parents=True, exist_ok=True)

    data = _collect(root, vendor=args.vendor, skip_native=args.skip_native)
    (out_dir / "smoke_check.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    _write_md(out_dir / "smoke_check.md", data)
    print(out_dir / "smoke_check.json")
    return 0 if data.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
