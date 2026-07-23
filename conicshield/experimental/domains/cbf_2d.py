"""Uncertainty-aware CBF safety filter for 2D motion (R5).

Stages:
  1. Nominal affine control-barrier QP (implemented)
  2. Batched agents with distinct states/obstacles (implemented)
  3. SOC robust margin under bounded L2 observation noise (implemented)
  4. Minimal experimental short-horizon RH — gated on stage-4 checklist green
     (see ``cbf_rh``; not full MPC / multi-robot / AD)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

import numpy as np

from conicshield.experimental.adapters.track1_protocols import CanonicalSolverStatus
from conicshield.experimental.gradients.capability import CapabilityStatus


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
        }


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
    """Affine CBF inequality: a·u >= b  for single integrator ṗ = u.

    ḣ = 2(p-c)·u, require ḣ + α h >= 0 ⇒ 2(p-c)·u >= -α h.
    """

    p = np.asarray(position, dtype=np.float64).reshape(2)
    c = np.asarray(obstacle.center, dtype=np.float64).reshape(2)
    h = barrier_value(p, obstacle)
    a = 2.0 * (p - c)
    b = -float(alpha) * h
    return a, b


def _solve_nominal_cbf_qp(
    *,
    u_des: np.ndarray,
    a: np.ndarray,
    b: float,
    u_max: float,
    solver: Literal["CLARABEL", "SCS"] = "CLARABEL",
) -> tuple[np.ndarray, str, tuple[str, ...], float | None]:
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
        return np.full(2, np.nan), f"error:{type(exc).__name__}", (), time.perf_counter() - t0
    elapsed = time.perf_counter() - t0
    if u.value is None:
        return np.full(2, np.nan), status, (), elapsed
    uv = np.asarray(u.value, dtype=np.float64).reshape(2)
    active: list[str] = []
    if float(a @ uv - b) <= 1e-6:
        active.append("cbf")
    if abs(float(np.linalg.norm(uv) - u_max)) <= 1e-5:
        active.append("u_max")
    return uv, status, tuple(active), elapsed


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
    if "error" in s or "numeric" in s:
        return CanonicalSolverStatus.NUMERICAL_FAILURE
    return CanonicalSolverStatus.UNKNOWN


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
            stage=CBFStage.STAGE1_NOMINAL.value,
        )

    if baseline_s == CBFBaseline.MOREAU_FILTER.value:
        return CBFFilterResult(
            agent_id=agent.agent_id,
            u_safe=np.full(2, np.nan),
            u_desired=u_des,
            intervened=True,
            intervention_norm=float("nan"),
            barrier_value=h,
            safety_margin=h,
            active_constraints=(),
            solver_status="unavailable",
            canonical_status=CanonicalSolverStatus.UNAVAILABLE,
            baseline=baseline_s,
            stage=CBFStage.STAGE1_NOMINAL.value,
            fallback=True,
            metadata={"stub": True, "reason": "Moreau filter unavailable in research public path"},
        )

    if baseline_s == CBFBaseline.EXACT_VS_SMOOTHED.value:
        return CBFFilterResult(
            agent_id=agent.agent_id,
            u_safe=np.full(2, np.nan),
            u_desired=u_des,
            intervened=True,
            intervention_norm=float("nan"),
            barrier_value=h,
            safety_margin=h,
            active_constraints=(),
            solver_status="unavailable",
            canonical_status=CanonicalSolverStatus.UNAVAILABLE,
            baseline=baseline_s,
            stage=CBFStage.STAGE1_NOMINAL.value,
            fallback=True,
            metadata={
                "unavailable": True,
                "reason": "exact/smoothed differentiable filter baseline not wired for CBF",
            },
        )

    a, b = cbf_affine_constraint(agent.position, obstacle, alpha=alpha)
    u_safe, status, active, elapsed = _solve_nominal_cbf_qp(
        u_des=u_des, a=a, b=b, u_max=u_max, solver=solver
    )
    # Post-filter barrier rate margin: ḣ + α h
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
        active_constraints=active,
        solver_status=status,
        canonical_status=_map_status(status),
        baseline=baseline_s,
        stage=CBFStage.STAGE1_NOMINAL.value,
        solve_time_sec=elapsed,
        metadata={"alpha": alpha, "u_max": u_max, "solver": solver},
    )


def apply_cbf_filter_batched(
    agents: list[AgentState2D],
    obstacles: list[CircularObstacle],
    *,
    alpha: float = 1.0,
    u_max: float = 1.0,
    baseline: CBFBaseline | str = CBFBaseline.PUBLIC_SOLVER_FILTER,
    solver: Literal["CLARABEL", "SCS"] = "CLARABEL",
    shadow: bool = False,
) -> list[CBFFilterResult]:
    """Stage-2: batched agents with distinct states/obstacles (sequential research batch)."""

    if len(agents) != len(obstacles):
        raise ValueError("agents and obstacles must be paired 1:1 for stage-2 scaffold")
    results: list[CBFFilterResult] = []
    for agent, obs in zip(agents, obstacles, strict=True):
        primary = apply_cbf_filter(
            agent, obs, alpha=alpha, u_max=u_max, baseline=baseline, solver=solver
        )
        primary.stage = CBFStage.STAGE2_BATCHED.value
        primary.metadata["batch_emulation"] = "sequential_adapter"
        if shadow and baseline == CBFBaseline.PUBLIC_SOLVER_FILTER:
            other = "SCS" if solver == "CLARABEL" else "CLARABEL"
            shadow_res = apply_cbf_filter(
                agent, obs, alpha=alpha, u_max=u_max, baseline=baseline, solver=other  # type: ignore[arg-type]
            )
            primary.metadata["shadow"] = shadow_res.as_dict()
            if np.all(np.isfinite(primary.u_safe)) and np.all(np.isfinite(shadow_res.u_safe)):
                primary.metadata["shadow_disagreement_l2"] = float(
                    np.linalg.norm(primary.u_safe - shadow_res.u_safe)
                )
            primary.baseline = CBFBaseline.PRIMARY_PLUS_SHADOW.value
        results.append(primary)
    return results


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


def _solve_soc_robust_cbf_qp(
    *,
    u_des: np.ndarray,
    a: np.ndarray,
    b_rob: float,
    two_eps: float,
    u_max: float,
    solver: Literal["CLARABEL", "SCS"] = "CLARABEL",
) -> tuple[np.ndarray, str, tuple[str, ...], float | None]:
    import time

    import cvxpy as cp

    u = cp.Variable(2)
    t = cp.Variable(nonneg=True)
    cons = [
        a @ u - t >= float(b_rob),
        cp.norm(u, 2) * float(two_eps) <= t if two_eps > 0.0 else t >= 0.0,
        cp.norm(u, 2) <= float(u_max),
    ]
    if two_eps <= 0.0:
        # Reduce to nominal affine CBF when epsilon=0
        cons = [a @ u >= float(b_rob), cp.norm(u, 2) <= float(u_max)]
        t = None  # type: ignore[assignment]
    prob = cp.Problem(cp.Minimize(cp.sum_squares(u - u_des)), cons)
    t0 = time.perf_counter()
    try:
        prob.solve(solver=getattr(cp, solver), verbose=False)
        status = str(prob.status)
    except Exception as exc:  # noqa: BLE001
        return np.full(2, np.nan), f"error:{type(exc).__name__}", (), time.perf_counter() - t0
    elapsed = time.perf_counter() - t0
    if u.value is None:
        return np.full(2, np.nan), status, (), elapsed
    uv = np.asarray(u.value, dtype=np.float64).reshape(2)
    active: list[str] = []
    if two_eps > 0.0 and t is not None and t.value is not None:
        slack = float(a @ uv - float(t.value) - b_rob)
        if slack <= 1e-6:
            active.append("cbf_soc_robust")
    else:
        if float(a @ uv - b_rob) <= 1e-6:
            active.append("cbf")
    if abs(float(np.linalg.norm(uv) - u_max)) <= 1e-5:
        active.append("u_max")
    return uv, status, tuple(active), elapsed


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
            metadata={"epsilon": epsilon, "uncertainty_model_id": UNCERTAINTY_MODEL_ID},
        )

    a, b_rob, two_eps = robust_cbf_soc_constants(
        agent.position, obstacle, alpha=alpha, epsilon=epsilon
    )
    u_safe, status, active, elapsed = _solve_soc_robust_cbf_qp(
        u_des=u_des, a=a, b_rob=b_rob, two_eps=two_eps, u_max=u_max, solver=solver
    )
    p = np.asarray(agent.position, dtype=np.float64).reshape(2)
    c = np.asarray(obstacle.center, dtype=np.float64).reshape(2)
    if np.all(np.isfinite(u_safe)):
        # Nominal Lie derivative margin (not the robust margin)
        hdot = float(2.0 * np.dot(p - c, u_safe))
        nominal_margin = hdot + float(alpha) * h
        # Robust margin residual: a·u - 2ε||u|| - b_rob
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
        active_constraints=active,
        solver_status=status,
        canonical_status=_map_status(status),
        baseline=baseline_s,
        stage=CBFStage.STAGE3_SOC_ROBUST.value,
        solve_time_sec=elapsed,
        metadata={
            "alpha": alpha,
            "u_max": u_max,
            "epsilon": epsilon,
            "solver": solver,
            "uncertainty_model_id": UNCERTAINTY_MODEL_ID,
            "nominal_lie_margin": nominal_margin,
            "robust_margin": robust_margin,
            "b_rob": b_rob,
        },
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
    """Compare nominal vs SOC-robust filters, and robust filter on a perturbed observation."""

    nominal = apply_cbf_filter(agent, obstacle, alpha=alpha, u_max=u_max, solver=solver)
    robust = apply_cbf_filter_soc_robust(
        agent, obstacle, alpha=alpha, u_max=u_max, epsilon=epsilon, solver=solver
    )
    if delta is None:
        # Worst-case direction toward obstacle, scaled to epsilon
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
    }


# Justified uncertainty model for stage 3 (see research notes):
# Position is observed as p_hat = p_true + δ with ||δ||_2 <= epsilon (hard bounded
# measurement noise). Barrier h(p)=||p-c||^2 - r^2 for single integrator ṗ=u.
# Robust CBF requires inf_{||δ||<=ε} [2(p+δ-c)·u + α h(p+δ)] >= 0.
# Conservative SOC-representable sufficient condition used here:
#   2(p-c)·u + α h(p) >= 2ε||u|| + α(2ε||p-c|| + ε^2)
# Equivalently with slack t: a·u - t >= b_rob,  t >= 2ε ||u||_2.
UNCERTAINTY_MODEL_ID = "bounded_l2_position_observation_noise.v1"


@dataclass(slots=True)
class SOCRobustMarginModel:
    """Stage-3: uncertainty-aware robust margin via SOC under a declared noise model."""

    status: str = "implemented"
    implemented: bool = True
    uncertainty_model_id: str = UNCERTAINTY_MODEL_ID
    math_notes: str = (
        "Model: position observation noise δ with ||δ||_2 <= ε (hard bound). "
        "Robust CBF: require min_{||δ||<=ε} [2(p+δ-c)·u + α(||p+δ-c||^2 - r^2)] >= 0. "
        "Conservative SOC sufficient condition: "
        "2(p-c)·u + α h(p) >= 2ε||u|| + α(2ε||p-c|| + ε^2), "
        "encoded as a·u - t >= b_rob with t >= 2ε||u||_2. "
        "Do not claim robustness without this (or an equally explicit) uncertainty model."
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "implemented": self.implemented,
            "uncertainty_model_id": self.uncertainty_model_id,
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
        }


def compute_cbf_metrics(results: list[CBFFilterResult], *, dt: float = 0.1) -> CBFDomainMetrics:
    n = max(len(results), 1)
    violations = 0
    margins: list[float] = []
    interventions = 0
    norms: list[float] = []
    latencies: list[float] = []
    fallbacks = 0
    shadow_l2: list[float] = []
    robust_margins: list[float] = []
    for r in results:
        # One-step roll: p' = p + dt * u_safe; violation if barrier would be negative and unsafe control
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
        if r.fallback:
            fallbacks += 1
        if "shadow_disagreement_l2" in r.metadata:
            shadow_l2.append(float(r.metadata["shadow_disagreement_l2"]))
    # task_completion proxy: fraction with finite safe control
    task = float(sum(1 for r in results if np.all(np.isfinite(r.u_safe))) / n)
    robustness = float(min(robust_margins)) if robust_margins else None
    return CBFDomainMetrics(
        collision_or_safety_violation_rate=float(violations / n),
        minimum_safety_margin=float(min(margins)) if margins else float("nan"),
        task_completion=task,
        intervention_frequency=float(interventions / n),
        intervention_norm_mean=float(np.mean(norms)) if norms else 0.0,
        tail_latency=float(np.percentile(latencies, 95)) if latencies else None,
        fallback_rate=float(fallbacks / n),
        shadow_disagreement_mean=float(np.mean(shadow_l2)) if shadow_l2 else None,
        gradient_agreement=None,  # exact/smoothed CBF baseline not wired
        active_set_transition_frequency=0.0,  # single-step batch; multi-step later
        robustness_under_observation_and_model_perturbation=robustness,
    )


@dataclass(slots=True)
class CBF2DDomain:
    """One robust conic validation domain (R5)."""

    domain_id: str = "research.cbf_2d_motion.v1"
    status: str = "stages_1_2_3_implemented_stage4_experimental_rh"
    stages: tuple[str, ...] = tuple(s.value for s in CBFStage)
    scope_limit: str = (
        "One domain only. Do not add multiple robotics environments, "
        "full autonomous-driving stacks, or a general MPC framework. "
        "Stage-4 RH is short-horizon single-agent experimental only."
    )
    baselines: tuple[str, ...] = tuple(b.value for b in CBFBaseline)
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
    return apply_cbf_filter_batched(agents, obstacles, shadow=True)


def demo_stage3_soc_robust() -> CBFFilterResult:
    agent = AgentState2D(
        position=np.array([0.0, 0.0], dtype=np.float64),
        u_desired=np.array([1.0, 0.0], dtype=np.float64),
        agent_id="a0",
    )
    obs = CircularObstacle(center=np.array([1.0, 0.0], dtype=np.float64), radius=0.5, obstacle_id="o0")
    return apply_cbf_filter_soc_robust(agent, obs, epsilon=0.05)
