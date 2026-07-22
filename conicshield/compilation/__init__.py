"""Compilation support: topology, templates, fingerprints, caches, and pools."""

from __future__ import annotations

from conicshield.compilation.bounded_cache import BoundedLRUCache
from conicshield.compilation.capabilities import (
    DEFAULT_COMPILATION_CAPABILITIES,
    CompilationCapabilities,
    resolve_capabilities,
)
from conicshield.compilation.compiled_template import CompiledShieldTemplate, NumericBuffers
from conicshield.compilation.metrics import LifecycleMetrics
from conicshield.compilation.parameter_layout import ParameterLayout
from conicshield.compilation.solver_pool import SolverPool, SolverPoolCheckoutError
from conicshield.compilation.structural_fingerprint import (
    NumericalSignature,
    SetupValuesFingerprint,
    StructuralFingerprint,
    numerical_signature,
    setup_values_fingerprint,
    structural_fingerprint,
)
from conicshield.compilation.topology import ConstraintTopology, topology_from_shield_qp

__all__ = [
    "DEFAULT_COMPILATION_CAPABILITIES",
    "BoundedLRUCache",
    "CompilationCapabilities",
    "CompiledShieldTemplate",
    "ConstraintTopology",
    "LifecycleMetrics",
    "NumericalSignature",
    "NumericBuffers",
    "ParameterLayout",
    "SetupValuesFingerprint",
    "SolverPool",
    "SolverPoolCheckoutError",
    "StructuralFingerprint",
    "numerical_signature",
    "resolve_capabilities",
    "setup_values_fingerprint",
    "structural_fingerprint",
    "topology_from_shield_qp",
]
