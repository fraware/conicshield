#!/usr/bin/env python3
"""Heterogeneous batch vs sequential parity evidence runner.

Writes a decision-grade evidence artifact under ``docs/stabilization/`` or
``benchmarks/reports/``. Never marks PASS without real Moreau solves.

Status values:
  - PASS: sequential vs batch corrected actions match within tolerance
  - FAIL: Moreau available but mismatch / solve error
  - NOT_RUN: Moreau / license / OS unavailable (gate remains blocked)
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _blocked(reason: str) -> dict[str, Any]:
    return {
        "schema_version": "conicshield_heterogeneous_batch_parity/v1",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "NOT_RUN",
        "blocked_reason": reason,
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "gate_claim": "Heterogeneous batch parity remains BLOCKED",
    }


def _run_parity(*, rtol: float, atol: float) -> dict[str, Any]:
    from conicshield.core.moreau_batched import NativeMoreauCompiledBatchProjector
    from conicshield.core.moreau_compiled import (
        NativeMoreauCompiledOptions,
        NativeMoreauCompiledProjector,
    )
    from conicshield.specs.schema import (
        BoxConstraint,
        RateConstraint,
        SafetySpec,
        SimplexConstraint,
        TurnFeasibilityConstraint,
    )

    spec = SafetySpec(
        spec_id="hetero-batch-parity-evidence",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[0, 1, 2, 3]),
            BoxConstraint(lower=[0.0] * 4, upper=[1.0] * 4),
            RateConstraint(max_delta=[0.8] * 4),
        ],
    )
    opts = NativeMoreauCompiledOptions(
        device="cpu",
        max_iter=800,
        verbose=False,
        persist_warm_start=False,
        use_compiled_solver=True,
    )
    proposals = np.array(
        [
            [0.85, 0.05, 0.05, 0.05],
            [0.2, 0.3, 0.25, 0.25],
            [0.4, 0.35, 0.15, 0.1],
            [0.1, 0.1, 0.1, 0.7],
        ],
        dtype=np.float64,
    )
    previous = np.array(
        [
            [0.25, 0.25, 0.25, 0.25],
            [0.1, 0.2, 0.3, 0.4],
            [0.4, 0.2, 0.2, 0.2],
            [0.3, 0.3, 0.2, 0.2],
        ],
        dtype=np.float64,
    )
    uppers = np.array(
        [
            [1.0, 1.0, 1.0, 1.0],
            [0.7, 1.0, 1.0, 1.0],
            [1.0, 0.6, 1.0, 1.0],
            [1.0, 1.0, 0.5, 1.0],
        ],
        dtype=np.float64,
    )
    row_ids = ["r0", "r1", "r2", "r3"]

    seq = NativeMoreauCompiledProjector(spec=spec, options=opts)
    bat = NativeMoreauCompiledBatchProjector(spec=spec, options=opts)

    seq_out: list[np.ndarray] = []
    seq_meta: list[dict[str, Any]] = []
    for i in range(proposals.shape[0]):
        row_spec = SafetySpec(
            spec_id=spec.spec_id,
            action_dim=4,
            constraints=[
                SimplexConstraint(total=1.0),
                TurnFeasibilityConstraint(allowed_actions=[0, 1, 2, 3]),
                BoxConstraint(lower=[0.0] * 4, upper=uppers[i].tolist()),
                RateConstraint(max_delta=[0.8] * 4),
            ],
        )
        seq.spec = row_spec
        result = seq.project(proposals[i], previous[i])
        seq_out.append(np.asarray(result.corrected_action, dtype=np.float64))
        seq_meta.append(
            {
                "row_id": row_ids[i],
                "solver_status": result.solver_status,
                "release_decision": str(result.release_decision),
                "verification_passed": None
                if result.verification is None
                else bool(result.verification.passed),
            }
        )

    batch_result = bat.project_batch(
        proposals,
        previous,
        uppers=uppers,
        row_ids=row_ids,
    )
    stacked = np.stack(seq_out, axis=0)
    batched = np.asarray(batch_result.corrected_actions, dtype=np.float64)
    abs_err = np.abs(batched - stacked)
    max_abs = float(np.max(abs_err))
    match = bool(np.allclose(batched, stacked, rtol=rtol, atol=atol))

    batch_meta = []
    for row in batch_result.rows:
        batch_meta.append(
            {
                "row_id": row.metadata.get("row_id"),
                "solver_status": row.solver_status,
                "release_decision": str(row.release_decision),
                "verification_passed": None
                if row.verification is None
                else bool(row.verification.passed),
            }
        )

    return {
        "schema_version": "conicshield_heterogeneous_batch_parity/v1",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "PASS" if match else "FAIL",
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "batch_size": int(proposals.shape[0]),
        "rtol": rtol,
        "atol": atol,
        "max_abs_error": max_abs,
        "sequential_rows": seq_meta,
        "batch_rows": batch_meta,
        "gate_claim": (
            "Heterogeneous batch parity PASS"
            if match
            else "Heterogeneous batch parity FAIL"
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="JSON evidence path (default: docs/stabilization/heterogeneous_batch_parity.json).",
    )
    p.add_argument("--rtol", type=float, default=1e-4)
    p.add_argument("--atol", type=float, default=1e-5)
    args = p.parse_args()

    repo = _repo_root()
    out = args.out or (repo / "docs" / "stabilization" / "heterogeneous_batch_parity.json")

    if sys.platform == "win32":
        payload = _blocked(
            "Native Windows cannot run licensed Moreau; use WSL2 with solver-moreau-cpu."
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": payload["status"], "blocked_reason": payload["blocked_reason"]}, indent=2))
        return 2

    try:
        import moreau
    except Exception as exc:  # noqa: BLE001
        payload = _blocked(f"moreau import failed: {type(exc).__name__}: {exc}")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": payload["status"], "blocked_reason": payload["blocked_reason"]}, indent=2))
        return 2

    if not hasattr(moreau, "CompiledSolver"):
        payload = _blocked("installed moreau lacks CompiledSolver (likely PyPI stub)")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": payload["status"], "blocked_reason": payload["blocked_reason"]}, indent=2))
        return 2

    try:
        payload = _run_parity(rtol=float(args.rtol), atol=float(args.atol))
    except RuntimeError as exc:
        msg = str(exc).lower()
        if "license" in msg or "key" in msg:
            payload = _blocked(f"Moreau license error: {exc}")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"status": payload["status"], "blocked_reason": payload["blocked_reason"]}, indent=2))
            return 2
        raise
    except Exception as exc:  # noqa: BLE001
        payload = {
            "schema_version": "conicshield_heterogeneous_batch_parity/v1",
            "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "gate_claim": "Heterogeneous batch parity FAIL",
        }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md = out.with_suffix(".md")
    md.write_text(
        "\n".join(
            [
                "# Heterogeneous batch parity evidence",
                "",
                f"- status: **{payload.get('status')}**",
                f"- generated_at_utc: `{payload.get('generated_at_utc')}`",
                f"- gate_claim: {payload.get('gate_claim')}",
                (
                    f"- blocked_reason: {payload.get('blocked_reason')}"
                    if payload.get("blocked_reason")
                    else f"- max_abs_error: {payload.get('max_abs_error')}"
                ),
                "",
                f"JSON: `{out.as_posix()}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload.get("status"),
                "gate_claim": payload.get("gate_claim"),
                "max_abs_error": payload.get("max_abs_error"),
                "blocked_reason": payload.get("blocked_reason"),
                "out": str(out),
            },
            indent=2,
        )
    )
    if payload.get("status") == "PASS":
        return 0
    if payload.get("status") == "NOT_RUN":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
