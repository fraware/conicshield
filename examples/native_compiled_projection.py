#!/usr/bin/env python3
"""One native compiled sequential projection (requires vendor Moreau).

Audience: integrator evaluating the sequential native compiled path.
Prerequisites: vendor Moreau installed and licensed; ``pip install -e ".[solver]"`` on Linux/WSL.
Proves: ``create_projector(..., Backend.NATIVE_MOREAU)`` returns a feasible corrected action.
Does not prove: batched throughput wins or reference parity (run parity tooling separately).
Expected: proposed/corrected vectors and solver metadata — or SKIP if Moreau/license unavailable.
"""

from __future__ import annotations

import numpy as np

from _common import configure_stdio, minimal_spec, section, skip

from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions
from conicshield.core.solver_factory import Backend, create_projector


def main() -> int:
    configure_stdio()

    section("Environment")
    try:
        import moreau  # noqa: F401
    except ImportError as exc:
        return skip("moreau not installed", detail=exc)

    spec = minimal_spec()
    projector = create_projector(
        spec=spec,
        backend=Backend.NATIVE_MOREAU,
        native_options=NativeMoreauCompiledOptions(device="cpu", max_iter=800, verbose=False),
    )

    prev = np.full(4, 0.25, dtype=np.float64)
    proposed = np.array([0.7, 0.1, 0.1, 0.1], dtype=np.float64)

    section("project (NATIVE_MOREAU)")
    try:
        result = projector.project(proposed, prev)
    except RuntimeError as exc:
        if "license" in str(exc).lower():
            return skip("Moreau license not available", detail=exc)
        raise

    print("proposed:", np.round(proposed, 4).tolist())
    print("corrected:", np.round(result.corrected_action, 4).tolist())
    print("solver_status:", result.solver_status)
    print("intervened:", result.intervened)
    if result.solve_time_sec is not None:
        print("solve_time_sec:", round(result.solve_time_sec, 6))
    print("sum(corrected):", round(float(np.sum(result.corrected_action)), 6))

    section("Done")
    print("Batch API: python examples/true_batched_compiled_projection.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
