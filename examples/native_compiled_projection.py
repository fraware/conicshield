#!/usr/bin/env python3
"""One native compiled sequential projection (requires vendor Moreau).

Audience: integrator evaluating sequential native compiled path.
Prerequisites: vendor Moreau installed and licensed; ``pip install -e ".[solver]"`` or project .venv.
Proves: ``create_projector(..., Backend.NATIVE_MOREAU)`` returns a corrected action vector.
Does not prove: batched throughput wins or parity against reference without separate parity run.
Expected: prints proposed/corrected vectors, or exits 0 with Skip if Moreau unavailable.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import minimal_spec  # noqa: E402

from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions
from conicshield.core.solver_factory import Backend, create_projector


def main() -> int:
    try:
        import moreau  # noqa: F401
    except ImportError as exc:
        print("Skip: moreau not installed.", exc)
        return 0

    spec = minimal_spec()
    projector = create_projector(
        spec=spec,
        backend=Backend.NATIVE_MOREAU,
        native_options=NativeMoreauCompiledOptions(device="cpu", max_iter=800, verbose=False),
    )
    prev = np.full(4, 0.25, dtype=np.float64)
    proposed = np.array([0.7, 0.1, 0.1, 0.1], dtype=np.float64)
    try:
        result = projector.project(proposed, prev)
    except RuntimeError as exc:
        if "license" in str(exc).lower():
            print("Skip: Moreau license not available.", exc)
            return 0
        raise
    print("proposed:", proposed)
    print("corrected:", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
