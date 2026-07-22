"""Structural and setup fingerprints for compiled shield templates.

Re-exports S3 structural/numerical keys and adds setup-value fingerprints used
to skip redundant ``CompiledSolver.setup`` calls.
"""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

from conicshield.compilation.structural_keys import (
    NumericalSignature,
    StructuralFingerprint,
    numerical_signature,
    structural_fingerprint,
)

__all__ = [
    "NumericalSignature",
    "SetupValuesFingerprint",
    "StructuralFingerprint",
    "numerical_signature",
    "setup_values_fingerprint",
    "structural_fingerprint",
]


class SetupValuesFingerprint(str):
    """Opaque digest of ``P_values`` / ``A_values`` that affect factorization."""

    __slots__ = ()


def setup_values_fingerprint(
    p_values: np.ndarray,
    a_values: np.ndarray,
    *,
    extra: Any = None,
) -> SetupValuesFingerprint:
    """Hash numeric CSR values required by ``setup`` (not ``q`` / ``b``)."""
    h = hashlib.sha256()
    p = np.ascontiguousarray(np.asarray(p_values, dtype=np.float64))
    a = np.ascontiguousarray(np.asarray(a_values, dtype=np.float64))
    h.update(b"P")
    h.update(np.asarray(p.shape, dtype=np.int64).tobytes())
    h.update(p.tobytes())
    h.update(b"A")
    h.update(np.asarray(a.shape, dtype=np.int64).tobytes())
    h.update(a.tobytes())
    if extra is not None:
        h.update(repr(extra).encode("utf-8"))
    return SetupValuesFingerprint(h.hexdigest()[:24])
