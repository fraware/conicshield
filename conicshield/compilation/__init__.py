"""Compilation support: structural fingerprints, bounded caches, and solver pools."""

from __future__ import annotations

from conicshield.compilation.bounded_cache import BoundedLRUCache
from conicshield.compilation.metrics import LifecycleMetrics
from conicshield.compilation.solver_pool import SolverPool, SolverPoolCheckoutError
from conicshield.compilation.structural_keys import (
    NumericalSignature,
    StructuralFingerprint,
    numerical_signature,
    structural_fingerprint,
)

__all__ = [
    "BoundedLRUCache",
    "LifecycleMetrics",
    "NumericalSignature",
    "SolverPool",
    "SolverPoolCheckoutError",
    "StructuralFingerprint",
    "numerical_signature",
    "structural_fingerprint",
]
