from __future__ import annotations

from typing import Any, Protocol

import numpy as np

from conicshield.core.result import ProjectionResult


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
    ) -> ProjectionResult:
        ...
