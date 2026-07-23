#!/usr/bin/env python3
"""Mandatory known-feasible native solve + known-infeasible/failure-policy check.

Used by vendor CI before/around the pytest suite so the job cannot pass with
zero native solves (CS-SOLVER-003).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _vendor_required() -> bool:
    return os.environ.get("CONICSHIELD_VENDOR_REQUIRED", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _require_moreau() -> None:
    try:
        import moreau  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        msg = f"moreau import failed: {exc}"
        if _vendor_required():
            raise SystemExit(f"CONICSHIELD_VENDOR_REQUIRED=1 but {msg}") from exc
        raise SystemExit(f"SKIP: {msg}") from exc
    try:
        import cvxpy as cp
    except Exception as exc:  # noqa: BLE001
        msg = f"cvxpy import failed: {exc}"
        if _vendor_required():
            raise SystemExit(f"CONICSHIELD_VENDOR_REQUIRED=1 but {msg}") from exc
        raise SystemExit(f"SKIP: {msg}") from exc
    if not hasattr(cp, "MOREAU"):
        msg = "cp.MOREAU not registered"
        if _vendor_required():
            raise SystemExit(f"CONICSHIELD_VENDOR_REQUIRED=1 but {msg}")
        raise SystemExit(f"SKIP: {msg}")


def _known_feasible_native() -> dict[str, Any]:
    from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions, NativeMoreauCompiledProjector
    from conicshield.specs.schema import BoxConstraint, SafetySpec, SimplexConstraint

    spec = SafetySpec(
        spec_id="vendor-ci/known-feasible",
        version="0.1.0",
        action_dim=2,
        constraints=[
            SimplexConstraint(total=1.0),
            BoxConstraint(lower=[0.0, 0.0], upper=[1.0, 1.0]),
        ],
    )
    proj = NativeMoreauCompiledProjector(
        spec=spec,
        options=NativeMoreauCompiledOptions(device="cpu", max_iter=400, verbose=False),
    )
    proposed = np.array([0.8, 0.2], dtype=np.float64)
    result = proj.project(proposed)
    ok = (
        result.corrected_action is not None
        and np.all(np.isfinite(result.corrected_action))
        and abs(float(np.sum(result.corrected_action)) - 1.0) <= 1e-5
        and (result.verification is None or result.verification.passed)
    )
    return {
        "ok": bool(ok),
        "solver_status": getattr(result, "solver_status", None),
        "release_decision": str(getattr(result, "release_decision", None)),
        "sum_corrected": float(np.sum(result.corrected_action)) if result.corrected_action is not None else None,
        "native_solve_count": 1 if ok else 0,
    }


def _known_infeasible_or_failure_policy() -> dict[str, Any]:
    """Exercise fail-safe / rejection path for nonfinite / infeasible primary solves."""
    from conicshield.specs.schema import BoxConstraint, FailSafePolicy, SafetySpec, SimplexConstraint
    from conicshield.specs.shield_qp import parse_safety_spec_for_shield
    from conicshield.verification.fallback import (
        FallbackConfig,
        SolveAttemptResult,
        run_verified_release_pipeline,
    )
    from conicshield.verification.feasibility import VerificationReleaseError
    from conicshield.verification.release_policy import ReleaseDecision

    spec = SafetySpec(
        spec_id="vendor-ci/failure-policy",
        version="0.1.0",
        action_dim=2,
        constraints=[
            SimplexConstraint(total=1.0),
            BoxConstraint(lower=[0.0, 0.0], upper=[1.0, 1.0]),
        ],
        fail_safe_policy=FailSafePolicy.UNIFORM_ADMISSIBLE,
    )
    data = parse_safety_spec_for_shield(spec)
    proposed = np.array([0.9, 0.1], dtype=np.float64)

    def _primary(*, warm_start: bool) -> SolveAttemptResult:
        del warm_start
        return SolveAttemptResult(
            candidate=np.array([np.nan, 0.0], dtype=np.float64),
            raw_status="infeasible",
            warm_started=False,
            kind="primary",
        )

    try:
        outcome = run_verified_release_pipeline(
            data=data,
            proposed_action=proposed,
            previous_action=None,
            reference_action=None,
            policy_weight=1.0,
            reference_weight=0.0,
            primary_solve=_primary,
            config=FallbackConfig(
                enable_cold_retry=False,
                max_attempts=2,
                public_fallback=None,
                fail_safe_policy=FailSafePolicy.UNIFORM_ADMISSIBLE,
            ),
        )
        ok = outcome.release_decision in {
            ReleaseDecision.ACCEPTED_FAIL_SAFE,
            ReleaseDecision.REJECTED_NONFINITE,
            ReleaseDecision.REJECTED_STATUS,
            ReleaseDecision.REJECTED_BACKEND_ERROR,
        } or (
            outcome.candidate is not None
            and np.all(np.isfinite(outcome.candidate))
            and abs(float(np.sum(outcome.candidate)) - 1.0) <= 1e-5
        )
        return {
            "ok": bool(ok),
            "mode": "fail_safe_pipeline",
            "release_decision": str(outcome.release_decision),
        }
    except VerificationReleaseError as exc:
        return {"ok": True, "mode": "verification_release_error", "error": str(exc)[:200]}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Write evidence JSON for assert_vendor_ci_evidence.py.",
    )
    args = p.parse_args()

    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    _require_moreau()
    feasible = _known_feasible_native()
    failure = _known_infeasible_or_failure_policy()

    payload = {
        "schema_version": "conicshield_vendor_mandatory_solves/v1",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "known_feasible_ok": bool(feasible.get("ok")),
        "known_infeasible_or_failure_policy_ok": bool(failure.get("ok")),
        "native_solve_count": int(feasible.get("native_solve_count") or 0),
        "known_feasible": feasible,
        "failure_policy": failure,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(args.out)

    if not payload["known_feasible_ok"]:
        print("ERROR: known-feasible native solve failed", file=sys.stderr)
        return 1
    if not payload["known_infeasible_or_failure_policy_ok"]:
        print("ERROR: known-infeasible / failure-policy check failed", file=sys.stderr)
        return 1
    if payload["native_solve_count"] <= 0:
        print("ERROR: native_solve_count is zero", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
