#!/usr/bin/env python3
"""True batched compiled solve via NativeMoreauCompiledBatchProjector (requires vendor Moreau)."""

from __future__ import annotations

import numpy as np

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import minimal_spec  # noqa: E402

from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions
from conicshield.core.solver_factory import create_batch_projector


def main() -> int:
    try:
        import moreau  # noqa: F401
    except ImportError as exc:
        print("Skip: moreau not installed.", exc)
        return 0

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
    try:
        corrected = batch.project_batch(proposals, prev)
    except RuntimeError as exc:
        if "license" in str(exc).lower():
            print("Skip: Moreau license not available.", exc)
            return 0
        raise
    print("input shape:", proposals.shape)
    print("output shape:", corrected.shape)
    print("corrected_batch:\n", corrected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
