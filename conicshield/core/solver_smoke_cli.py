"""Minimal reference + native solve smoke test (requires solver extras and license for ``solve``)."""

from __future__ import annotations

import argparse
import json
import sys
import time
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


def _minimal_spec() -> SafetySpec:
    return SafetySpec(
        spec_id="smoke/minimal",
        version="0.1.0",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[0, 1, 2, 3]),
            BoxConstraint(lower=[0.0] * 4, upper=[1.0] * 4),
            RateConstraint(max_delta=[0.9] * 4),
        ],
    )


def _run_arm(
    backend: Backend,
    proposed: np.ndarray,
    prev: np.ndarray | None,
) -> dict[str, Any]:
    spec = _minimal_spec()
    if backend == Backend.CVXPY_MOREAU:
        proj = create_projector(
            spec=spec,
            backend=backend,
            cvxpy_options=SolverOptions(device="cpu", max_iter=500, verbose=False),
        )
    else:
        proj = create_projector(
            spec=spec,
            backend=backend,
            native_options=NativeMoreauCompiledOptions(device="cpu", max_iter=500, verbose=False),
        )
    result = proj.project(
        proposed,
        prev,
        policy_weight=1.0,
        reference_weight=0.0,
    )
    out = result.as_dict()
    out["sum_corrected"] = float(np.sum(result.corrected_action))
    return out


def run_solver_smoke_dict(
    *,
    skip_native: bool = False,
) -> dict[str, Any]:
    """Return smoke report dict (reference + optional native single solves)."""
    proposed = np.array([0.7, 0.2, 0.05, 0.05], dtype=np.float64)
    prev = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64)

    report: dict[str, Any] = {"reference": None, "native": None, "native_warm_sequence": None, "errors": []}

    try:
        report["reference"] = _run_arm(Backend.CVXPY_MOREAU, proposed, prev)
    except Exception as exc:
        report["errors"].append({"arm": "reference", "error": str(exc)})

    if not skip_native:
        try:
            report["native"] = _run_arm(Backend.NATIVE_MOREAU, proposed, prev)
        except Exception as exc:
            report["errors"].append({"arm": "native", "error": str(exc)})

        try:
            report["native_warm_sequence"] = run_native_warm_smoke_dict()
        except Exception as exc:
            report["errors"].append({"arm": "native_warm_sequence", "error": str(exc)})

    return report


def run_native_warm_smoke_dict() -> dict[str, Any]:
    """Two solves on the same native projector with persist_warm_start (Layer B warm-start smoke)."""
    spec = _minimal_spec()
    proj = create_projector(
        spec=spec,
        backend=Backend.NATIVE_MOREAU,
        native_options=NativeMoreauCompiledOptions(
            device="cpu",
            max_iter=500,
            verbose=False,
            persist_warm_start=True,
        ),
    )
    p1 = np.array([0.7, 0.2, 0.05, 0.05], dtype=np.float64)
    prev = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64)
    p2 = np.array([0.5, 0.3, 0.1, 0.1], dtype=np.float64)

    t0 = time.perf_counter()
    r1 = proj.project(p1, prev, policy_weight=1.0, reference_weight=0.0)
    t1 = time.perf_counter()
    r2 = proj.project(p2, r1.corrected_action, policy_weight=1.0, reference_weight=0.0)
    t2 = time.perf_counter()

    return {
        "first_solve_sec": round(t1 - t0, 6),
        "second_solve_sec": round(t2 - t1, 6),
        "first_warm_started_flag": r1.warm_started,
        "second_warm_started_flag": r2.warm_started,
        "sum_corrected_first": float(np.sum(r1.corrected_action)),
        "sum_corrected_second": float(np.sum(r2.corrected_action)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ConicShield solver smoke (CVXPY/Moreau + native).")
    parser.add_argument("--skip-native", action="store_true", help="Only run CVXPY reference path.")
    args = parser.parse_args()

    report = run_solver_smoke_dict(skip_native=args.skip_native)
    print(json.dumps(report, indent=2))
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
