#!/usr/bin/env python3
"""One reference (CVXPY + Moreau) projection on the minimal supported spec.

Audience: integrator using the public reference stack.
Prerequisites: ``pip install -e ".[dev]"``; CVXPY and Moreau installed (see docs/DEVENV.md).
Proves: ``create_projector(..., Backend.CVXPY_MOREAU)`` returns a ``ProjectionResult`` with a
  simplex-feasible corrected action.
Does not prove: native compiled speed, batch throughput, or parity vs native without a parity run.
Expected: proposed/corrected vectors; solver_status line; sum(corrected) ~ 1.0 — or SKIP if stack missing.
"""

from __future__ import annotations

import numpy as np

from _common import configure_stdio, minimal_spec, section, skip

from conicshield.core.solver_factory import Backend, create_projector


def main() -> int:
    configure_stdio()

    section("Environment")
    try:
        import cvxpy  # noqa: F401
    except ImportError as exc:
        return skip("cvxpy not installed", detail=exc)
    try:
        import moreau  # noqa: F401
    except ImportError as exc:
        return skip("moreau not installed (reference path uses Moreau solver)", detail=exc)

    spec = minimal_spec()
    print("spec_id:", spec.spec_id, "action_dim:", spec.action_dim)

    section("project (CVXPY_MOREAU)")
    projector = create_projector(spec=spec, backend=Backend.CVXPY_MOREAU)
    prev = np.full(4, 0.25, dtype=np.float64)
    proposed = np.array([0.7, 0.1, 0.1, 0.1], dtype=np.float64)
    try:
        result = projector.project(proposed, prev)
    except Exception as exc:
        return skip("reference projection failed", detail=exc)

    print("proposed:", np.round(proposed, 4).tolist())
    print("corrected:", np.round(result.corrected_action, 4).tolist())
    print("solver_status:", result.solver_status)
    print("intervened:", result.intervened, "intervention_norm:", round(result.intervention_norm, 4))
    simplex_sum = float(np.sum(result.corrected_action))
    print("sum(corrected):", round(simplex_sum, 6))
    if abs(simplex_sum - 1.0) > 1e-3:
        print("WARN: corrected action is not on simplex within 1e-3")

    section("Done")
    print("Native path: python examples/native_compiled_projection.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
