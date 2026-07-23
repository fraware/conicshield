"""Minimal experimental short-horizon receding-horizon CBF safety filter (R5 stage 4).

Scope (hard limits):
  - Single agent, 2D single-integrator CBF domain only
  - Short prediction horizon (default 3); apply first control only (true RH)
  - Reuses stage-1 nominal / stage-3 SOC-robust constraint structure
  - **Not** multi-robot, **not** full MPC, **not** an AD stack

Fail-closed unless the machine-checkable stage-4 checklist is green
(``evaluate_stage4_gate(...).unblock_allowed``). Experimental only —
``CapabilityStatus`` labeled; never a production claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

import numpy as np

from conicshield.experimental.domains.cbf_2d import (
    AgentState2D,
    CBFBaseline,
    CBFFilterResult,
    CBFStage,
    CircularObstacle,
    apply_cbf_filter,
    apply_cbf_filter_soc_robust,
    barrier_value,
)
from conicshield.experimental.gradients.capability import CapabilityStatus

RH_SCHEMA_ID = "research.cbf_receding_horizon.v0"
RH_EXPERIMENT_VERSION = "rh-v0.1.0"
RH_IMPLEMENTED = True
DEFAULT_HORIZON = 3
DEFAULT_DT = 0.1
MAX_ALLOWED_HORIZON = 8  # hard cap; keep short-horizon experimental

RH_LIMITATIONS: tuple[str, ...] = (
    "Experimental research filter only; not production-qualified.",
    "Single-agent 2D single-integrator; no multi-robot coupling.",
    "Short-horizon open-loop prediction inside the RH window; not full MPC "
    "with terminal ingredients or recursive feasibility certificates.",
    "No autonomous-driving / general AD stack.",
    "Native Moreau filter baseline remains unavailable on the public research path.",
    "Stage-3 robust mode uses the declared SOC sufficient condition, not a tight robust MPC tube.",
)


class RHConstraintMode(StrEnum):
    NOMINAL_STAGE1 = "nominal_stage1_cbf"
    SOC_ROBUST_STAGE3 = "soc_robust_stage3_cbf"


@dataclass(slots=True)
class RHStepRecord:
    step_index: int
    position: np.ndarray
    u_desired: np.ndarray
    u_applied: np.ndarray
    barrier_before: float
    barrier_after: float
    safety_margin: float
    robust_margin: float | None
    intervened: bool
    intervention_norm: float
    active_constraints: tuple[str, ...]
    solver_status: str
    feasible: bool
    solve_time_sec: float | None
    baseline: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "position": np.asarray(self.position, dtype=np.float64).tolist(),
            "u_desired": np.asarray(self.u_desired, dtype=np.float64).tolist(),
            "u_applied": np.asarray(self.u_applied, dtype=np.float64).tolist(),
            "barrier_before": float(self.barrier_before),
            "barrier_after": float(self.barrier_after),
            "safety_margin": float(self.safety_margin),
            "robust_margin": None if self.robust_margin is None else float(self.robust_margin),
            "intervened": self.intervened,
            "intervention_norm": float(self.intervention_norm),
            "active_constraints": list(self.active_constraints),
            "solver_status": self.solver_status,
            "feasible": self.feasible,
            "solve_time_sec": self.solve_time_sec,
            "baseline": self.baseline,
        }


@dataclass(slots=True)
class RHMetrics:
    n_steps: int
    feasibility_rate: float
    intervention_frequency: float
    intervention_norm_mean: float
    minimum_barrier: float
    minimum_safety_margin: float
    minimum_robust_margin: float | None
    collision_or_barrier_violation_rate: float
    active_set_chatter_rate: float
    mean_solve_time_sec: float | None
    p95_solve_time_sec: float | None
    stage3_robust_margin_interaction: float | None
    infeasible_horizon_flag: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "n_steps": self.n_steps,
            "feasibility_rate": self.feasibility_rate,
            "intervention_frequency": self.intervention_frequency,
            "intervention_norm_mean": self.intervention_norm_mean,
            "minimum_barrier": self.minimum_barrier,
            "minimum_safety_margin": self.minimum_safety_margin,
            "minimum_robust_margin": self.minimum_robust_margin,
            "collision_or_barrier_violation_rate": self.collision_or_barrier_violation_rate,
            "active_set_chatter_rate": self.active_set_chatter_rate,
            "mean_solve_time_sec": self.mean_solve_time_sec,
            "p95_solve_time_sec": self.p95_solve_time_sec,
            "stage3_robust_margin_interaction": self.stage3_robust_margin_interaction,
            "infeasible_horizon_flag": self.infeasible_horizon_flag,
        }


@dataclass(slots=True)
class RHNegativeRetention:
    """Retain edge-case / negative outcomes for honest reporting."""

    infeasible_steps: list[int] = field(default_factory=list)
    active_set_chatter_steps: list[int] = field(default_factory=list)
    barrier_violations: list[int] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "infeasible_steps": list(self.infeasible_steps),
            "active_set_chatter_steps": list(self.active_set_chatter_steps),
            "barrier_violations": list(self.barrier_violations),
            "notes": list(self.notes),
        }


@dataclass(slots=True)
class RHTrajectoryResult:
    schema_id: str = RH_SCHEMA_ID
    experiment_version: str = RH_EXPERIMENT_VERSION
    capability_status: CapabilityStatus = CapabilityStatus.BLOCKED
    experimental: bool = True
    production_claim: bool = False
    ran: bool = False
    fail_closed_reason: str | None = None
    stage4_gate_status: str = "unknown"
    stage4_unblock_allowed: bool = False
    horizon: int = DEFAULT_HORIZON
    dt: float = DEFAULT_DT
    constraint_mode: str = RHConstraintMode.NOMINAL_STAGE1.value
    baseline: str = CBFBaseline.PUBLIC_SOLVER_FILTER.value
    agent_id: str = ""
    obstacle_id: str = ""
    steps: list[RHStepRecord] = field(default_factory=list)
    metrics: RHMetrics | None = None
    negatives: RHNegativeRetention = field(default_factory=RHNegativeRetention)
    baseline_comparison: dict[str, Any] = field(default_factory=dict)
    limitations: tuple[str, ...] = RH_LIMITATIONS
    reproducibility: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "experiment_version": self.experiment_version,
            "capability_status": str(self.capability_status),
            "experimental": self.experimental,
            "production_claim": self.production_claim,
            "ran": self.ran,
            "fail_closed_reason": self.fail_closed_reason,
            "stage4_gate_status": self.stage4_gate_status,
            "stage4_unblock_allowed": self.stage4_unblock_allowed,
            "horizon": self.horizon,
            "dt": self.dt,
            "constraint_mode": self.constraint_mode,
            "baseline": self.baseline,
            "agent_id": self.agent_id,
            "obstacle_id": self.obstacle_id,
            "steps": [s.as_dict() for s in self.steps],
            "metrics": None if self.metrics is None else self.metrics.as_dict(),
            "negatives": self.negatives.as_dict(),
            "baseline_comparison": dict(self.baseline_comparison),
            "limitations": list(self.limitations),
            "reproducibility": dict(self.reproducibility),
            "rh_mpc_full": False,
            "multi_robot": False,
            "stage": CBFStage.STAGE4_RECEDING.value,
        }


def describe_rh_capability() -> dict[str, Any]:
    """Honest capability descriptor for stage-4 gate / domain status."""

    return {
        "implemented": RH_IMPLEMENTED,
        "experiment_version": RH_EXPERIMENT_VERSION,
        "schema_id": RH_SCHEMA_ID,
        "capability_status": str(CapabilityStatus.AVAILABLE),
        "experimental": True,
        "production_claim": False,
        "rh_mpc_full": False,
        "multi_robot": False,
        "default_horizon": DEFAULT_HORIZON,
        "max_allowed_horizon": MAX_ALLOWED_HORIZON,
        "constraint_modes": [m.value for m in RHConstraintMode],
        "limitations": list(RH_LIMITATIONS),
        "requires_stage4_checklist_green": True,
    }


def _fail_closed(
    *,
    reason: str,
    gate_status: str,
    unblock: bool,
    agent: AgentState2D,
    obstacle: CircularObstacle,
    horizon: int,
    dt: float,
    mode: str,
    baseline: str,
    reproducibility: dict[str, Any],
) -> RHTrajectoryResult:
    return RHTrajectoryResult(
        capability_status=CapabilityStatus.BLOCKED,
        ran=False,
        fail_closed_reason=reason,
        stage4_gate_status=gate_status,
        stage4_unblock_allowed=unblock,
        horizon=horizon,
        dt=dt,
        constraint_mode=mode,
        baseline=baseline,
        agent_id=agent.agent_id,
        obstacle_id=obstacle.obstacle_id,
        negatives=RHNegativeRetention(notes=[reason]),
        reproducibility=reproducibility,
    )


def _solve_step(
    agent: AgentState2D,
    obstacle: CircularObstacle,
    *,
    mode: RHConstraintMode,
    alpha: float,
    u_max: float,
    epsilon: float,
    baseline: str,
    solver: Literal["CLARABEL", "SCS"],
    shadow: bool,
) -> CBFFilterResult:
    if mode == RHConstraintMode.SOC_ROBUST_STAGE3:
        primary = apply_cbf_filter_soc_robust(
            agent,
            obstacle,
            alpha=alpha,
            u_max=u_max,
            epsilon=epsilon,
            baseline=baseline,
            solver=solver,
        )
    else:
        primary = apply_cbf_filter(
            agent,
            obstacle,
            alpha=alpha,
            u_max=u_max,
            baseline=baseline,
            solver=solver,
        )
    primary.stage = CBFStage.STAGE4_RECEDING.value
    primary.metadata["rh_constraint_mode"] = mode.value
    primary.metadata["experimental_rh"] = True
    if shadow and baseline == CBFBaseline.PUBLIC_SOLVER_FILTER.value:
        other: Literal["CLARABEL", "SCS"] = "SCS" if solver == "CLARABEL" else "CLARABEL"
        if mode == RHConstraintMode.SOC_ROBUST_STAGE3:
            shadow_res = apply_cbf_filter_soc_robust(
                agent,
                obstacle,
                alpha=alpha,
                u_max=u_max,
                epsilon=epsilon,
                baseline=baseline,
                solver=other,
            )
        else:
            shadow_res = apply_cbf_filter(
                agent,
                obstacle,
                alpha=alpha,
                u_max=u_max,
                baseline=baseline,
                solver=other,
            )
        primary.metadata["shadow"] = shadow_res.as_dict()
        if np.all(np.isfinite(primary.u_safe)) and np.all(np.isfinite(shadow_res.u_safe)):
            primary.metadata["shadow_disagreement_l2"] = float(np.linalg.norm(primary.u_safe - shadow_res.u_safe))
        primary.baseline = CBFBaseline.PRIMARY_PLUS_SHADOW.value
    return primary


def _compute_metrics(steps: list[RHStepRecord], negatives: RHNegativeRetention) -> RHMetrics:
    n = max(len(steps), 1)
    feas = sum(1 for s in steps if s.feasible)
    interv = sum(1 for s in steps if s.intervened)
    norms = [s.intervention_norm for s in steps if np.isfinite(s.intervention_norm)]
    barriers = [s.barrier_after for s in steps if np.isfinite(s.barrier_after)]
    margins = [s.safety_margin for s in steps if np.isfinite(s.safety_margin)]
    robusts = [s.robust_margin for s in steps if s.robust_margin is not None and np.isfinite(s.robust_margin)]
    viol = sum(1 for s in steps if s.barrier_after < -1e-6)
    latencies = [s.solve_time_sec for s in steps if s.solve_time_sec is not None]
    chatter = float(len(negatives.active_set_chatter_steps) / max(len(steps) - 1, 1)) if len(steps) > 1 else 0.0
    # Interaction proxy: mean robust margin when stage-3 mode was used
    stage3_interaction = float(np.mean(robusts)) if robusts else None
    return RHMetrics(
        n_steps=len(steps),
        feasibility_rate=float(feas / n),
        intervention_frequency=float(interv / n),
        intervention_norm_mean=float(np.mean(norms)) if norms else 0.0,
        minimum_barrier=float(min(barriers)) if barriers else float("nan"),
        minimum_safety_margin=float(min(margins)) if margins else float("nan"),
        minimum_robust_margin=float(min(robusts)) if robusts else None,
        collision_or_barrier_violation_rate=float(viol / n),
        active_set_chatter_rate=chatter,
        mean_solve_time_sec=float(np.mean(latencies)) if latencies else None,
        p95_solve_time_sec=float(np.percentile(latencies, 95)) if latencies else None,
        stage3_robust_margin_interaction=stage3_interaction,
        infeasible_horizon_flag=bool(negatives.infeasible_steps),
    )


def _run_trajectory(
    agent: AgentState2D,
    obstacle: CircularObstacle,
    *,
    horizon: int,
    dt: float,
    mode: RHConstraintMode,
    alpha: float,
    u_max: float,
    epsilon: float,
    baseline: str,
    solver: Literal["CLARABEL", "SCS"],
    shadow: bool,
    u_desired_policy: np.ndarray | None,
) -> tuple[list[RHStepRecord], RHNegativeRetention]:
    steps: list[RHStepRecord] = []
    negatives = RHNegativeRetention()
    pos = np.asarray(agent.position, dtype=np.float64).reshape(2).copy()
    u_pol = (
        np.asarray(u_desired_policy, dtype=np.float64).reshape(2)
        if u_desired_policy is not None
        else np.asarray(agent.u_desired, dtype=np.float64).reshape(2)
    )
    prev_active: tuple[str, ...] | None = None

    for t in range(horizon):
        cur = AgentState2D(position=pos.copy(), u_desired=u_pol.copy(), agent_id=agent.agent_id)
        h_before = barrier_value(pos, obstacle)
        filt = _solve_step(
            cur,
            obstacle,
            mode=mode,
            alpha=alpha,
            u_max=u_max,
            epsilon=epsilon,
            baseline=baseline,
            solver=solver,
            shadow=shadow,
        )
        feasible = bool(
            (
                filt.canonical_status.value in {"optimal"}
                or filt.solver_status in {"optimal", "optimal_inaccurate", "no_filter"}
            )
            and np.all(np.isfinite(filt.u_safe))
        )
        if not feasible:
            negatives.infeasible_steps.append(t)
            u_app = np.full(2, np.nan)
        else:
            u_app = np.asarray(filt.u_safe, dtype=np.float64).reshape(2)

        if prev_active is not None and set(filt.active_constraints) != set(prev_active):
            # Chatter: active-set flip between consecutive RH applications
            negatives.active_set_chatter_steps.append(t)
        prev_active = filt.active_constraints

        pos_next = pos + float(dt) * u_app if np.all(np.isfinite(u_app)) else pos.copy()
        h_after = barrier_value(pos_next, obstacle)
        if h_after < -1e-6:
            negatives.barrier_violations.append(t)

        robust_m: float | None = None
        if mode == RHConstraintMode.SOC_ROBUST_STAGE3 and np.isfinite(filt.safety_margin):
            robust_m = float(filt.safety_margin)

        steps.append(
            RHStepRecord(
                step_index=t,
                position=pos.copy(),
                u_desired=u_pol.copy(),
                u_applied=u_app.copy(),
                barrier_before=float(h_before),
                barrier_after=float(h_after),
                safety_margin=float(filt.safety_margin),
                robust_margin=robust_m,
                intervened=bool(filt.intervened),
                intervention_norm=float(filt.intervention_norm),
                active_constraints=tuple(filt.active_constraints),
                solver_status=str(filt.solver_status),
                feasible=feasible,
                solve_time_sec=filt.solve_time_sec,
                baseline=str(filt.baseline),
            )
        )
        if not feasible:
            # Fail closed for remaining horizon after infeasibility
            negatives.notes.append(f"infeasible_at_step_{t}: remaining horizon truncated (negative retention)")
            break
        pos = pos_next

    if negatives.infeasible_steps:
        negatives.notes.append("infeasible_horizon_edge_case_retained")
    if negatives.active_set_chatter_steps:
        negatives.notes.append("active_set_chatter_edge_case_retained")
    if negatives.barrier_violations:
        negatives.notes.append("barrier_violation_edge_case_retained")
    return steps, negatives


def run_receding_horizon_filter(
    agent: AgentState2D,
    obstacle: CircularObstacle,
    *,
    horizon: int = DEFAULT_HORIZON,
    dt: float = DEFAULT_DT,
    alpha: float = 1.0,
    u_max: float = 1.0,
    epsilon: float = 0.05,
    constraint_mode: RHConstraintMode | str = RHConstraintMode.NOMINAL_STAGE1,
    baseline: CBFBaseline | str = CBFBaseline.PUBLIC_SOLVER_FILTER,
    solver: Literal["CLARABEL", "SCS"] = "CLARABEL",
    shadow: bool = False,
    u_desired_policy: np.ndarray | None = None,
    require_stage4_checklist_green: bool = True,
    gate_evaluation: Any | None = None,
    compare_baselines: bool = True,
) -> RHTrajectoryResult:
    """Run minimal single-agent short-horizon RH safety filter.

    Fail-closed when ``require_stage4_checklist_green`` and the stage-4 gate
    does not report checklist green (``unblock_allowed``).
    """

    if horizon < 1 or horizon > MAX_ALLOWED_HORIZON:
        raise ValueError(f"horizon must be in [1, {MAX_ALLOWED_HORIZON}]")
    if dt <= 0.0:
        raise ValueError("dt must be > 0")

    mode = constraint_mode if isinstance(constraint_mode, RHConstraintMode) else RHConstraintMode(str(constraint_mode))
    baseline_s = str(baseline)
    reproducibility = {
        "schema_id": RH_SCHEMA_ID,
        "experiment_version": RH_EXPERIMENT_VERSION,
        "horizon": horizon,
        "dt": dt,
        "alpha": alpha,
        "u_max": u_max,
        "epsilon": epsilon,
        "constraint_mode": mode.value,
        "baseline": baseline_s,
        "solver": solver,
        "shadow": shadow,
        "agent": agent.as_dict(),
        "obstacle": obstacle.as_dict(),
    }

    gate_status = "bypassed"
    unblock = True
    if require_stage4_checklist_green:
        if gate_evaluation is None:
            from conicshield.experimental.domains.stage4_gate import evaluate_stage4_gate

            gate_evaluation = evaluate_stage4_gate()
        gate_d: dict[str, Any]
        as_dict_fn = getattr(gate_evaluation, "as_dict", None)
        if callable(as_dict_fn):
            gate_d = dict(as_dict_fn())
        elif isinstance(gate_evaluation, dict):
            gate_d = dict(gate_evaluation)
        else:
            raise TypeError("gate_evaluation must provide as_dict() or be a mapping")
        gate_status = str(gate_d.get("stage4_status", "unknown"))
        unblock = bool(gate_d.get("unblock_allowed", False)) and bool(gate_d.get("all_required_passed", False))
        reproducibility["stage4_gate"] = {
            "stage4_status": gate_status,
            "unblock_allowed": unblock,
            "all_required_passed": gate_d.get("all_required_passed"),
            "passed_count": gate_d.get("passed_count"),
            "required_count": gate_d.get("required_count"),
        }
        if not unblock:
            return _fail_closed(
                reason=(
                    "stage4_checklist_not_green: RH refuses to run "
                    f"(status={gate_status}, unblock_allowed={gate_d.get('unblock_allowed')})"
                ),
                gate_status=gate_status,
                unblock=False,
                agent=agent,
                obstacle=obstacle,
                horizon=horizon,
                dt=dt,
                mode=mode.value,
                baseline=baseline_s,
                reproducibility=reproducibility,
            )

    steps, negatives = _run_trajectory(
        agent,
        obstacle,
        horizon=horizon,
        dt=dt,
        mode=mode,
        alpha=alpha,
        u_max=u_max,
        epsilon=epsilon,
        baseline=baseline_s,
        solver=solver,
        shadow=shadow,
        u_desired_policy=u_desired_policy,
    )
    metrics = _compute_metrics(steps, negatives)

    comparison: dict[str, Any] = {}
    if compare_baselines:
        # No-filter open-loop roll (same policy) for contrast hooks
        nf_steps, nf_neg = _run_trajectory(
            agent,
            obstacle,
            horizon=horizon,
            dt=dt,
            mode=RHConstraintMode.NOMINAL_STAGE1,
            alpha=alpha,
            u_max=u_max,
            epsilon=epsilon,
            baseline=CBFBaseline.NO_FILTER.value,
            solver=solver,
            shadow=False,
            u_desired_policy=u_desired_policy,
        )
        comparison["no_filter"] = {
            "metrics": _compute_metrics(nf_steps, nf_neg).as_dict(),
            "negatives": nf_neg.as_dict(),
        }
        # Public solver single-step (stage-1) first-control contrast
        single = apply_cbf_filter(agent, obstacle, alpha=alpha, u_max=u_max, solver=solver)
        comparison["public_solver_single_step"] = single.as_dict()
        # Shadow hook availability (Clarabel vs SCS) on the initial state
        other: Literal["CLARABEL", "SCS"] = "SCS" if solver == "CLARABEL" else "CLARABEL"
        try:
            shadow0 = apply_cbf_filter(agent, obstacle, alpha=alpha, u_max=u_max, solver=other)
            comparison["shadow_initial"] = {
                "solver": other,
                "result": shadow0.as_dict(),
                "disagreement_l2": (
                    float(np.linalg.norm(single.u_safe - shadow0.u_safe))
                    if np.all(np.isfinite(single.u_safe)) and np.all(np.isfinite(shadow0.u_safe))
                    else None
                ),
            }
        except Exception as exc:  # noqa: BLE001
            comparison["shadow_initial"] = {"available": False, "error": type(exc).__name__}

    return RHTrajectoryResult(
        capability_status=CapabilityStatus.AVAILABLE,
        ran=True,
        fail_closed_reason=None,
        stage4_gate_status=gate_status,
        stage4_unblock_allowed=unblock,
        horizon=horizon,
        dt=dt,
        constraint_mode=mode.value,
        baseline=baseline_s,
        agent_id=agent.agent_id,
        obstacle_id=obstacle.obstacle_id,
        steps=steps,
        metrics=metrics,
        negatives=negatives,
        baseline_comparison=comparison,
        reproducibility=reproducibility,
    )


def demo_rh_scenario(*, require_gate: bool = True) -> RHTrajectoryResult:
    """CI-small demo: agent approaching a circular obstacle under short-horizon RH."""

    agent = AgentState2D(
        position=np.array([0.0, 0.0], dtype=np.float64),
        u_desired=np.array([1.0, 0.0], dtype=np.float64),
        agent_id="rh_a0",
    )
    obs = CircularObstacle(
        center=np.array([1.2, 0.0], dtype=np.float64),
        radius=0.5,
        obstacle_id="rh_o0",
    )
    return run_receding_horizon_filter(
        agent,
        obs,
        horizon=DEFAULT_HORIZON,
        dt=DEFAULT_DT,
        constraint_mode=RHConstraintMode.NOMINAL_STAGE1,
        shadow=True,
        require_stage4_checklist_green=require_gate,
    )


def demo_rh_soc_robust(*, require_gate: bool = True) -> RHTrajectoryResult:
    """CI-small demo using stage-3 SOC-robust constraints inside the RH loop."""

    agent = AgentState2D(
        position=np.array([0.0, 0.0], dtype=np.float64),
        u_desired=np.array([1.0, 0.0], dtype=np.float64),
        agent_id="rh_a0_robust",
    )
    obs = CircularObstacle(
        center=np.array([1.2, 0.0], dtype=np.float64),
        radius=0.5,
        obstacle_id="rh_o0",
    )
    return run_receding_horizon_filter(
        agent,
        obs,
        horizon=DEFAULT_HORIZON,
        dt=DEFAULT_DT,
        constraint_mode=RHConstraintMode.SOC_ROBUST_STAGE3,
        epsilon=0.05,
        require_stage4_checklist_green=require_gate,
    )


def main() -> None:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="CBF experimental short-horizon RH filter")
    parser.add_argument("--output-dir", type=Path, default=Path("output/research/cbf_rh"))
    parser.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    parser.add_argument("--ci-small", action="store_true")
    parser.add_argument("--soc-robust", action="store_true")
    parser.add_argument("--bypass-gate", action="store_true", help="research debug only")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.soc_robust:
        result = demo_rh_soc_robust(require_gate=not args.bypass_gate)
    else:
        result = demo_rh_scenario(require_gate=not args.bypass_gate)
    if not args.ci_small and args.horizon != DEFAULT_HORIZON:
        agent = AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]), "rh_a0")
        obs = CircularObstacle(np.array([1.2, 0.0]), 0.5, "rh_o0")
        result = run_receding_horizon_filter(
            agent,
            obs,
            horizon=min(args.horizon, MAX_ALLOWED_HORIZON),
            constraint_mode=(
                RHConstraintMode.SOC_ROBUST_STAGE3 if args.soc_robust else RHConstraintMode.NOMINAL_STAGE1
            ),
            require_stage4_checklist_green=not args.bypass_gate,
        )

    out = args.output_dir / "cbf_rh_result.json"
    out.write_text(json.dumps(result.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    cap = describe_rh_capability()
    (args.output_dir / "cbf_rh_capability.json").write_text(
        json.dumps(cap, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"wrote {out} ran={result.ran} status={result.capability_status} "
        f"gate={result.stage4_gate_status} version={RH_EXPERIMENT_VERSION}"
    )


if __name__ == "__main__":
    main()
