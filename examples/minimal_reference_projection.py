#!/usr/bin/env python3
"""One reference (CVXPY/Moreau) projection on the minimal supported spec.

Audience: integrator (public/reference stack).
Prerequisites: ``pip install -e ".[dev]"``; CVXPY/Moreau available in environment.
Proves: ``create_projector`` + ``Backend.CVXPY_MOREAU`` returns a corrected action vector.
Does not prove: native batch speedup or vendor-native parity.
Expected: prints proposed and corrected vectors (or Skip if solver unavailable).
"""

from __future__ import annotations

import numpy as np

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import minimal_spec  # noqa: E402

from conicshield.core.solver_factory import Backend, create_projector


def main() -> int:
    spec = minimal_spec()
    projector = create_projector(spec=spec, backend=Backend.CVXPY_MOREAU)
    prev = np.full(4, 0.25, dtype=np.float64)
    proposed = np.array([0.7, 0.1, 0.1, 0.1], dtype=np.float64)
    try:
        result = projector.project(proposed, prev)
    except Exception as exc:
        print("Skip: reference stack unavailable in this environment.", exc)
        return 0
    print("corrected_action:", result.corrected_action)
    print("solver_status:", result.solver_status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
