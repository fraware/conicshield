from __future__ import annotations

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
from conicshield.core.interfaces import ProjectorProtocol
from conicshield.core.moreau_batched import NativeMoreauCompiledBatchProjector
from conicshield.core.moreau_compiled import (
    NativeMoreauCompiledOptions,
    NativeMoreauCompiledProjector,
)
from conicshield.specs.compiler import CVXPYMoreauProjector, SolverOptions
from conicshield.specs.schema import SafetySpec

__all__ = [
    "AUTO_PRODUCTION_ENV",
    "Backend",
    "PUBLIC_BACKENDS",
    "VENDOR_BACKENDS",
    "CanonicalSolverStatus",
    "CVXPYClarabelProjector",
    "CVXPYSCSProjector",
    "PublicClarabelProjector",
    "PublicSCSProjector",
    "configured_production_backend",
    "create_batch_projector",
    "create_projector",
    "is_public_backend",
    "is_vendor_backend",
    "normalize_cvxpy_status",
    "normalize_moreau_status",
    "normalize_solver_status",
    "parse_backend",
    "resolve_backend",
]


def create_projector(
    *,
    spec: SafetySpec,
    backend: Backend | str = Backend.CVXPY_MOREAU,
    cvxpy_options: SolverOptions | None = None,
    native_options: NativeMoreauCompiledOptions | None = None,
    production_backend: Backend | str | None = None,
) -> ProjectorProtocol:
    """Create a projector for ``backend``.

    Default remains explicit :attr:`Backend.CVXPY_MOREAU` for compatibility.
    Pass :attr:`Backend.AUTO` for the documented AUTO policy (defaults to
    :attr:`Backend.PUBLIC_CLARABEL`; never selects vendor Moreau from importability).
    """
    resolved = resolve_backend(backend, production_backend=production_backend)
    if resolved is Backend.PUBLIC_CLARABEL:
        return PublicClarabelProjector(spec=spec, options=cvxpy_options)
    if resolved is Backend.PUBLIC_SCS:
        return PublicSCSProjector(spec=spec, options=cvxpy_options)
    if resolved is Backend.CVXPY_MOREAU:
        return CVXPYMoreauProjector(spec=spec, options=cvxpy_options)
    if resolved is Backend.NATIVE_MOREAU:
        return NativeMoreauCompiledProjector(spec=spec, options=native_options)
    raise ValueError(
        f"Unsupported backend for create_projector: {resolved!s}. "
        f"Use create_batch_projector for {Backend.NATIVE_MOREAU_BATCH!s}."
    )


def create_batch_projector(
    *,
    spec: SafetySpec,
    backend: Backend | str = Backend.NATIVE_MOREAU_BATCH,
    native_options: NativeMoreauCompiledOptions | None = None,
    production_backend: Backend | str | None = None,
) -> NativeMoreauCompiledBatchProjector:
    """Return the batched native projector (one ``CompiledSolver.solve(qs, bs)`` per call).

    Use ``Backend.NATIVE_MOREAU_BATCH`` (default) or ``Backend.NATIVE_MOREAU`` as aliases.
    AUTO resolves via :func:`resolve_backend` but batching still requires a native vendor
    backend — AUTO→PUBLIC_* is rejected with an actionable error.
    """
    resolved = resolve_backend(backend, production_backend=production_backend)
    if resolved not in (Backend.NATIVE_MOREAU, Backend.NATIVE_MOREAU_BATCH):
        raise ValueError(
            f"Batched compiled projection requires {Backend.NATIVE_MOREAU_BATCH!s} or "
            f"{Backend.NATIVE_MOREAU!s}, got {resolved!s} "
            f"(from requested {backend!s}). AUTO/public backends are not batch-native; "
            "select NATIVE_MOREAU_BATCH explicitly when the vendor stack is installed."
        )
    return NativeMoreauCompiledBatchProjector(spec=spec, options=native_options)
