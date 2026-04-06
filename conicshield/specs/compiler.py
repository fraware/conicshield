from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield._optional import OptionalDependencyError, require_module
from conicshield.core.result import ProjectionResult
from conicshield.specs.schema import SafetySpec


@dataclass(slots=True)
class SolverOptions:
    solver_name: str = "MOREAU"
    verify_solver_name: str | None = None
    device: str = "cpu"
    max_iter: int = 300
    verbose: bool = False
    time_limit: float | None = None
    ipm_settings: dict[str, Any] = field(default_factory=dict)
    active_tol: float = 1e-6


class CVXPYMoreauProjector:
    """Reference projector using CVXPY.

    The solver-backed path is optional. In environments without CVXPY,
    the module raises a clear optional-dependency error when invoked.
    """

    def __init__(self, *, spec: SafetySpec, options: SolverOptions | None = None) -> None:
        self.spec = spec
        self.options = options or SolverOptions()

    def _ensure_initialized(self) -> None:
        require_module("cvxpy", "CVXPY-based reference projector")
        raise OptionalDependencyError(
            "The CVXPY/Moreau reference projector is provided as an integration seam. "
            "Wire the exact constraint compilation for your deployed spec family before use."
        )

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
        self._ensure_initialized()
        raise RuntimeError("Unreachable")
