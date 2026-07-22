from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

import numpy as np

from conicshield.core.result import ProjectionResult


class ConcurrencyModel(StrEnum):
    """Declared concurrency contract for a projector / solver implementation.

    * ``INSTANCE_CONFINED`` — one owner thread/coroutine; sharing is undefined.
    * ``LOCK_PROTECTED`` — internal lock serializes ``project`` / ``reset_state``.
    * ``POOLED_EXCLUSIVE_CHECKOUT`` — mutable solvers obtained via exclusive pool checkout.
    * ``STATELESS`` — no mutable solver / warm-start state; safe to share.
    """

    INSTANCE_CONFINED = "instance_confined"
    LOCK_PROTECTED = "lock_protected"
    POOLED_EXCLUSIVE_CHECKOUT = "pooled_exclusive_checkout"
    STATELESS = "stateless"


class ProjectorProtocol(Protocol):
    def project(
        self,
        proposed_action: np.ndarray,
        previous_action: np.ndarray | None = None,
        *,
        reference_action: np.ndarray | None = None,
        policy_weight: float = 1.0,
        reference_weight: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> ProjectionResult: ...


class StatefulProjectorProtocol(ProjectorProtocol, Protocol):
    """Projector that may retain episode / trajectory warm-start state."""

    concurrency_model: ConcurrencyModel

    def reset_state(self, *, scope_id: str | None = None) -> None:
        """Clear warm starts and episode-scoped solver state.

        When ``scope_id`` is ``None``, clear all retained trajectory/episode state.
        When set, clear only state associated with that stable identity.
        """
        ...
