from __future__ import annotations

from typing import Any

import numpy as np

from conicshield.core.result import ProjectionResult


class PassthroughProjector:
    """Reference/testing projector: returns proposed distribution as the correction."""

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
        proposed = np.asarray(proposed_action, dtype=float).copy()
        return ProjectionResult(
            proposed_action=proposed,
            corrected_action=proposed.copy(),
            intervened=False,
            intervention_norm=0.0,
            solver_status="optimal",
            objective_value=0.0,
            active_constraints=[],
            warm_started=True,
            solve_time_sec=0.001,
            setup_time_sec=0.0001,
            iterations=1,
            construction_time_sec=0.0,
            device="cpu",
            metadata=dict(metadata or {}),
        )
