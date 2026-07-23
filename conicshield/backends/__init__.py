"""Backend adapters, status normalization, public projectors, and capability discovery.

Public CVXPY projectors are imported lazily so leaf modules (``status``, ``base``)
can be used from verification/core without circular imports.
"""

from __future__ import annotations

from typing import Any

from conicshield.backends.base import (
    AUTO_PRODUCTION_ENV,
    PUBLIC_BACKENDS,
    VENDOR_BACKENDS,
    Backend,
    configured_production_backend,
    is_public_backend,
    is_vendor_backend,
    parse_backend,
    resolve_backend,
)
from conicshield.backends.status import (
    CanonicalSolverStatus,
    normalize_cvxpy_status,
    normalize_moreau_status,
    normalize_solver_status,
)

__all__ = [
    "AUTO_PRODUCTION_ENV",
    "Backend",
    "BackendCapabilities",
    "CapabilityFlag",
    "CanonicalSolverStatus",
    "CVXPYClarabelProjector",
    "CVXPYSCSProjector",
    "PUBLIC_BACKENDS",
    "PublicClarabelProjector",
    "PublicSCSProjector",
    "VENDOR_BACKENDS",
    "configured_production_backend",
    "discover_all_capabilities",
    "evidence_subset",
    "is_public_backend",
    "is_vendor_backend",
    "normalize_cvxpy_status",
    "normalize_moreau_status",
    "normalize_solver_status",
    "parse_backend",
    "resolve_backend",
]

_LAZY_PUBLIC = {
    "CVXPYClarabelProjector",
    "CVXPYSCSProjector",
    "PublicClarabelProjector",
    "PublicSCSProjector",
}
_LAZY_CAPS = {
    "BackendCapabilities",
    "CapabilityFlag",
    "discover_all_capabilities",
    "evidence_subset",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_PUBLIC:
        from conicshield.backends import public_cvxpy as _public

        return getattr(_public, name)
    if name in _LAZY_CAPS:
        from conicshield.backends import capabilities as _caps

        return getattr(_caps, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
