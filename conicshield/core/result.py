from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(slots=True)
class ProjectionResult:
    proposed_action: np.ndarray
    corrected_action: np.ndarray
    intervened: bool
    intervention_norm: float
    solver_status: str
    objective_value: float | None = None
    active_constraints: list[str] = field(default_factory=list)
    warm_started: bool = False

    solve_time_sec: float | None = None
    setup_time_sec: float | None = None
    iterations: int | None = None
    construction_time_sec: float | None = None
    device: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "proposed_action": self.proposed_action.tolist(),
            "corrected_action": self.corrected_action.tolist(),
            "intervened": self.intervened,
            "intervention_norm": float(self.intervention_norm),
            "solver_status": self.solver_status,
            "objective_value": self.objective_value,
            "active_constraints": list(self.active_constraints),
            "warm_started": self.warm_started,
            "solve_time_sec": self.solve_time_sec,
            "setup_time_sec": self.setup_time_sec,
            "iterations": self.iterations,
            "construction_time_sec": self.construction_time_sec,
            "device": self.device,
            "metadata": dict(self.metadata),
        }
