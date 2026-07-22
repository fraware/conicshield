"""Backend adapters, status normalization, public projectors, and capability discovery."""

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
from conicshield.backends.capabilities import (
    BackendCapabilities,
    CapabilityFlag,
    discover_all_capabilities,
    evidence_subset,
)
from conicshield.backends.public_cvxpy import (
    CVXPYClarabelProjector,
    CVXPYSCSProjector,
    PublicClarabelProjector,
    PublicSCSProjector,
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
