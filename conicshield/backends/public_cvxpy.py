"""Public CVXPY projectors (Clarabel / SCS) for credential-free operation."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from conicshield.backends.status import normalize_cvxpy_status
from conicshield.compilation.metrics import LifecycleMetrics
from conicshield.core.interfaces import ConcurrencyModel
from conicshield.core.result import ProjectionResult
from conicshield.core.telemetry import extract_cvxpy_telemetry, telemetry_into_projection_fields
from conicshield.solver_errors import require_solver_module
from conicshield.specs.compiler import SolverOptions
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


class _PublicCvxpyProjectorBase:
    """Shared shield-QP path for public CVXPY solvers (not vendor Moreau)."""

    concurrency_model: ConcurrencyModel = ConcurrencyModel.STATELESS
    backend_id: str
    default_solver_name: str

    def __init__(
        self,
        *,
        spec: SafetySpec,
        options: SolverOptions | None = None,
        metrics: LifecycleMetrics | None = None,
    ) -> None:
        self.spec = spec
        opts = options or SolverOptions(solver_name=self.default_solver_name)
        if not opts.solver_name or opts.solver_name.upper() == "MOREAU":
            opts = replace(opts, solver_name=self.default_solver_name)
        self.options = opts
        self.metrics = metrics if metrics is not None else LifecycleMetrics()

    def reset_state(self, *, scope_id: str | None = None) -> None:
        del scope_id

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
        require_solver_module("cvxpy", f"public {self.default_solver_name} projector")
        import cvxpy as cp

        solver_name = str(self.options.solver_name or self.default_solver_name).upper()
        solver = getattr(cp, solver_name, None)
        if solver is None:
            raise RuntimeError(
                f"CVXPY does not expose cp.{solver_name}. "
                f'Install public solvers via: pip install -e ".[solver-public]" '
                "(see docs/MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md)."
            )

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
            del warm_start
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
                "solver": solver,
                "verbose": bool(self.options.verbose),
            }
            if self.options.max_iter:
                if solver_name == "SCS":
                    solve_kw["max_iters"] = int(self.options.max_iter)
                else:
                    solve_kw["max_iter"] = int(self.options.max_iter)
            if self.options.time_limit is not None:
                solve_kw["time_limit"] = float(self.options.time_limit)

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
                        f"CVXPY/{solver_name} solve failed: status={problem.status!r}"
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
                backend_id=self.backend_id,
                solver_name=solver_name,
                device="cpu",
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


class PublicClarabelProjector(_PublicCvxpyProjectorBase):
    """Credential-free public projector using CVXPY Clarabel."""

    backend_id = "public_clarabel"
    default_solver_name = "CLARABEL"


class PublicSCSProjector(_PublicCvxpyProjectorBase):
    """Credential-free public projector using CVXPY SCS."""

    backend_id = "public_scs"
    default_solver_name = "SCS"


# Aliases accepted by stabilization tests / docs.
CVXPYClarabelProjector = PublicClarabelProjector
CVXPYSCSProjector = PublicSCSProjector
