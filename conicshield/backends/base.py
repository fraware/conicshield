"""Explicit solver backend identifiers and AUTO resolution policy.

AUTO never selects vendor Moreau merely because the ``moreau`` module imports.
Silent production-backend switching after failure is forbidden; declared fallback
evidence (S2) remains the only sanctioned recovery path.
"""

from __future__ import annotations

import os
from enum import StrEnum


class Backend(StrEnum):
    """Production backend identifiers (string values retained for compatibility)."""

    AUTO = "auto"
    PUBLIC_CLARABEL = "public_clarabel"
    PUBLIC_SCS = "public_scs"
    CVXPY_MOREAU = "cvxpy_moreau"
    NATIVE_MOREAU = "native_moreau"
    NATIVE_MOREAU_BATCH = "native_moreau_batch"


VENDOR_BACKENDS: frozenset[Backend] = frozenset(
    {
        Backend.CVXPY_MOREAU,
        Backend.NATIVE_MOREAU,
        Backend.NATIVE_MOREAU_BATCH,
    }
)

PUBLIC_BACKENDS: frozenset[Backend] = frozenset(
    {
        Backend.PUBLIC_CLARABEL,
        Backend.PUBLIC_SCS,
    }
)

# Environment variable for an *explicit* production override used only by AUTO.
# Values must be Backend enum names or values. Vendor values are allowed only when
# set deliberately here — never inferred from package importability.
AUTO_PRODUCTION_ENV = "CONICSHIELD_PRODUCTION_BACKEND"


def parse_backend(raw: str | Backend) -> Backend:
    """Parse a backend name or value into :class:`Backend`."""
    if isinstance(raw, Backend):
        return raw
    text = str(raw).strip()
    if not text:
        raise ValueError("backend must be a non-empty string")
    try:
        return Backend(text)
    except ValueError:
        pass
    try:
        return Backend[text.upper()]
    except KeyError as exc:
        raise ValueError(
            f"Unknown backend {raw!r}. Expected one of: "
            + ", ".join(m.name for m in Backend)
        ) from exc


def configured_production_backend() -> Backend | None:
    """Return an explicitly configured production backend for AUTO, if any.

    Reads :data:`AUTO_PRODUCTION_ENV`. Empty / unset → ``None`` (AUTO defaults
    to :attr:`Backend.PUBLIC_CLARABEL`).
    """
    raw = os.environ.get(AUTO_PRODUCTION_ENV, "").strip()
    if not raw:
        return None
    backend = parse_backend(raw)
    if backend is Backend.AUTO:
        raise ValueError(
            f"{AUTO_PRODUCTION_ENV} cannot be AUTO; set an explicit backend "
            f"(e.g. PUBLIC_CLARABEL or CVXPY_MOREAU)."
        )
    return backend


def resolve_backend(
    backend: Backend | str,
    *,
    production_backend: Backend | str | None = None,
) -> Backend:
    """Resolve ``backend`` to a concrete non-AUTO backend.

    Policy:
    * Explicit non-AUTO selections are returned unchanged.
    * AUTO uses ``production_backend`` when provided, else
      :func:`configured_production_backend`, else :attr:`Backend.PUBLIC_CLARABEL`.
    * AUTO never inspects ``import moreau`` / package presence.
    """
    selected = parse_backend(backend)
    if selected is not Backend.AUTO:
        return selected

    override = production_backend
    if override is None:
        override = configured_production_backend()
    if override is None:
        return Backend.PUBLIC_CLARABEL

    resolved = parse_backend(override)
    if resolved is Backend.AUTO:
        raise ValueError("production_backend override must not be AUTO")
    return resolved


def is_vendor_backend(backend: Backend | str) -> bool:
    return parse_backend(backend) in VENDOR_BACKENDS


def is_public_backend(backend: Backend | str) -> bool:
    return parse_backend(backend) in PUBLIC_BACKENDS
