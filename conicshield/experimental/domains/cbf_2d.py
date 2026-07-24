"""Uncertainty-aware CBF safety filter for 2D motion (R5 / R13).

Stages:
  1. Nominal affine control-barrier QP (implemented)
  2. Batched agents with distinct states/obstacles (true compiled batch when topology matches)
  3. SOC robust margin under bounded L2 observation noise (implemented)
  4. Minimal experimental short-horizon RH — gated on stage-4 checklist green
     (see ``cbf_rh``; not full MPC / multi-robot / AD)

Hard non-claims: no MPC / recursive feasibility / multi-robot certificates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

import numpy as np

from conicshield.experimental.adapters.track1_protocols import (
    CanonicalSolverStatus,
    ReleaseDecision,
    SolverProvenance,
)
from conicshield.experimental.gradients.capability import CapabilityStatus

# Declared models (must be present on every verified filter output).
DYNAMICS_MODEL_ID = "single_integrator_2d.v1"  # p_dot = u
# Justified uncertainty model for stage 3 (see research notes):
# Position is observed as p_hat = p_true + δ with ||δ||_2 <= epsilon (hard bounded
# measurement noise). Barrier h(p)=||p-c||^2 - r^2 for single integrator p_dot=u.
# Robust CBF requires inf_{||δ||<=ε} [2(p+δ-c)·u + α h(p+δ)] >= 0.
# Conservative SOC-representable sufficient condition used here:
#   2(p-c)·u + α h(p) >= 2ε||u|| + α(2ε||p-c|| + ε^2)
# Equivalently with slack t: a·u - t >= b_rob,  t >= 2ε ||u||_2.
UNCERTAINTY_MODEL_ID = "bounded_l2_position_observation_noise.v1"
OBSERVATION_MODEL_ID = UNCERTAINTY_MODEL_ID

BATCH_MODE_COMPILED = "compiled_joint_qp"
BATCH_MODE_SEQUENTIAL = "sequential_adapter"
BATCH_EMULATION_WATERMARK = "batch_emulation:sequential_adapter"

_RESIDUAL_TOL = 1e-5
_ACTIVE_TOL = 1e-6


class CBFStage(StrEnum):
    STAGE1_NOMINAL = "stage1_nominal_affine_cbf_qp"
    STAGE2_BATCHED = "stage2_batched_agents"
    STAGE3_SOC_ROBUST = "stage3_soc_robust_margin"
    STAGE4_RECEDING = "stage4_receding_horizon_experimental"


class CBFBaseline(StrEnum):
    NO_FILTER = "no_filter"
    PUBLIC_SOLVER_FILTER = "public_solver_filter"
    MOREAU_FILTER = "moreau_filter"
    PRIMARY_PLUS_SHADOW = "primary_plus_shadow_assurance"
    EXACT_VS_SMOOTHED = "exact_versus_smoothed_differentiable_filter"


@dataclass(slots=True)
class AgentState2D:
    """Single-integrator agent in R^2: position p, desired control u_des."""

    position: np.ndarray  # shape (2,)
    u_desired: np.ndarray  # shape (2,)
    agent_id: str = "agent0"

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "position": np.asarray(self.position, dtype=np.float64).tolist(),
            "u_desired": np.asarray(self.u_desired, dtype=np.float64).tolist(),
        }


@dataclass(slots=True)
class CircularObstacle:
    center: np.ndarray
    radius: float
    obstacle_id: str = "obs0"

    def as_dict(self) -> dict[str, Any]:
        return {
            "obstacle_id": self.obstacle_id,
            "center": np.asarray(self.center, dtype=np.float64).tolist(),
            "radius": float(self.radius),
        }


@dataclass(slots=True)
class CBFVerificationReport:
    """Independent verification evidence for a CBF filter candidate.

    Never treats CVXPY returning a value alone as admissibility.
    """

    finite_value: bool
    norm_bound_residual: float
    cbf_residual: float
    robust_soc_residual: float | None
    solver_status: str
    canonical_status: CanonicalSolverStatus
    release_decision: ReleaseDecision
    active_constraints: tuple[str, ...]
    solver_provenance: SolverProvenance
    passed: bool
    residual_tolerance: float = _RESIDUAL_TOL
    notes: tuple[str, ...] = ()
    dynamics_model_id: str = DYNAMICS_MODEL_ID
    observation_model_id: str = OBSERVATION_MODEL_ID

    def as_dict(self) -> dict[str, Any]:
        return {
            "finite_value": self.finite_value,
            "norm_bound_residual": float(self.norm_bound_residual),
            "cbf_residual": float(self.cbf_residual),
            "robust_soc_residual": (
                None if self.robust_soc_residual is None else float(self.robust_soc_residual)
            ),
            "solver_status": self.solver_status,
            "canonical_status": str(self.canonical_status),
            "release_decision": str(self.release_decision),
            "active_constraints": list(self.active_constraints),
            "solver_provenance": self.solver_provenance.as_dict(),
            "passed": self.passed,
            "residual_tolerance": float(self.residual_tolerance),
            "notes": list(self.notes),
            "dynamics_model_id": self.dynamics_model_id,
            "observation_model_id": self.observation_model_id,
        }


@dataclass(slots=True)
class CBFFilterResult:
    agent_id: str
    u_safe: np.ndarray
    u_desired: np.ndarray
    intervened: bool
    intervention_norm: float
    barrier_value: float
    safety_margin: float
    active_constraints: tuple[str, ...]
    solver_status: str
    canonical_status: CanonicalSolverStatus
    baseline: str
    stage: str
    solve_time_sec: float | None = None
    fallback: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    verification: CBFVerificationReport | None = None
    release_decision: ReleaseDecision | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "u_safe": np.asarray(self.u_safe, dtype=np.float64).tolist(),
            "u_desired": np.asarray(self.u_desired, dtype=np.float64).tolist(),
            "intervened": self.intervened,
            "intervention_norm": float(self.intervention_norm),
            "barrier_value": float(self.barrier_value),
            "safety_margin": float(self.safety_margin),
            "active_constraints": list(self.active_constraints),
            "solver_status": self.solver_status,
            "canonical_status": str(self.canonical_status),
            "baseline": self.baseline,
            "stage": self.stage,
            "solve_time_sec": self.solve_time_sec,
            "fallback": self.fallback,
            "metadata": dict(self.metadata),
            "verification": None if self.verification is None else self.verification.as_dict(),
            "release_decision": None if self.release_decision is None else str(self.release_decision),
        }


@dataclass(slots=True)
class RobustnessValidationReport:
    """Independent worst-case δ check for a robust (or nominal) safe control."""

    epsilon: float
    delta_star: np.ndarray
    min_actual_margin: float
    soc_declared_margin: float | None
    bound_gap: float | None
    intervention_increase: float
    objective_cost: float
    robust_condition_holds: bool
    uncertainty_model_id: str = UNCERTAINTY_MODEL_ID
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "epsilon": float(self.epsilon),
            "delta_star": np.asarray(self.delta_star, dtype=np.float64).tolist(),
            "min_actual_margin": float(self.min_actual_margin),
            "soc_declared_margin": (
                None if self.soc_declared_margin is None else float(self.soc_declared_margin)
            ),
            "bound_gap": None if self.bound_gap is None else float(self.bound_gap),
            "intervention_increase": float(self.intervention_increase),
            "objective_cost": float(self.objective_cost),
            "robust_condition_holds": self.robust_condition_holds,
            "uncertainty_model_id": self.uncertainty_model_id,
            "notes": list(self.notes),
        }


def validate_cbf_inputs(
    agent: AgentState2D,
    obstacle: CircularObstacle,
    *,
    alpha: float,
    u_max: float,
    epsilon: float | None = None,
    require_dynamics_model: bool = True,
    require_observation_model: bool = False,
) -> None:
    """Fail closed on invalid CBF inputs (R13)."""

    p = np.asarray(agent.position, dtype=np.float64).reshape(-1)
    u = np.asarray(agent.u_desired, dtype=np.float64).reshape(-1)
    c = np.asarray(obstacle.center, dtype=np.float64).reshape(-1)
    if p.shape != (2,) or not np.all(np.isfinite(p)):
        raise ValueError("agent.position must be a finite 2D vector")
    if u.shape != (2,) or not np.all(np.isfinite(u)):
        raise ValueError("agent.u_desired must be a finite 2D vector")
    if c.shape != (2,) or not np.all(np.isfinite(c)):
        raise ValueError("obstacle.center must be a finite 2D vector")
    if not np.isfinite(obstacle.radius) or float(obstacle.radius) <= 0.0:
        raise ValueError("obstacle.radius must satisfy r > 0")
    if not np.isfinite(alpha) or float(alpha) < 0.0:
        raise ValueError("alpha must satisfy alpha >= 0")
    if not np.isfinite(u_max) or float(u_max) <= 0.0:
        raise ValueError("u_max must satisfy u_max > 0")
    if epsilon is not None:
        if not np.isfinite(epsilon) or float(epsilon) < 0.0:
            raise ValueError("epsilon must satisfy epsilon >= 0")
    if require_dynamics_model and not DYNAMICS_MODEL_ID:
        raise ValueError("dynamics model must be declared")
    if require_observation_model and not OBSERVATION_MODEL_ID:
        raise ValueError("observation model must be declared")


def barrier_value(position: np.ndarray, obstacle: CircularObstacle) -> float:
    """h(p) = ||p - c||^2 - r^2  (safe when h >= 0)."""

    p = np.asarray(position, dtype=np.float64).reshape(2)
    c = np.asarray(obstacle.center, dtype=np.float64).reshape(2)
    return float(np.dot(p - c, p - c) - obstacle.radius**2)


def cbf_affine_constraint(
    position: np.ndarray,
    obstacle: CircularObstacle,
    *,
    alpha: float,
) -> tuple[np.ndarray, float]:
    """Affine CBF inequality: a·u >= b  for single integrator p_dot = u.

    h_dot = 2(p-c)·u, require h_dot + α h >= 0 ⇒ 2(p-c)·u >= -α h.
    """

    p = np.asarray(position, dtype=np.float64).reshape(2)
    c = np.asarray(obstacle.center, dtype=np.float64).reshape(2)
    h = barrier_value(p, obstacle)
    a = 2.0 * (p - c)
    b = -float(alpha) * h
    return a, b


def _public_solver_provenance(solver: Literal["CLARABEL", "SCS"]) -> SolverProvenance:
    version: str | None = None
    try:
        if solver == "CLARABEL":
            import clarabel  # type: ignore[import-untyped]

            version = getattr(clarabel, "__version__", None)
        else:
            import scs  # type: ignore[import-untyped]

            version = getattr(scs, "__version__", None)
    except Exception:  # noqa: BLE001
        version = None
    return SolverProvenance(
        backend_id=f"public_cvxpy_{solver.lower()}",
        solver_name=solver,
        solver_version=version,
        package_distribution="cvxpy",
        package_version=_cvxpy_version(),
        package_source="pypi",
        algorithm="qp" if solver == "CLARABEL" else "scs",
        settings={"role": "primary" if solver == "CLARABEL" else "secondary"},
        platform_note="Clarabel primary + SCS secondary public refs",
    )


def _cvxpy_version() -> str | None:
    try:
        import cvxpy as cp

        return getattr(cp, "__version__", None)
    except Exception:  # noqa: BLE001
        return None


def _unavailable_moreau_provenance() -> SolverProvenance:
    return SolverProvenance(
        backend_id="moreau_cbf_filter",
        solver_name="MOREAU",
        solver_version=None,
        package_distribution="moreau",
        package_version=None,
        package_source=None,
        platform_note="Moreau CBF path explicitly unavailable on this host (not a comparison baseline)",
    )


def _moreau_cbf_live() -> tuple[bool, str]:
    """Return (live, reason). Live only when native Moreau is executable for CBF."""

    import sys

    if sys.platform.startswith("win"):
        return False, "moreau_unsupported_on_native_windows"
    try:
        from conicshield.backends.base import Backend
        from conicshield.backends.capabilities import discover_moreau_family

        caps = discover_moreau_family(backend=Backend.NATIVE_MOREAU, run_license_check=False)
        if not caps.package_importable or not caps.native_compiled_api:
            return False, "moreau_native_compiled_api_unavailable"
        # CBF is not yet encoded onto CompiledSolver shield templates in research.
        return False, "moreau_cbf_encoder_not_wired"
    except Exception as exc:  # noqa: BLE001
        return False, f"moreau_probe_failed:{type(exc).__name__}"


def _map_status(raw: str) -> CanonicalSolverStatus:
    s = raw.lower()
    if "optimal" in s:
        return CanonicalSolverStatus.OPTIMAL
    if "infeas" in s:
        return CanonicalSolverStatus.INFEASIBLE
    if "iter" in s:
        return CanonicalSolverStatus.ITERATION_LIMIT
    if "time" in s:
        return CanonicalSolverStatus.TIME_LIMIT
    if "unavailable" in s:
        return CanonicalSolverStatus.UNAVAILABLE
    if "error" in s or "numeric" in s:
        return CanonicalSolverStatus.NUMERICAL_FAILURE
    return CanonicalSolverStatus.UNKNOWN


def verify_cbf_candidate(
    u_safe: np.ndarray,
    *,
    u_des: np.ndarray,
    a: np.ndarray,
    b: float,
    u_max: float,
    solver_status: str,
    solver_provenance: SolverProvenance,
    two_eps: float | None = None,
    b_rob: float | None = None,
    residual_tol: float = _RESIDUAL_TOL,
    observation_model_id: str = OBSERVATION_MODEL_ID,
) -> CBFVerificationReport:
    """Independently recompute residuals and decide release (never value-only)."""

    uv = np.asarray(u_safe, dtype=np.float64).reshape(-1)
    finite = bool(uv.shape == (2,) and np.all(np.isfinite(uv)))
    notes: list[str] = []
    if not finite:
        notes.append("nonfinite_candidate")
        return CBFVerificationReport(
            finite_value=False,
            norm_bound_residual=float("nan"),
            cbf_residual=float("nan"),
            robust_soc_residual=float("nan") if two_eps is not None else None,
            solver_status=solver_status,
            canonical_status=_map_status(solver_status),
            release_decision=ReleaseDecision.REJECT,
            active_constraints=(),
            solver_provenance=solver_provenance,
            passed=False,
            residual_tolerance=residual_tol,
            notes=tuple(notes),
            observation_model_id=observation_model_id,
        )

    norm_u = float(np.linalg.norm(uv))
    norm_bound_residual = max(0.0, norm_u - float(u_max))
    cbf_residual = max(0.0, float(b) - float(a @ uv))
    robust_soc_residual: float | None = None
    if two_eps is not None and b_rob is not None:
        robust_soc_residual = max(
            0.0,
            float(b_rob) - (float(a @ uv) - float(two_eps) * norm_u),
        )

    active: list[str] = []
    if two_eps is not None and b_rob is not None:
        slack = float(a @ uv) - float(two_eps) * norm_u - float(b_rob)
        if slack <= _ACTIVE_TOL:
            active.append("cbf_soc_robust")
    else:
        if float(a @ uv - b) <= _ACTIVE_TOL:
            active.append("cbf")
    if abs(norm_u - float(u_max)) <= 1e-5:
        active.append("u_max")

    canonical = _map_status(solver_status)
    residuals_ok = (
        norm_bound_residual <= residual_tol
        and cbf_residual <= residual_tol
        and (robust_soc_residual is None or robust_soc_residual <= residual_tol)
    )
    status_ok = canonical is CanonicalSolverStatus.OPTIMAL
    if not residuals_ok:
        notes.append("residual_gate_failed")
    if not status_ok:
        notes.append("status_gate_failed")
    # Research domain: verified feasible → experimental_only (never production approve).
    if finite and residuals_ok and status_ok:
        decision = ReleaseDecision.EXPERIMENTAL_ONLY
        passed = True
    elif canonical is CanonicalSolverStatus.UNAVAILABLE:
        decision = ReleaseDecision.FALLBACK
        passed = False
        notes.append("backend_unavailable")
    else:
        decision = ReleaseDecision.REJECT
        passed = False
        notes.append("cvxpy_value_alone_insufficient")

    # Silence unused; kept for future objective checks / API symmetry.
    _ = u_des

    return CBFVerificationReport(
        finite_value=True,
        norm_bound_residual=float(norm_bound_residual),
        cbf_residual=float(cbf_residual),
        robust_soc_residual=robust_soc_residual,
        solver_status=solver_status,
        canonical_status=canonical,
        release_decision=decision,
        active_constraints=tuple(active),
        solver_provenance=solver_provenance,
        passed=passed,
        residual_tolerance=residual_tol,
        notes=tuple(notes),
        observation_model_id=observation_model_id,
    )


def _solve_nominal_cbf_qp(
    *,
    u_des: np.ndarray,
    a: np.ndarray,
    b: float,
    u_max: float,
    solver: Literal["CLARABEL", "SCS"] = "CLARABEL",
) -> tuple[np.ndarray, str, float | None]:
    import time

    import cvxpy as cp

    u = cp.Variable(2)
    cons = [a @ u >= b, cp.norm(u, 2) <= float(u_max)]
    prob = cp.Problem(cp.Minimize(cp.sum_squares(u - u_des)), cons)
    t0 = time.perf_counter()
    try:
        prob.solve(solver=getattr(cp, solver), verbose=False)
        status = str(prob.status)
    except Exception as exc:  # noqa: BLE001
        return np.full(2, np.nan), f"error:{type(exc).__name__}", time.perf_counter() - t0
    elapsed = time.perf_counter() - t0
    if u.value is None:
        return np.full(2, np.nan), status, elapsed
    return np.asarray(u.value, dtype=np.float64).reshape(2), status, elapsed


def _solve_soc_robust_cbf_qp(
    *,
    u_des: np.ndarray,
    a: np.ndarray,
    b_rob: float,
    two_eps: float,
    u_max: float,
    solver: Literal["CLARABEL", "SCS"] = "CLARABEL",
) -> tuple[np.ndarray, str, float | None]:
    import time

    import cvxpy as cp

    u = cp.Variable(2)
    if two_eps <= 0.0:
        cons = [a @ u >= float(b_rob), cp.norm(u, 2) <= float(u_max)]
    else:
        t = cp.Variable(nonneg=True)
        cons = [
            a @ u - t >= float(b_rob),
            cp.norm(u, 2) * float(two_eps) <= t,
            cp.norm(u, 2) <= float(u_max),
        ]
    prob = cp.Problem(cp.Minimize(cp.sum_squares(u - u_des)), cons)
    t0 = time.perf_counter()
    try:
        prob.solve(solver=getattr(cp, solver), verbose=False)
        status = str(prob.status)
    except Exception as exc:  # noqa: BLE001
        return np.full(2, np.nan), f"error:{type(exc).__name__}", time.perf_counter() - t0
    elapsed = time.perf_counter() - t0
    if u.value is None:
        return np.full(2, np.nan), status, elapsed
    return np.asarray(u.value, dtype=np.float64).reshape(2), status, elapsed


def _unavailable_baseline_result(
    agent: AgentState2D,
    *,
    h: float,
    u_des: np.ndarray,
    baseline_s: str,
    stage: str,
    reason: str,
    epsilon: float | None = None,
) -> CBFFilterResult:
    """Explicitly unavailable baseline — not a NaN comparison stub."""

    provenance = (
        _unavailable_moreau_provenance()
        if baseline_s == CBFBaseline.MOREAU_FILTER.value
        else SolverProvenance(
            backend_id="cbf_baseline_unavailable",
            solver_name=baseline_s,
            solver_version=None,
            package_distribution=None,
            package_version=None,
        )
    )
    verification = CBFVerificationReport(
        finite_value=False,
        norm_bound_residual=float("nan"),
        cbf_residual=float("nan"),
        robust_soc_residual=None,
        solver_status="unavailable",
        canonical_status=CanonicalSolverStatus.UNAVAILABLE,
        release_decision=ReleaseDecision.FALLBACK,
        active_constraints=(),
        solver_provenance=provenance,
        passed=False,
        notes=("baseline_explicitly_unavailable", "not_a_comparison_baseline"),
    )
    meta: dict[str, Any] = {
        "unavailable": True,
        "comparison_baseline": False,
        "reason": reason,
        "dynamics_model_id": DYNAMICS_MODEL_ID,
        "observation_model_id": OBSERVATION_MODEL_ID,
    }
    if epsilon is not None:
        meta["epsilon"] = epsilon
        meta["uncertainty_model_id"] = UNCERTAINTY_MODEL_ID
    return CBFFilterResult(
        agent_id=agent.agent_id,
        u_safe=np.full(2, np.nan),
        u_desired=u_des,
        intervened=False,
        intervention_norm=float("nan"),
        barrier_value=h,
        safety_margin=float("nan"),
        active_constraints=(),
        solver_status="unavailable",
        canonical_status=CanonicalSolverStatus.UNAVAILABLE,
        baseline=baseline_s,
        stage=stage,
        fallback=True,
        metadata=meta,
        verification=verification,
        release_decision=ReleaseDecision.FALLBACK,
    )


def apply_cbf_filter(
    agent: AgentState2D,
    obstacle: CircularObstacle,
    *,
    alpha: float = 1.0,
    u_max: float = 1.0,
    baseline: CBFBaseline | str = CBFBaseline.PUBLIC_SOLVER_FILTER,
    solver: Literal["CLARABEL", "SCS"] = "CLARABEL",
) -> CBFFilterResult:
    """Stage-1 nominal affine CBF QP (or baseline variants)."""

    validate_cbf_inputs(agent, obstacle, alpha=alpha, u_max=u_max)
    baseline_s = str(baseline)
    h = barrier_value(agent.position, obstacle)
    u_des = np.asarray(agent.u_desired, dtype=np.float64).reshape(2)

    if baseline_s == CBFBaseline.NO_FILTER.value:
        a, b = cbf_affine_constraint(agent.position, obstacle, alpha=alpha)
        provenance = SolverProvenance(
            backend_id="no_filter",
            solver_name="none",
            solver_version=None,
            package_distribution=None,
            package_version=None,
        )
        verification = verify_cbf_candidate(
            u_des,
            u_des=u_des,
            a=a,
            b=b,
            u_max=u_max,
            solver_status="no_filter",
            solver_provenance=provenance,
        )
        # no_filter is not a solver release — keep experimental_only only if residuals pass,
        # else still surface residual failure without pretending solver success.
        if verification.passed:
            verification = CBFVerificationReport(
                finite_value=verification.finite_value,
                norm_bound_residual=verification.norm_bound_residual,
                cbf_residual=verification.cbf_residual,
                robust_soc_residual=None,
                solver_status="no_filter",
                canonical_status=CanonicalSolverStatus.OPTIMAL,
                release_decision=ReleaseDecision.EXPERIMENTAL_ONLY,
                active_constraints=verification.active_constraints,
                solver_provenance=provenance,
                passed=True,
                residual_tolerance=verification.residual_tolerance,
                notes=("no_filter_passthrough",),
            )
        return CBFFilterResult(
            agent_id=agent.agent_id,
            u_safe=u_des.copy(),
            u_desired=u_des,
            intervened=False,
            intervention_norm=0.0,
            barrier_value=h,
            safety_margin=h,
            active_constraints=verification.active_constraints,
            solver_status="no_filter",
            canonical_status=CanonicalSolverStatus.OPTIMAL,
            baseline=baseline_s,
            stage=CBFStage.STAGE1_NOMINAL.value,
            metadata={
                "alpha": alpha,
                "u_max": u_max,
                "dynamics_model_id": DYNAMICS_MODEL_ID,
                "observation_model_id": OBSERVATION_MODEL_ID,
            },
            verification=verification,
            release_decision=verification.release_decision,
        )

    if baseline_s == CBFBaseline.MOREAU_FILTER.value:
        live, reason = _moreau_cbf_live()
        if not live:
            return _unavailable_baseline_result(
                agent,
                h=h,
                u_des=u_des,
                baseline_s=baseline_s,
                stage=CBFStage.STAGE1_NOMINAL.value,
                reason=reason,
            )
        # Reserved for future live Moreau CBF encoder.
        return _unavailable_baseline_result(
            agent,
            h=h,
            u_des=u_des,
            baseline_s=baseline_s,
            stage=CBFStage.STAGE1_NOMINAL.value,
            reason="moreau_cbf_encoder_not_wired",
        )

    if baseline_s == CBFBaseline.EXACT_VS_SMOOTHED.value:
        return _unavailable_baseline_result(
            agent,
            h=h,
            u_des=u_des,
            baseline_s=baseline_s,
            stage=CBFStage.STAGE1_NOMINAL.value,
            reason="exact/smoothed differentiable filter baseline not wired for CBF",
        )

    a, b = cbf_affine_constraint(agent.position, obstacle, alpha=alpha)
    u_safe, status, elapsed = _solve_nominal_cbf_qp(
        u_des=u_des, a=a, b=b, u_max=u_max, solver=solver
    )
    provenance = _public_solver_provenance(solver)
    verification = verify_cbf_candidate(
        u_safe,
        u_des=u_des,
        a=a,
        b=b,
        u_max=u_max,
        solver_status=status,
        solver_provenance=provenance,
    )
    p = np.asarray(agent.position, dtype=np.float64).reshape(2)
    c = np.asarray(obstacle.center, dtype=np.float64).reshape(2)
    if np.all(np.isfinite(u_safe)):
        hdot = float(2.0 * np.dot(p - c, u_safe))
        margin = hdot + float(alpha) * h
    else:
        margin = float("nan")
    diff = float(np.linalg.norm(u_safe - u_des)) if np.all(np.isfinite(u_safe)) else float("nan")
    return CBFFilterResult(
        agent_id=agent.agent_id,
        u_safe=u_safe,
        u_desired=u_des,
        intervened=bool(np.isfinite(diff) and diff > 1e-8),
        intervention_norm=diff,
        barrier_value=h,
        safety_margin=margin,
        active_constraints=verification.active_constraints,
        solver_status=status,
        canonical_status=verification.canonical_status,
        baseline=baseline_s,
        stage=CBFStage.STAGE1_NOMINAL.value,
        solve_time_sec=elapsed,
        metadata={
            "alpha": alpha,
            "u_max": u_max,
            "solver": solver,
            "dynamics_model_id": DYNAMICS_MODEL_ID,
            "observation_model_id": OBSERVATION_MODEL_ID,
            "solver_role": "primary" if solver == "CLARABEL" else "secondary",
        },
        verification=verification,
        release_decision=verification.release_decision,
    )


def apply_cbf_filter_batch(
    agents: list[AgentState2D],
    obstacles: list[CircularObstacle],
    *,
    alpha: float = 1.0,
    u_max: float = 1.0,
    baseline: CBFBaseline | str = CBFBaseline.PUBLIC_SOLVER_FILTER,
    solver: Literal["CLARABEL", "SCS"] = "CLARABEL",
    shadow: bool = False,
    epsilon: float | None = None,
    assert_matches_sequential: bool = True,
) -> list[CBFFilterResult]:
    """True compiled joint batch when topology permits (R13).

    Independent agents sharing (alpha, u_max, baseline, solver, epsilon mode) are
    solved as one joint CVXPY problem. Sequential Python loops are never labeled
    as compiled batch without the sequential watermark.
    """

    if len(agents) != len(obstacles):
        raise ValueError("agents and obstacles must be paired 1:1")
    if not agents:
        return []

    baseline_s = str(baseline)
    for agent, obs in zip(agents, obstacles, strict=True):
        validate_cbf_inputs(
            agent,
            obs,
            alpha=alpha,
            u_max=u_max,
            epsilon=epsilon,
            require_observation_model=epsilon is not None,
        )

    topology_ok = baseline_s in {
        CBFBaseline.PUBLIC_SOLVER_FILTER.value,
        CBFBaseline.PRIMARY_PLUS_SHADOW.value,
    }
    if not topology_ok or baseline_s in {
        CBFBaseline.MOREAU_FILTER.value,
        CBFBaseline.EXACT_VS_SMOOTHED.value,
        CBFBaseline.NO_FILTER.value,
    }:
        # Fall back to sequential with explicit watermark (not claimed as compiled batch).
        return apply_cbf_filter_batched(
            agents,
            obstacles,
            alpha=alpha,
            u_max=u_max,
            baseline=baseline,
            solver=solver,
            shadow=shadow,
            epsilon=epsilon,
        )

    if epsilon is None:
        results = _solve_nominal_compiled_batch(
            agents, obstacles, alpha=alpha, u_max=u_max, solver=solver
        )
    else:
        results = _solve_soc_compiled_batch(
            agents,
            obstacles,
            alpha=alpha,
            u_max=u_max,
            epsilon=float(epsilon),
            solver=solver,
        )

    for r in results:
        r.stage = CBFStage.STAGE2_BATCHED.value
        r.metadata["batch_mode"] = BATCH_MODE_COMPILED
        r.metadata["batch_emulation"] = BATCH_MODE_COMPILED
        r.metadata["dynamics_model_id"] = DYNAMICS_MODEL_ID
        r.metadata["observation_model_id"] = OBSERVATION_MODEL_ID

    if shadow:
        other: Literal["CLARABEL", "SCS"] = "SCS" if solver == "CLARABEL" else "CLARABEL"
        if epsilon is None:
            shadows = _solve_nominal_compiled_batch(
                agents, obstacles, alpha=alpha, u_max=u_max, solver=other
            )
        else:
            shadows = _solve_soc_compiled_batch(
                agents,
                obstacles,
                alpha=alpha,
                u_max=u_max,
                epsilon=float(epsilon),
                solver=other,
            )
        for primary, sh in zip(results, shadows, strict=True):
            primary.metadata["shadow"] = sh.as_dict()
            if np.all(np.isfinite(primary.u_safe)) and np.all(np.isfinite(sh.u_safe)):
                primary.metadata["shadow_disagreement_l2"] = float(
                    np.linalg.norm(primary.u_safe - sh.u_safe)
                )
            primary.baseline = CBFBaseline.PRIMARY_PLUS_SHADOW.value
            primary.metadata["primary_solver"] = solver
            primary.metadata["secondary_solver"] = other

    if assert_matches_sequential and results:
        seq = apply_cbf_filter_batched(
            agents,
            obstacles,
            alpha=alpha,
            u_max=u_max,
            baseline=CBFBaseline.PUBLIC_SOLVER_FILTER,
            solver=solver,
            shadow=False,
            epsilon=epsilon,
            _watermark_only=True,
        )
        for i, (b_row, s_row) in enumerate(zip(results, seq, strict=True)):
            if not (np.all(np.isfinite(b_row.u_safe)) and np.all(np.isfinite(s_row.u_safe))):
                continue
            if float(np.linalg.norm(b_row.u_safe - s_row.u_safe)) > 1e-4:
                raise AssertionError(
                    f"batch≢sequential at row {i}: "
                    f"batch={b_row.u_safe.tolist()} seq={s_row.u_safe.tolist()}"
                )
            b_row.metadata["batch_equals_sequential"] = True

    return results


def apply_cbf_filter_batched(
    agents: list[AgentState2D],
    obstacles: list[CircularObstacle],
    *,
    alpha: float = 1.0,
    u_max: float = 1.0,
    baseline: CBFBaseline | str = CBFBaseline.PUBLIC_SOLVER_FILTER,
    solver: Literal["CLARABEL", "SCS"] = "CLARABEL",
    shadow: bool = False,
    epsilon: float | None = None,
    _watermark_only: bool = False,
) -> list[CBFFilterResult]:
    """Sequential research batch with explicit watermark (not compiled batch).

    Prefer ``apply_cbf_filter_batch`` for topology-matched compiled joint solves.
    """

    if len(agents) != len(obstacles):
        raise ValueError("agents and obstacles must be paired 1:1 for stage-2 scaffold")
    results: list[CBFFilterResult] = []
    for agent, obs in zip(agents, obstacles, strict=True):
        if epsilon is None:
            primary = apply_cbf_filter(
                agent, obs, alpha=alpha, u_max=u_max, baseline=baseline, solver=solver
            )
        else:
            primary = apply_cbf_filter_soc_robust(
                agent,
                obs,
                alpha=alpha,
                u_max=u_max,
                epsilon=float(epsilon),
                baseline=baseline,
                solver=solver,
            )
        primary.stage = CBFStage.STAGE2_BATCHED.value
        primary.metadata["batch_emulation"] = BATCH_MODE_SEQUENTIAL
        primary.metadata["batch_mode"] = BATCH_MODE_SEQUENTIAL
        primary.metadata[BATCH_EMULATION_WATERMARK] = True
        if not _watermark_only:
            primary.metadata["watermark"] = BATCH_EMULATION_WATERMARK
        if shadow and str(baseline) in {
            CBFBaseline.PUBLIC_SOLVER_FILTER.value,
            CBFBaseline.PRIMARY_PLUS_SHADOW.value,
        }:
            other: Literal["CLARABEL", "SCS"] = "SCS" if solver == "CLARABEL" else "CLARABEL"
            if epsilon is None:
                shadow_res = apply_cbf_filter(
                    agent,
                    obs,
                    alpha=alpha,
                    u_max=u_max,
                    baseline=CBFBaseline.PUBLIC_SOLVER_FILTER,
                    solver=other,
                )
            else:
                shadow_res = apply_cbf_filter_soc_robust(
                    agent,
                    obs,
                    alpha=alpha,
                    u_max=u_max,
                    epsilon=float(epsilon),
                    baseline=CBFBaseline.PUBLIC_SOLVER_FILTER,
                    solver=other,
                )
            primary.metadata["shadow"] = shadow_res.as_dict()
            if np.all(np.isfinite(primary.u_safe)) and np.all(np.isfinite(shadow_res.u_safe)):
                primary.metadata["shadow_disagreement_l2"] = float(
                    np.linalg.norm(primary.u_safe - shadow_res.u_safe)
                )
            primary.baseline = CBFBaseline.PRIMARY_PLUS_SHADOW.value
        results.append(primary)
    return results


def _solve_nominal_compiled_batch(
    agents: list[AgentState2D],
    obstacles: list[CircularObstacle],
    *,
    alpha: float,
    u_max: float,
    solver: Literal["CLARABEL", "SCS"],
) -> list[CBFFilterResult]:
    import time

    import cvxpy as cp

    n = len(agents)
    u_des = np.vstack([np.asarray(a.u_desired, dtype=np.float64).reshape(2) for a in agents])
    a_rows = np.zeros((n, 2), dtype=np.float64)
    b_vals = np.zeros(n, dtype=np.float64)
    hs = np.zeros(n, dtype=np.float64)
    for i, (agent, obs) in enumerate(zip(agents, obstacles, strict=True)):
        a_i, b_i = cbf_affine_constraint(agent.position, obs, alpha=alpha)
        a_rows[i] = a_i
        b_vals[i] = b_i
        hs[i] = barrier_value(agent.position, obs)

    u = cp.Variable((n, 2))
    cons = []
    for i in range(n):
        cons.append(a_rows[i] @ u[i] >= float(b_vals[i]))
        cons.append(cp.norm(u[i], 2) <= float(u_max))
    prob = cp.Problem(cp.Minimize(cp.sum_squares(u - u_des)), cons)
    t0 = time.perf_counter()
    try:
        prob.solve(solver=getattr(cp, solver), verbose=False)
        status = str(prob.status)
    except Exception as exc:  # noqa: BLE001
        status = f"error:{type(exc).__name__}"
        u_val = np.full((n, 2), np.nan)
        elapsed = time.perf_counter() - t0
        return [
            _row_from_batch_values(
                agents[i],
                obstacles[i],
                u_safe=u_val[i],
                u_des=u_des[i],
                a=a_rows[i],
                b=float(b_vals[i]),
                h=float(hs[i]),
                alpha=alpha,
                u_max=u_max,
                status=status,
                elapsed=elapsed / max(n, 1),
                solver=solver,
                robust=False,
            )
            for i in range(n)
        ]
    elapsed = time.perf_counter() - t0
    if u.value is None:
        u_val = np.full((n, 2), np.nan)
    else:
        u_val = np.asarray(u.value, dtype=np.float64).reshape(n, 2)
    return [
        _row_from_batch_values(
            agents[i],
            obstacles[i],
            u_safe=u_val[i],
            u_des=u_des[i],
            a=a_rows[i],
            b=float(b_vals[i]),
            h=float(hs[i]),
            alpha=alpha,
            u_max=u_max,
            status=status,
            elapsed=elapsed / max(n, 1),
            solver=solver,
            robust=False,
        )
        for i in range(n)
    ]


def _solve_soc_compiled_batch(
    agents: list[AgentState2D],
    obstacles: list[CircularObstacle],
    *,
    alpha: float,
    u_max: float,
    epsilon: float,
    solver: Literal["CLARABEL", "SCS"],
) -> list[CBFFilterResult]:
    import time

    import cvxpy as cp

    n = len(agents)
    u_des = np.vstack([np.asarray(a.u_desired, dtype=np.float64).reshape(2) for a in agents])
    a_rows = np.zeros((n, 2), dtype=np.float64)
    b_robs = np.zeros(n, dtype=np.float64)
    two_eps_vals = np.zeros(n, dtype=np.float64)
    hs = np.zeros(n, dtype=np.float64)
    for i, (agent, obs) in enumerate(zip(agents, obstacles, strict=True)):
        a_i, b_rob, two_eps = robust_cbf_soc_constants(
            agent.position, obs, alpha=alpha, epsilon=epsilon
        )
        a_rows[i] = a_i
        b_robs[i] = b_rob
        two_eps_vals[i] = two_eps
        hs[i] = barrier_value(agent.position, obs)

    u = cp.Variable((n, 2))
    cons = []
    for i in range(n):
        if float(two_eps_vals[i]) <= 0.0:
            cons.append(a_rows[i] @ u[i] >= float(b_robs[i]))
        else:
            t_i = cp.Variable(nonneg=True)
            cons.append(a_rows[i] @ u[i] - t_i >= float(b_robs[i]))
            cons.append(cp.norm(u[i], 2) * float(two_eps_vals[i]) <= t_i)
        cons.append(cp.norm(u[i], 2) <= float(u_max))
    prob = cp.Problem(cp.Minimize(cp.sum_squares(u - u_des)), cons)
    t0 = time.perf_counter()
    try:
        prob.solve(solver=getattr(cp, solver), verbose=False)
        status = str(prob.status)
    except Exception as exc:  # noqa: BLE001
        status = f"error:{type(exc).__name__}"
        u_val = np.full((n, 2), np.nan)
        elapsed = time.perf_counter() - t0
        return [
            _row_from_batch_values(
                agents[i],
                obstacles[i],
                u_safe=u_val[i],
                u_des=u_des[i],
                a=a_rows[i],
                b=float(b_robs[i]),
                h=float(hs[i]),
                alpha=alpha,
                u_max=u_max,
                status=status,
                elapsed=elapsed / max(n, 1),
                solver=solver,
                robust=True,
                two_eps=float(two_eps_vals[i]),
                b_rob=float(b_robs[i]),
                epsilon=epsilon,
            )
            for i in range(n)
        ]
    elapsed = time.perf_counter() - t0
    if u.value is None:
        u_val = np.full((n, 2), np.nan)
    else:
        u_val = np.asarray(u.value, dtype=np.float64).reshape(n, 2)
    return [
        _row_from_batch_values(
            agents[i],
            obstacles[i],
            u_safe=u_val[i],
            u_des=u_des[i],
            a=a_rows[i],
            b=float(b_robs[i]),
            h=float(hs[i]),
            alpha=alpha,
            u_max=u_max,
            status=status,
            elapsed=elapsed / max(n, 1),
            solver=solver,
            robust=True,
            two_eps=float(two_eps_vals[i]),
            b_rob=float(b_robs[i]),
            epsilon=epsilon,
        )
        for i in range(n)
    ]


def _row_from_batch_values(
    agent: AgentState2D,
    obstacle: CircularObstacle,
    *,
    u_safe: np.ndarray,
    u_des: np.ndarray,
    a: np.ndarray,
    b: float,
    h: float,
    alpha: float,
    u_max: float,
    status: str,
    elapsed: float,
    solver: Literal["CLARABEL", "SCS"],
    robust: bool,
    two_eps: float | None = None,
    b_rob: float | None = None,
    epsilon: float | None = None,
) -> CBFFilterResult:
    provenance = _public_solver_provenance(solver)
    a_nom, b_nom = cbf_affine_constraint(agent.position, obstacle, alpha=alpha)
    verification = verify_cbf_candidate(
        u_safe,
        u_des=u_des,
        a=a_nom,
        b=b_nom,
        u_max=u_max,
        solver_status=status,
        solver_provenance=provenance,
        two_eps=two_eps if robust else None,
        b_rob=b_rob if robust else None,
    )
    p = np.asarray(agent.position, dtype=np.float64).reshape(2)
    c = np.asarray(obstacle.center, dtype=np.float64).reshape(2)
    if np.all(np.isfinite(u_safe)):
        if robust and two_eps is not None and b_rob is not None:
            margin = float(a @ u_safe - two_eps * np.linalg.norm(u_safe) - b_rob)
            nominal_margin = float(2.0 * np.dot(p - c, u_safe) + float(alpha) * h)
        else:
            margin = float(2.0 * np.dot(p - c, u_safe) + float(alpha) * h)
            nominal_margin = margin
    else:
        margin = float("nan")
        nominal_margin = float("nan")
    diff = float(np.linalg.norm(u_safe - u_des)) if np.all(np.isfinite(u_safe)) else float("nan")
    meta: dict[str, Any] = {
        "alpha": alpha,
        "u_max": u_max,
        "solver": solver,
        "dynamics_model_id": DYNAMICS_MODEL_ID,
        "observation_model_id": OBSERVATION_MODEL_ID,
        "solver_role": "primary" if solver == "CLARABEL" else "secondary",
        "nominal_lie_margin": nominal_margin,
    }
    if robust:
        meta["epsilon"] = epsilon
        meta["uncertainty_model_id"] = UNCERTAINTY_MODEL_ID
        meta["robust_margin"] = margin
        meta["b_rob"] = b_rob
    return CBFFilterResult(
        agent_id=agent.agent_id,
        u_safe=np.asarray(u_safe, dtype=np.float64).reshape(2),
        u_desired=np.asarray(u_des, dtype=np.float64).reshape(2),
        intervened=bool(np.isfinite(diff) and diff > 1e-8),
        intervention_norm=diff,
        barrier_value=h,
        safety_margin=margin,
        active_constraints=verification.active_constraints,
        solver_status=status,
        canonical_status=verification.canonical_status,
        baseline=CBFBaseline.PUBLIC_SOLVER_FILTER.value,
        stage=CBFStage.STAGE2_BATCHED.value,
        solve_time_sec=elapsed,
        metadata=meta,
        verification=verification,
        release_decision=verification.release_decision,
    )


def robust_cbf_soc_constants(
    position: np.ndarray,
    obstacle: CircularObstacle,
    *,
    alpha: float,
    epsilon: float,
) -> tuple[np.ndarray, float, float]:
    """Return (a, b_rob, two_eps) for the conservative SOC robust CBF constraint."""

    if epsilon < 0.0:
        raise ValueError("epsilon must be >= 0")
    p = np.asarray(position, dtype=np.float64).reshape(2)
    c = np.asarray(obstacle.center, dtype=np.float64).reshape(2)
    h = barrier_value(p, obstacle)
    a = 2.0 * (p - c)
    dist = float(np.linalg.norm(p - c))
    # a·u - 2ε||u|| >= -α h + α(2ε||p-c|| + ε^2)
    b_rob = -float(alpha) * h + float(alpha) * (2.0 * float(epsilon) * dist + float(epsilon) ** 2)
    return a, b_rob, 2.0 * float(epsilon)


def apply_cbf_filter_soc_robust(
    agent: AgentState2D,
    obstacle: CircularObstacle,
    *,
    alpha: float = 1.0,
    u_max: float = 1.0,
    epsilon: float = 0.05,
    baseline: CBFBaseline | str = CBFBaseline.PUBLIC_SOLVER_FILTER,
    solver: Literal["CLARABEL", "SCS"] = "CLARABEL",
) -> CBFFilterResult:
    """Stage-3 SOC robust margin under ``UNCERTAINTY_MODEL_ID``."""

    validate_cbf_inputs(
        agent,
        obstacle,
        alpha=alpha,
        u_max=u_max,
        epsilon=epsilon,
        require_observation_model=True,
    )
    baseline_s = str(baseline)
    h = barrier_value(agent.position, obstacle)
    u_des = np.asarray(agent.u_desired, dtype=np.float64).reshape(2)
    if baseline_s == CBFBaseline.NO_FILTER.value:
        return CBFFilterResult(
            agent_id=agent.agent_id,
            u_safe=u_des.copy(),
            u_desired=u_des,
            intervened=False,
            intervention_norm=0.0,
            barrier_value=h,
            safety_margin=h,
            active_constraints=(),
            solver_status="no_filter",
            canonical_status=CanonicalSolverStatus.OPTIMAL,
            baseline=baseline_s,
            stage=CBFStage.STAGE3_SOC_ROBUST.value,
            metadata={
                "epsilon": epsilon,
                "uncertainty_model_id": UNCERTAINTY_MODEL_ID,
                "dynamics_model_id": DYNAMICS_MODEL_ID,
                "observation_model_id": OBSERVATION_MODEL_ID,
            },
            release_decision=ReleaseDecision.EXPERIMENTAL_ONLY,
        )

    if baseline_s == CBFBaseline.MOREAU_FILTER.value:
        live, reason = _moreau_cbf_live()
        return _unavailable_baseline_result(
            agent,
            h=h,
            u_des=u_des,
            baseline_s=baseline_s,
            stage=CBFStage.STAGE3_SOC_ROBUST.value,
            reason=reason if not live else "moreau_cbf_encoder_not_wired",
            epsilon=epsilon,
        )

    if baseline_s == CBFBaseline.EXACT_VS_SMOOTHED.value:
        return _unavailable_baseline_result(
            agent,
            h=h,
            u_des=u_des,
            baseline_s=baseline_s,
            stage=CBFStage.STAGE3_SOC_ROBUST.value,
            reason="exact/smoothed differentiable filter baseline not wired for CBF",
            epsilon=epsilon,
        )

    a, b_rob, two_eps = robust_cbf_soc_constants(
        agent.position, obstacle, alpha=alpha, epsilon=epsilon
    )
    a_nom, b_nom = cbf_affine_constraint(agent.position, obstacle, alpha=alpha)
    u_safe, status, elapsed = _solve_soc_robust_cbf_qp(
        u_des=u_des, a=a, b_rob=b_rob, two_eps=two_eps, u_max=u_max, solver=solver
    )
    provenance = _public_solver_provenance(solver)
    verification = verify_cbf_candidate(
        u_safe,
        u_des=u_des,
        a=a_nom,
        b=b_nom,
        u_max=u_max,
        solver_status=status,
        solver_provenance=provenance,
        two_eps=two_eps,
        b_rob=b_rob,
    )
    p = np.asarray(agent.position, dtype=np.float64).reshape(2)
    c = np.asarray(obstacle.center, dtype=np.float64).reshape(2)
    if np.all(np.isfinite(u_safe)):
        hdot = float(2.0 * np.dot(p - c, u_safe))
        nominal_margin = hdot + float(alpha) * h
        robust_margin = float(a @ u_safe - two_eps * np.linalg.norm(u_safe) - b_rob)
    else:
        nominal_margin = float("nan")
        robust_margin = float("nan")
    diff = float(np.linalg.norm(u_safe - u_des)) if np.all(np.isfinite(u_safe)) else float("nan")
    return CBFFilterResult(
        agent_id=agent.agent_id,
        u_safe=u_safe,
        u_desired=u_des,
        intervened=bool(np.isfinite(diff) and diff > 1e-8),
        intervention_norm=diff,
        barrier_value=h,
        safety_margin=robust_margin,
        active_constraints=verification.active_constraints,
        solver_status=status,
        canonical_status=verification.canonical_status,
        baseline=baseline_s,
        stage=CBFStage.STAGE3_SOC_ROBUST.value,
        solve_time_sec=elapsed,
        metadata={
            "alpha": alpha,
            "u_max": u_max,
            "epsilon": epsilon,
            "solver": solver,
            "uncertainty_model_id": UNCERTAINTY_MODEL_ID,
            "dynamics_model_id": DYNAMICS_MODEL_ID,
            "observation_model_id": OBSERVATION_MODEL_ID,
            "nominal_lie_margin": nominal_margin,
            "robust_margin": robust_margin,
            "b_rob": b_rob,
            "solver_role": "primary" if solver == "CLARABEL" else "secondary",
        },
        verification=verification,
        release_decision=verification.release_decision,
    )


def validate_robust_cbf_control(
    agent: AgentState2D,
    obstacle: CircularObstacle,
    u_safe: np.ndarray,
    *,
    alpha: float = 1.0,
    epsilon: float = 0.05,
    u_desired: np.ndarray | None = None,
    soc_declared_margin: float | None = None,
    nominal_intervention_norm: float | None = None,
) -> RobustnessValidationReport:
    """Independently solve worst-case δ on ||δ||_2 ≤ ε and report margins (R13)."""

    validate_cbf_inputs(
        agent,
        obstacle,
        alpha=alpha,
        u_max=1.0 if u_desired is None else max(float(np.linalg.norm(u_desired)), 1e-6),
        epsilon=epsilon,
        require_observation_model=True,
    )
    u = np.asarray(u_safe, dtype=np.float64).reshape(2)
    if not np.all(np.isfinite(u)):
        raise ValueError("u_safe must be finite for robustness validation")
    p = np.asarray(agent.position, dtype=np.float64).reshape(2)
    c = np.asarray(obstacle.center, dtype=np.float64).reshape(2)
    r = float(obstacle.radius)
    u_des = (
        np.asarray(agent.u_desired, dtype=np.float64).reshape(2)
        if u_desired is None
        else np.asarray(u_desired, dtype=np.float64).reshape(2)
    )

    import cvxpy as cp

    delta = cp.Variable(2)
    p_pert = p + delta
    # f(δ) = 2(p+δ-c)·u + α (||p+δ-c||^2 - r^2)
    lie = 2.0 * (p_pert - c) @ u + float(alpha) * (cp.sum_squares(p_pert - c) - r**2)
    prob = cp.Problem(cp.Minimize(lie), [cp.norm(delta, 2) <= float(epsilon)])
    try:
        prob.solve(solver=cp.CLARABEL, verbose=False)
        if delta.value is None or prob.value is None:
            prob.solve(solver=cp.SCS, verbose=False)
    except Exception:  # noqa: BLE001
        prob.solve(solver=cp.SCS, verbose=False)

    if delta.value is None or prob.value is None or not np.isfinite(float(prob.value)):
        raise RuntimeError("worst-case delta solve failed")

    delta_star = np.asarray(delta.value, dtype=np.float64).reshape(2)
    min_actual = float(prob.value)
    objective_cost = float(np.dot(u - u_des, u - u_des))
    intervention = float(np.linalg.norm(u - u_des))
    if nominal_intervention_norm is None:
        intervention_increase = 0.0
    else:
        intervention_increase = max(0.0, intervention - float(nominal_intervention_norm))

    bound_gap: float | None = None
    if soc_declared_margin is not None and np.isfinite(soc_declared_margin):
        # SOC sufficient residual vs true worst-case margin; conservatism ⇒ gap ≥ 0.
        bound_gap = float(min_actual - float(soc_declared_margin))

    holds = bool(min_actual >= -1e-5)
    notes: list[str] = []
    if not holds:
        notes.append("robust_condition_violated")
    if bound_gap is not None and bound_gap < -1e-4:
        notes.append("soc_margin_not_conservative_vs_actual")

    return RobustnessValidationReport(
        epsilon=float(epsilon),
        delta_star=delta_star,
        min_actual_margin=min_actual,
        soc_declared_margin=soc_declared_margin,
        bound_gap=bound_gap,
        intervention_increase=intervention_increase,
        objective_cost=objective_cost,
        robust_condition_holds=holds,
        notes=tuple(notes),
    )


def stage3_disagreement_under_perturbation(
    agent: AgentState2D,
    obstacle: CircularObstacle,
    *,
    epsilon: float = 0.05,
    delta: np.ndarray | None = None,
    alpha: float = 1.0,
    u_max: float = 1.0,
    solver: Literal["CLARABEL", "SCS"] = "CLARABEL",
) -> dict[str, Any]:
    """Compare nominal vs SOC-robust filters, and independently validate robust margin."""

    nominal = apply_cbf_filter(agent, obstacle, alpha=alpha, u_max=u_max, solver=solver)
    robust = apply_cbf_filter_soc_robust(
        agent, obstacle, alpha=alpha, u_max=u_max, epsilon=epsilon, solver=solver
    )
    # Never treat unavailable baselines as comparison arms.
    if nominal.metadata.get("comparison_baseline") is False or robust.metadata.get(
        "comparison_baseline"
    ) is False:
        return {
            "uncertainty_model_id": UNCERTAINTY_MODEL_ID,
            "epsilon": epsilon,
            "comparison_skipped": True,
            "reason": "unavailable_baseline_excluded_from_comparison",
            "nominal": nominal.as_dict(),
            "robust": robust.as_dict(),
        }

    if delta is None:
        p = np.asarray(agent.position, dtype=np.float64).reshape(2)
        c = np.asarray(obstacle.center, dtype=np.float64).reshape(2)
        v = c - p
        nrm = float(np.linalg.norm(v))
        delta = (epsilon * v / nrm) if nrm > 1e-12 else np.array([epsilon, 0.0])
    else:
        delta = np.asarray(delta, dtype=np.float64).reshape(2)
        if float(np.linalg.norm(delta)) > epsilon + 1e-9:
            raise ValueError("perturbation delta must satisfy ||delta|| <= epsilon")
    perturbed_agent = AgentState2D(
        position=np.asarray(agent.position, dtype=np.float64).reshape(2) + delta,
        u_desired=agent.u_desired,
        agent_id=agent.agent_id + "_pert",
    )
    robust_pert = apply_cbf_filter_soc_robust(
        perturbed_agent, obstacle, alpha=alpha, u_max=u_max, epsilon=epsilon, solver=solver
    )
    disagree = float("nan")
    if np.all(np.isfinite(nominal.u_safe)) and np.all(np.isfinite(robust.u_safe)):
        disagree = float(np.linalg.norm(nominal.u_safe - robust.u_safe))

    robustness: dict[str, Any] | None = None
    if np.all(np.isfinite(robust.u_safe)):
        report = validate_robust_cbf_control(
            agent,
            obstacle,
            robust.u_safe,
            alpha=alpha,
            epsilon=epsilon,
            u_desired=nominal.u_desired,
            soc_declared_margin=float(robust.safety_margin),
            nominal_intervention_norm=float(nominal.intervention_norm)
            if np.isfinite(nominal.intervention_norm)
            else 0.0,
        )
        robustness = report.as_dict()

    return {
        "uncertainty_model_id": UNCERTAINTY_MODEL_ID,
        "epsilon": epsilon,
        "delta": delta.tolist(),
        "nominal": nominal.as_dict(),
        "robust": robust.as_dict(),
        "robust_on_perturbed_observation": robust_pert.as_dict(),
        "nominal_vs_robust_u_l2": disagree,
        "robust_margin_nominal_obs": robust.safety_margin,
        "robust_margin_perturbed_obs": robust_pert.safety_margin,
        "robustness_validation": robustness,
        "comparison_skipped": False,
    }


@dataclass(slots=True)
class SOCRobustMarginModel:
    """Stage-3: uncertainty-aware robust margin via SOC under a declared noise model."""

    status: str = "implemented"
    implemented: bool = True
    uncertainty_model_id: str = UNCERTAINTY_MODEL_ID
    dynamics_model_id: str = DYNAMICS_MODEL_ID
    observation_model_id: str = OBSERVATION_MODEL_ID
    math_notes: str = (
        "Model: position observation noise δ with ||δ||_2 <= ε (hard bound). "
        "Robust CBF: require min_{||δ||<=ε} [2(p+δ-c)·u + α(||p+δ-c||^2 - r^2)] >= 0. "
        "Conservative SOC sufficient condition: "
        "2(p-c)·u + α h(p) >= 2ε||u|| + α(2ε||p-c|| + ε^2), "
        "encoded as a·u - t >= b_rob with t >= 2ε||u||_2. "
        "Do not claim robustness without this (or an equally explicit) uncertainty model. "
        "No MPC / recursive feasibility / multi-robot claims."
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "implemented": self.implemented,
            "uncertainty_model_id": self.uncertainty_model_id,
            "dynamics_model_id": self.dynamics_model_id,
            "observation_model_id": self.observation_model_id,
            "math_notes": self.math_notes,
            "stage": CBFStage.STAGE3_SOC_ROBUST.value,
        }


# Backward-compatible name
SOCRobustMarginScaffold = SOCRobustMarginModel


STAGE4_VALIDATION_CHECKLIST: tuple[str, ...] = (
    "stage1_nominal_cbf_qp_feasible_on_demo_corpus",
    "stage2_batched_agents_metrics_recorded",
    "stage3_soc_robust_margin_feasible_under_declared_noise_model",
    "stage3_robust_margin_disagreement_under_perturbation_quantified",
    "single_step_safety_margin_nonnegative_on_held_out_nominal_cases",
    "no_unexplained_infeasibility_rate_above_threshold",
)


@dataclass(slots=True)
class RecedingHorizonExperimental:
    """Stage-4 RH capability descriptor (experimental short-horizon filter).

    Full RH-MPC / multi-robot / AD remain out of scope. Runtime execution still
    fail-closes unless ``evaluate_stage4_gate`` reports checklist green.
    """

    status: str = "experimental_rh_available"
    capability_status: CapabilityStatus = CapabilityStatus.AVAILABLE
    reason: str = (
        "Minimal experimental single-agent short-horizon RH safety filter is implemented "
        "in conicshield.experimental.domains.cbf_rh. Runs only when the stage-4 checklist "
        "is green; not full MPC, not multi-robot, not production-qualified."
    )
    validation_checklist: tuple[str, ...] = STAGE4_VALIDATION_CHECKLIST
    checklist_satisfied: dict[str, bool] = field(default_factory=dict)
    rh_mpc_full: bool = False
    multi_robot: bool = False
    recursive_feasibility: bool = False
    experiment_version: str = "rh-v0.1.0"

    def as_dict(self) -> dict[str, Any]:
        satisfied = {k: bool(self.checklist_satisfied.get(k, False)) for k in self.validation_checklist}
        return {
            "status": self.status,
            "capability_status": str(self.capability_status),
            "reason": self.reason,
            "stage": CBFStage.STAGE4_RECEDING.value,
            "validation_checklist": list(self.validation_checklist),
            "checklist_satisfied": satisfied,
            "all_gates_passed": all(satisfied.values()) if satisfied else False,
            "unblock_allowed": False,  # runtime gate lives in cbf_rh / stage4_gate
            "rh_mpc_full": self.rh_mpc_full,
            "multi_robot": self.multi_robot,
            "recursive_feasibility": self.recursive_feasibility,
            "experiment_version": self.experiment_version,
            "experimental": True,
            "production_claim": False,
        }


# Backward-compatible alias (Wave ≤7 name)
RecedingHorizonBlocked = RecedingHorizonExperimental


def stage4_gate_status(*, checklist_satisfied: dict[str, bool] | None = None) -> RecedingHorizonExperimental:
    """Domain-level stage-4 capability object (experimental RH available when checklist green)."""

    return RecedingHorizonExperimental(checklist_satisfied=dict(checklist_satisfied or {}))


@dataclass(slots=True)
class CBFDomainMetrics:
    collision_or_safety_violation_rate: float
    minimum_safety_margin: float
    task_completion: float
    intervention_frequency: float
    intervention_norm_mean: float
    tail_latency: float | None
    fallback_rate: float
    shadow_disagreement_mean: float | None
    gradient_agreement: float | None
    active_set_transition_frequency: float
    robustness_under_observation_and_model_perturbation: float | None
    unavailable_baseline_excluded_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "collision_or_safety_violation_rate": self.collision_or_safety_violation_rate,
            "minimum_safety_margin": self.minimum_safety_margin,
            "task_completion": self.task_completion,
            "intervention_frequency": self.intervention_frequency,
            "intervention_norm_mean": self.intervention_norm_mean,
            "tail_latency": self.tail_latency,
            "fallback_rate": self.fallback_rate,
            "shadow_disagreement_mean": self.shadow_disagreement_mean,
            "gradient_agreement": self.gradient_agreement,
            "active_set_transition_frequency": self.active_set_transition_frequency,
            "robustness_under_observation_and_model_perturbation": (
                self.robustness_under_observation_and_model_perturbation
            ),
            "unavailable_baseline_excluded_count": self.unavailable_baseline_excluded_count,
        }


def _is_comparison_eligible(result: CBFFilterResult) -> bool:
    """Unavailable / NaN stubs are never comparison baselines (R13)."""

    if result.metadata.get("comparison_baseline") is False:
        return False
    if result.metadata.get("unavailable") is True:
        return False
    if result.canonical_status is CanonicalSolverStatus.UNAVAILABLE:
        return False
    if result.solver_status == "unavailable":
        return False
    return True


def compute_cbf_metrics(results: list[CBFFilterResult], *, dt: float = 0.1) -> CBFDomainMetrics:
    _ = dt  # reserved for one-step roll metrics
    eligible = [r for r in results if _is_comparison_eligible(r)]
    excluded = len(results) - len(eligible)
    n = max(len(eligible), 1)
    violations = 0
    margins: list[float] = []
    interventions = 0
    norms: list[float] = []
    latencies: list[float] = []
    fallbacks = 0
    shadow_l2: list[float] = []
    robust_margins: list[float] = []
    for r in results:
        if r.fallback or not _is_comparison_eligible(r):
            fallbacks += 1
    for r in eligible:
        if r.barrier_value < 0 and (not np.isfinite(r.safety_margin) or r.safety_margin < -1e-6):
            violations += 1
        if np.isfinite(r.safety_margin):
            margins.append(float(r.safety_margin))
        if r.stage == CBFStage.STAGE3_SOC_ROBUST.value and np.isfinite(r.safety_margin):
            robust_margins.append(float(r.safety_margin))
        if r.intervened:
            interventions += 1
        if np.isfinite(r.intervention_norm):
            norms.append(float(r.intervention_norm))
        if r.solve_time_sec is not None:
            latencies.append(float(r.solve_time_sec))
        if "shadow_disagreement_l2" in r.metadata:
            shadow_l2.append(float(r.metadata["shadow_disagreement_l2"]))
    task = float(sum(1 for r in eligible if np.all(np.isfinite(r.u_safe))) / n) if eligible else 0.0
    robustness = float(min(robust_margins)) if robust_margins else None
    return CBFDomainMetrics(
        collision_or_safety_violation_rate=float(violations / n) if eligible else float("nan"),
        minimum_safety_margin=float(min(margins)) if margins else float("nan"),
        task_completion=task,
        intervention_frequency=float(interventions / n) if eligible else 0.0,
        intervention_norm_mean=float(np.mean(norms)) if norms else 0.0,
        tail_latency=float(np.percentile(latencies, 95)) if latencies else None,
        fallback_rate=float(fallbacks / max(len(results), 1)),
        shadow_disagreement_mean=float(np.mean(shadow_l2)) if shadow_l2 else None,
        gradient_agreement=None,  # exact/smoothed CBF baseline not wired
        active_set_transition_frequency=0.0,
        robustness_under_observation_and_model_perturbation=robustness,
        unavailable_baseline_excluded_count=excluded,
    )


@dataclass(slots=True)
class CBF2DDomain:
    """One robust conic validation domain (R5 / R13)."""

    domain_id: str = "research.cbf_2d_motion.v1"
    status: str = "stages_1_2_3_implemented_stage4_experimental_rh"
    stages: tuple[str, ...] = tuple(s.value for s in CBFStage)
    scope_limit: str = (
        "One domain only. Do not add multiple robotics environments, "
        "full autonomous-driving stacks, or a general MPC framework. "
        "Stage-4 RH is short-horizon single-agent experimental only. "
        "No recursive feasibility or multi-robot claims."
    )
    baselines: tuple[str, ...] = tuple(b.value for b in CBFBaseline)
    dynamics_model_id: str = DYNAMICS_MODEL_ID
    observation_model_id: str = OBSERVATION_MODEL_ID
    metrics: tuple[str, ...] = (
        "collision_or_safety_violation_rate",
        "minimum_safety_margin",
        "task_completion",
        "intervention_frequency",
        "intervention_norm",
        "tail_latency",
        "fallback_rate",
        "shadow_disagreement",
        "gradient_agreement",
        "active_set_transition_frequency",
        "robustness_under_observation_and_model_perturbation",
        "rh_feasibility_rate",
        "rh_active_set_chatter_rate",
        "rh_stage3_robust_margin_interaction",
    )
    stage3: SOCRobustMarginModel = field(default_factory=SOCRobustMarginModel)
    stage4: RecedingHorizonExperimental = field(default_factory=RecedingHorizonExperimental)

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "status": self.status,
            "stages": list(self.stages),
            "scope_limit": self.scope_limit,
            "baselines": list(self.baselines),
            "dynamics_model_id": self.dynamics_model_id,
            "observation_model_id": self.observation_model_id,
            "metrics": list(self.metrics),
            "stage3": self.stage3.as_dict(),
            "stage4": self.stage4.as_dict(),
        }


# Backward-compatible alias for wave-1 imports
CBF2DDomainScaffold = CBF2DDomain


def nominal_cbf_qp_placeholder(*, state: tuple[float, float], obstacle: tuple[float, float]) -> dict[str, Any]:
    """Deprecated wave-1 placeholder — prefer ``apply_cbf_filter``."""

    agent = AgentState2D(
        position=np.asarray(state, dtype=np.float64),
        u_desired=np.array([1.0, 0.0], dtype=np.float64),
    )
    obs = CircularObstacle(center=np.asarray(obstacle, dtype=np.float64), radius=0.5)
    return apply_cbf_filter(agent, obs).as_dict()


def demo_stage1_scenario() -> CBFFilterResult:
    agent = AgentState2D(
        position=np.array([0.0, 0.0], dtype=np.float64),
        u_desired=np.array([1.0, 0.0], dtype=np.float64),
        agent_id="a0",
    )
    obs = CircularObstacle(center=np.array([1.0, 0.0], dtype=np.float64), radius=0.5, obstacle_id="o0")
    return apply_cbf_filter(agent, obs)


def demo_stage2_batch() -> list[CBFFilterResult]:
    agents = [
        AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]), "a0"),
        AgentState2D(np.array([0.0, 1.0]), np.array([0.0, -1.0]), "a1"),
    ]
    obstacles = [
        CircularObstacle(np.array([1.0, 0.0]), 0.5, "o0"),
        CircularObstacle(np.array([0.0, 0.0]), 0.4, "o1"),
    ]
    return apply_cbf_filter_batch(agents, obstacles, shadow=True)


def demo_stage3_soc_robust() -> CBFFilterResult:
    agent = AgentState2D(
        position=np.array([0.0, 0.0], dtype=np.float64),
        u_desired=np.array([1.0, 0.0], dtype=np.float64),
        agent_id="a0",
    )
    obs = CircularObstacle(center=np.array([1.0, 0.0], dtype=np.float64), radius=0.5, obstacle_id="o0")
    return apply_cbf_filter_soc_robust(agent, obs, epsilon=0.05)
