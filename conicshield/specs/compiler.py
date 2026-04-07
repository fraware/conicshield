from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.core.result import ProjectionResult
from conicshield.core.telemetry import extract_cvxpy_telemetry, telemetry_into_projection_fields
from conicshield.solver_errors import require_solver_module
from conicshield.specs.schema import SafetySpec
from conicshield.specs.shield_qp import parse_safety_spec_for_shield


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
    """Reference projector: CVXPY model solved with ``cp.MOREAU``."""

    def __init__(self, *, spec: SafetySpec, options: SolverOptions | None = None) -> None:
        self.spec = spec
        self.options = options or SolverOptions()

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
        require_solver_module("cvxpy", "CVXPY-based reference projector")
        import cvxpy as cp

        moreau_solver = getattr(cp, "MOREAU", None)
        if moreau_solver is None:
            raise RuntimeError("CVXPY does not expose cp.MOREAU. Install moreau, cvxpy>=1.8.2, and cvxpylayers>=1.0.4.")

        data = parse_safety_spec_for_shield(self.spec)
        n = data.n
        x = cp.Variable(n)
        cons: list = [
            cp.sum(x) == float(data.simplex_total),
            x >= np.asarray(data.lower, dtype=np.float64),
            x <= np.asarray(data.upper, dtype=np.float64),
        ]
        for i in range(n):
            if not data.allowed_mask[i]:
                cons.append(x[i] == 0)

        prev = np.asarray(previous_action, dtype=np.float64).reshape(-1) if previous_action is not None else None
        if prev is not None and prev.shape[0] != n:
            raise ValueError("previous_action length mismatch")
        if prev is not None:
            d = np.asarray(data.max_delta, dtype=np.float64)
            cons.append(x - prev <= d)
            cons.append(prev - x <= d)

        p = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
        pw = float(policy_weight)
        rw = float(reference_weight)
        if reference_action is not None and rw > 0.0:
            r = np.asarray(reference_action, dtype=np.float64).reshape(-1)
            if r.shape[0] != n:
                raise ValueError("reference_action length mismatch")
            objective = cp.Minimize(pw * cp.sum_squares(x - p) + rw * cp.sum_squares(x - r))
        else:
            objective = cp.Minimize(pw * cp.sum_squares(x - p))

        problem = cp.Problem(objective, cons)

        solve_kw: dict[str, Any] = {
            "solver": moreau_solver,
            "verbose": bool(self.options.verbose),
        }
        if self.options.device:
            solve_kw["device"] = self.options.device
        if self.options.max_iter:
            solve_kw["max_iter"] = int(self.options.max_iter)
        if self.options.time_limit is not None:
            solve_kw["time_limit"] = float(self.options.time_limit)
        if self.options.ipm_settings:
            solve_kw["ipm_settings"] = dict(self.options.ipm_settings)

        warm_started = False
        problem.solve(**solve_kw)

        if x.value is None:
            raise RuntimeError(f"CVXPY/Moreau solve failed: status={problem.status!r}")

        xv = np.asarray(x.value, dtype=np.float64).reshape(-1)
        proposed = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
        diff = float(np.linalg.norm(xv - proposed))
        intervened = diff > 1e-8

        tel = extract_cvxpy_telemetry(problem, warm_started=warm_started)
        tel_fields = telemetry_into_projection_fields(tel)

        active: list[str] = []
        if np.any(~data.allowed_mask):
            active.append("turn_feasibility")

        return ProjectionResult(
            proposed_action=proposed,
            corrected_action=xv,
            intervened=intervened,
            intervention_norm=diff,
            active_constraints=active,
            metadata=dict(metadata or {}),
            **tel_fields,
        )
