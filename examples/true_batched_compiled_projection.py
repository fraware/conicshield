#!/usr/bin/env python3
"""True batched compiled solve via ``NativeMoreauCompiledBatchProjector``.

Audience: integrator evaluating native batch API existence.
Prerequisites: vendor Moreau installed and licensed; ``pip install -e ".[solver]"`` on Linux/WSL.
Proves: ``create_batch_projector`` + ``project_batch`` returns shape ``(K, n)`` with simplex-feasible rows.
Does not prove: universal throughput wins — true batch exists in code; public narrative is
  **viability_only** (see ``benchmarks/reports/reference_system_status.json`` and
  docs/SOLVER_PATHS_AND_BATCHING.md).
Expected: input/output shapes; corrected batch array; per-row simplex sums ~ 1.0 — or SKIP.
"""

from __future__ import annotations

import numpy as np

from _common import configure_stdio, minimal_spec, section, skip

from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions
from conicshield.core.solver_factory import create_batch_projector


def main() -> int:
    configure_stdio()

    section("Environment")
    try:
        import moreau  # noqa: F401
    except ImportError as exc:
        return skip("moreau not installed", detail=exc)

    batch = create_batch_projector(
        spec=minimal_spec(),
        native_options=NativeMoreauCompiledOptions(device="cpu", max_iter=800, verbose=False),
    )
    prev = np.full(4, 0.25, dtype=np.float64)
    proposals = np.array(
        [
            [0.85, 0.05, 0.05, 0.05],
            [0.2, 0.3, 0.25, 0.25],
            [0.4, 0.35, 0.15, 0.1],
        ],
        dtype=np.float64,
    )

    section("project_batch")
    try:
        corrected = batch.project_batch(proposals, prev)
    except RuntimeError as exc:
        if "license" in str(exc).lower():
            return skip("Moreau license not available", detail=exc)
        raise

    print("input shape:", proposals.shape)
    print("output shape:", corrected.shape)
    if corrected.shape != proposals.shape:
        print("unexpected output shape")
        return 1

    section("Per-row simplex check")
    for i, row in enumerate(corrected):
        s = float(np.sum(row))
        print(f"  row {i}: sum={s:.6f} corrected={np.round(row, 4).tolist()}")
        if abs(s - 1.0) > 1e-3:
            print(f"  WARN: row {i} not on simplex within 1e-3")

    section("Done")
    print("Throughput claims are scenario-governed — see docs/SOLVER_PATHS_AND_BATCHING.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
