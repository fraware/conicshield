from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.backends.status import normalize_cvxpy_status
from conicshield.core.result import ProjectionResult
from conicshield.core.telemetry import extract_cvxpy_telemetry, telemetry_into_projection_fields
from conicshield.solver_errors import require_solver_module
from conicshield.specs.schema import SafetySpec
from conicshield.specs.shield_qp import parse_safety_spec_for_shield, validate_objective_weights
from conicshield.verification.fallback import (
    FallbackConfig,
    SolveAttemptResult,
    run_verified_release_pipeline,
)
from conicshield.verification.release import build_verified_projection_result, provenance_for_backend
from conicshield.verification.release_policy import ReleasePolicy
from conicshield.verification.residuals import ResidualTolerances


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
    abs_tol: float = 1e-6
    rel_tol: float = 1e-6
    intervention_abs_tol: float = 1e-8
    intervention_rel_tol: float = 1e-8
    accept_optimal_inaccurate: bool = False
    accept_iteration_limit: bool = False
    accept_time_limit: bool = False
    enable_cold_retry: bool = False
    deadline_sec: float | None = None
    max_release_attempts: int = 4


class CVXPYMoreauProjector:
    """Reference projector: CVXPY model solved with ``cp.MOREAU``."""

    def __init__(self, *, spec: SafetySpec, options: SolverOptions | None = None) -> None:
        self.spec = spec
        self.options = options or SolverOptions()

    def _release_policy(self) -> ReleasePolicy:
        opts = self.options
        return ReleasePolicy(
            accept_optimal_inaccurate=bool(opts.accept_optimal_inaccurate),
            accept_iteration_limit=bool(opts.accept_iteration_limit),
            accept_time_limit=bool(opts.accept_time_limit),
            tolerances=ResidualTolerances(
                abs_tol=float(opts.abs_tol),
                rel_tol=float(opts.rel_tol),
                active_tol=float(opts.active_tol),
            ),
            intervention_abs_tol=float(opts.intervention_abs_tol),
            intervention_rel_tol=float(opts.intervention_rel_tol),
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
        require_solver_module("cvxpy", "CVXPY-based reference projector")
        import cvxpy as cp

        moreau_solver = getattr(cp, "MOREAU", None)
        if moreau_solver is None:
            raise RuntimeError(
                "CVXPY does not expose cp.MOREAU. Install moreau, cvxpy>=1.8.2, "
                "and cvxpylayers>=1.0.4."
            )

        # Both CVXPY and native paths consume the same canonical ShieldQPData IR.
        data = parse_safety_spec_for_shield(self.spec)
        n = data.n
        pw, rw = validate_objective_weights(
            policy_weight,
            reference_weight,
            reference_present=reference_action is not None,
        )
        release_policy = self._release_policy()
        last_telemetry: dict[str, Any] = {"solver_status": "unknown", "warm_started": False}

        def _primary_solve(*, warm_start: bool) -> SolveAttemptResult:
            del warm_start  # CVXPY Moreau path does not persist warm starts here
            x = cp.Variable(n)
            cons: list = [
                cp.sum(x) == float(data.simplex_total),
                x >= np.asarray(data.lower, dtype=np.float64),
                x <= np.asarray(data.upper, dtype=np.float64),
            ]
            for i in range(n):
                if not data.allowed_mask[i]:
                    cons.append(x[i] == 0)

            prev = (
                np.asarray(previous_action, dtype=np.float64).reshape(-1)
                if previous_action is not None
                else None
            )
            if prev is not None and prev.shape[0] != n:
                raise ValueError("previous_action length mismatch")
            if prev is not None:
                d = np.asarray(data.max_delta, dtype=np.float64)
                cons.append(x - prev <= d)
                cons.append(prev - x <= d)

            p = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
            if reference_action is not None and rw > 0.0:
                r = np.asarray(reference_action, dtype=np.float64).reshape(-1)
                if r.shape[0] != n:
                    raise ValueError("reference_action length mismatch")
                objective = cp.Minimize(
                    pw * cp.sum_squares(x - p) + rw * cp.sum_squares(x - r)
                )
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

            try:
                problem.solve(**solve_kw)
            except Exception as exc:
                last_telemetry.clear()
                last_telemetry.update({"solver_status": "backend_error", "warm_started": False})
                return SolveAttemptResult(
                    candidate=None,
                    raw_status="backend_error",
                    objective=None,
                    error=exc,
                    warm_started=False,
                    kind="primary",
                )

            tel = extract_cvxpy_telemetry(problem, warm_started=False)
            last_telemetry.clear()
            last_telemetry.update(tel)
            if x.value is None:
                return SolveAttemptResult(
                    candidate=None,
                    raw_status=getattr(problem, "status", "unknown"),
                    objective=tel.get("objective_value"),
                    error=RuntimeError(
                        f"CVXPY/Moreau solve failed: status={problem.status!r}"
                    ),
                    warm_started=False,
                    kind="primary",
                )
            xv = np.asarray(x.value, dtype=np.float64).reshape(-1)
            return SolveAttemptResult(
                candidate=xv,
                raw_status=getattr(problem, "status", tel.get("solver_status")),
                objective=tel.get("objective_value"),
                warm_started=False,
                kind="primary",
            )

        outcome = run_verified_release_pipeline(
            data=data,
            proposed_action=np.asarray(proposed_action, dtype=np.float64),
            previous_action=previous_action,
            reference_action=reference_action,
            policy_weight=pw,
            reference_weight=rw,
            primary_solve=_primary_solve,
            config=FallbackConfig(
                enable_cold_retry=bool(self.options.enable_cold_retry),
                max_attempts=int(self.options.max_release_attempts),
                deadline_sec=self.options.deadline_sec,
                release_policy=release_policy,
                fail_safe_policy=data.fail_safe_policy,
            ),
            status_normalizer=normalize_cvxpy_status,
        )

        tel_fields = telemetry_into_projection_fields(last_telemetry)
        return build_verified_projection_result(
            proposed_action=np.asarray(proposed_action, dtype=np.float64),
            outcome=outcome,
            telemetry=tel_fields,
            provenance=provenance_for_backend(
                backend_id="cvxpy_moreau",
                solver_name=str(self.options.solver_name),
                device=self.options.device,
                package_distribution="cvxpy",
                settings={
                    "max_iter": self.options.max_iter,
                    "time_limit": self.options.time_limit,
                },
                warm_start_policy="none",
            ),
            metadata=metadata,
            release_policy=release_policy,
        )
