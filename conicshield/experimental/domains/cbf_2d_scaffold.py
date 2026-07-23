"""Uncertainty-aware CBF safety filter for 2D motion — compatibility shim.

Prefer ``conicshield.experimental.domains.cbf_2d``.
"""

from __future__ import annotations

from conicshield.experimental.domains.cbf_2d import (
    CBF2DDomain as CBF2DDomainScaffold,
)
from conicshield.experimental.domains.cbf_2d import (
    nominal_cbf_qp_placeholder,
)

__all__ = ["CBF2DDomainScaffold", "nominal_cbf_qp_placeholder"]
