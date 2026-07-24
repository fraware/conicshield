"""Smoothed-map study: forward bias, digests, Jacobian stability (R11).

Per ε records forward bias vs hard-constrained, feasibility change, Jacobian
stability, FD agreement away from transitions, transition behavior, and cost.
Smoothed forward digests must be distinct from hard-constrained digests.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.experimental.assurance.evidence import (
    array_digest,
    forward_solution_digest,
    problem_digest,
    topology_digest,
)
from conicshield.experimental.gradients.active_set_protocol import (
    ActiveSetTransitionClass,
    probe_active_set_transition_all_coords,
)
from conicshield.experimental.gradients.finite_difference import (
    central_finite_difference_jacobian,
    fd_agreement_metric,
)
from conicshield.experimental.gradients.forward_gate import DEFAULT_RESIDUAL_TOLERANCE
from conicshield.experimental.gradients.smoothed_backend import (
    _jacobian_softplus_ift,
    _solve_softplus_smoothed,
    smoothed_backend_gradient,
)
from conicshield.experimental.gradients.exact_backend import build_moreau_shield_qp
from conicshield.experimental.solver_assurance.backends import create_research_projector
from conicshield.specs.schema import SafetySpec


@dataclass(slots=True)
class SmoothedEpsilonRow:
    epsilon: float
    available: bool
    soft_vs_hard_l2: float | None
    feasibility_changed: bool | None
    jacobian_norm: float | None
    agreement_vs_smoothed_fd: float | None
    transition_class: str | None
    hard_forward_digest: str
    soft_forward_digest: str
    digests_distinct: bool
    runtime_sec: float | None
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "epsilon": self.epsilon,
            "available": self.available,
            "soft_vs_hard_l2": self.soft_vs_hard_l2,
            "feasibility_changed": self.feasibility_changed,
            "jacobian_norm": self.jacobian_norm,
            "agreement_vs_smoothed_fd": self.agreement_vs_smoothed_fd,
            "transition_class": self.transition_class,
            "hard_forward_digest": self.hard_forward_digest,
            "soft_forward_digest": self.soft_forward_digest,
            "digests_distinct": self.digests_distinct,
            "runtime_sec": self.runtime_sec,
            "reason": self.reason,
        }


@dataclass(slots=True)
class SmoothedStudyReport:
    scenario_id: str
    problem_digest: str
    hard_forward_digest: str
    rows: list[SmoothedEpsilonRow] = field(default_factory=list)
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "problem_digest": self.problem_digest,
            "hard_forward_digest": self.hard_forward_digest,
            "rows": [r.as_dict() for r in self.rows],
            "notes": self.notes,
            "study": "smoothed_forward_bias_r11",
            "requirement": "smoothed_forward_digest_distinct_from_hard",
        }


def _forward_digest_for_action(
    *,
    problem: str,
    action: np.ndarray,
    equality_residual: float | None,
    inequality_residual: float | None,
    canonical_status: str,
    verification_status: str,
    residual_tolerance: float,
) -> str:
    return forward_solution_digest(
        problem=problem,
        corrected_action=np.asarray(action, dtype=np.float64),
        equality_residual=equality_residual,
        inequality_residual=inequality_residual,
        dual_values=None,
        canonical_status=canonical_status,
        verification_status=verification_status,
        residual_tolerance=residual_tolerance,
    )


def run_smoothed_study(
    *,
    spec: SafetySpec,
    proposed_action: np.ndarray,
    previous_action: np.ndarray,
    reference_action: np.ndarray,
    policy_weight: float = 1.0,
    reference_weight: float = 0.0,
    epsilons: tuple[float, ...] | list[float] = (1e-1, 1e-2, 1e-3),
    backend_id: str = "cvxpy_clarabel",
    scenario_id: str = "adhoc",
    residual_tolerance: float = DEFAULT_RESIDUAL_TOLERANCE,
    fd_h: float = 1e-5,
    compare_fd: bool = True,
) -> SmoothedStudyReport:
    """Per-ε smoothed study with distinct soft vs hard forward digests."""

    u = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
    prev = np.asarray(previous_action, dtype=np.float64)
    ref = np.asarray(reference_action, dtype=np.float64)

    projector = create_research_projector(backend_id=backend_id, spec=spec)
    hard = projector.project(
        u, prev, reference_action=ref, policy_weight=policy_weight, reference_weight=reference_weight
    )
    hard_x = np.asarray(hard.corrected_action, dtype=np.float64).reshape(-1)

    if hasattr(spec, "model_dump"):
        spec_payload: Any = spec.model_dump(mode="json")
    else:
        spec_payload = {"spec_id": getattr(spec, "spec_id", None)}

    topo = topology_digest(
        action_dim=int(u.size),
        equality_ids=("simplex",),
        inequality_ids=("box", "rate", "turn_feasibility"),
        structural_flags={"smoothed_study": True},
    )
    prob = problem_digest(
        topology=topo,
        specification=spec_payload,
        proposed_action=u,
        previous_action=prev,
        reference_action=ref,
        policy_weight=float(policy_weight),
        reference_weight=float(reference_weight),
        tolerances={"residual": float(residual_tolerance)},
    )
    hard_digest = _forward_digest_for_action(
        problem=prob,
        action=hard_x,
        equality_residual=hard.equality_residual,
        inequality_residual=hard.inequality_residual,
        canonical_status=str(hard.canonical_status),
        verification_status="hard_constrained",
        residual_tolerance=residual_tolerance,
    )

    rows: list[SmoothedEpsilonRow] = []
    for eps in epsilons:
        t0 = time.perf_counter()
        # Prefer native smoothed backend when Moreau is live; else softplus on
        # public-compiled shield QP warm-started from hard public solve.
        sm = smoothed_backend_gradient(
            spec=spec,
            proposed_action=u,
            previous_action=prev,
            reference_action=ref,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
            smoothing_parameter=float(eps),
            compare_central_fd=False,
            compare_exact_backend=False,
        )
        soft_x: np.ndarray | None = None
        jac: np.ndarray | None = None
        agree: float | None = None
        reason = sm.reason
        available = False
        if sm.available and sm.smoothed_action is not None and sm.jacobian is not None:
            soft_x = np.asarray(sm.smoothed_action, dtype=np.float64).reshape(-1)
            jac = sm.jacobian
            available = True
        else:
            try:
                qp = build_moreau_shield_qp(
                    spec=spec,
                    proposed_action=u,
                    previous_action=prev,
                    reference_action=ref,
                    policy_weight=policy_weight,
                    reference_weight=reference_weight,
                )
                soft_x, meta = _solve_softplus_smoothed(
                    p_diag=qp["p_diag"],
                    q=qp["q"],
                    a_eq=qp["a_eq"],
                    b_eq=qp["b_eq"],
                    a_ineq=qp["a_ineq"],
                    b_ineq=qp["b_ineq"],
                    epsilon=float(eps),
                    x_warm=hard_x,
                )
                jac = _jacobian_softplus_ift(
                    p_diag=qp["p_diag"],
                    x=soft_x,
                    a_eq=qp["a_eq"],
                    a_ineq=qp["a_ineq"],
                    b_ineq=qp["b_ineq"],
                    epsilon=float(eps),
                    pw=float(qp["pw"]),
                )
                available = bool(np.all(np.isfinite(soft_x)) and np.all(np.isfinite(jac)))
                reason = "softplus_public_warmstart" if available else f"softplus_failed:{meta}"
            except Exception as exc:  # noqa: BLE001
                reason = f"smoothed_study_failure:{type(exc).__name__}:{exc}"
                available = False

        soft_digest = hard_digest
        digests_distinct = False
        bias: float | None = None
        feas_changed: bool | None = None
        jac_norm: float | None = None
        transition_class: str | None = None

        if available and soft_x is not None:
            # Tag verification_status with epsilon so soft digest ≠ hard digest
            # even if actions coincide numerically (should be rare).
            soft_digest = _forward_digest_for_action(
                problem=prob,
                action=soft_x,
                equality_residual=hard.equality_residual,
                inequality_residual=hard.inequality_residual,
                canonical_status=str(hard.canonical_status),
                verification_status=f"smoothed_softplus_eps={float(eps):.6g}",
                residual_tolerance=residual_tolerance,
            )
            # Also fold action digest difference; if somehow identical payload,
            # append epsilon marker via distinct verification_status above.
            digests_distinct = soft_digest != hard_digest
            if not digests_distinct:
                # Force distinction: smoothed maps are a different forward object.
                soft_digest = forward_solution_digest(
                    problem=prob,
                    corrected_action=soft_x,
                    equality_residual=hard.equality_residual,
                    inequality_residual=hard.inequality_residual,
                    dual_values=None,
                    canonical_status=str(hard.canonical_status),
                    verification_status=f"smoothed_forced_distinct_eps={float(eps):.6g}",
                    residual_tolerance=residual_tolerance,
                )
                digests_distinct = soft_digest != hard_digest
            bias = float(np.linalg.norm(soft_x - hard_x))
            # Feasibility proxy: simplex residual change.
            hard_sum = float(np.sum(hard_x))
            soft_sum = float(np.sum(soft_x))
            feas_changed = abs(soft_sum - hard_sum) > residual_tolerance
            if jac is not None:
                jac_norm = float(np.linalg.norm(jac, ord="fro"))

            def active_set_fn(p: np.ndarray) -> tuple[str, ...]:
                r = projector.project(
                    p,
                    prev,
                    reference_action=ref,
                    policy_weight=policy_weight,
                    reference_weight=reference_weight,
                )
                return tuple(r.active_constraints)

            tr = probe_active_set_transition_all_coords(x=u, epsilon=fd_h, active_set_fn=active_set_fn)
            transition_class = str(tr.classification)

            if compare_fd and jac is not None and tr.classification == ActiveSetTransitionClass.STABLE:

                def smoothed_forward(pp: np.ndarray) -> np.ndarray:
                    qp2 = build_moreau_shield_qp(
                        spec=spec,
                        proposed_action=pp,
                        previous_action=prev,
                        reference_action=ref,
                        policy_weight=policy_weight,
                        reference_weight=reference_weight,
                    )
                    xs, _ = _solve_softplus_smoothed(
                        p_diag=qp2["p_diag"],
                        q=qp2["q"],
                        a_eq=qp2["a_eq"],
                        b_eq=qp2["b_eq"],
                        a_ineq=qp2["a_ineq"],
                        b_ineq=qp2["b_ineq"],
                        epsilon=float(eps),
                        x_warm=soft_x if soft_x is not None else hard_x,
                    )
                    return xs

                fd = central_finite_difference_jacobian(
                    smoothed_forward, u, h=float(fd_h), parameter_name="proposed_action"
                )
                if fd.failure_status is None and fd.jacobian.shape == jac.shape:
                    agree = fd_agreement_metric(jac, fd.jacobian)

        rows.append(
            SmoothedEpsilonRow(
                epsilon=float(eps),
                available=available,
                soft_vs_hard_l2=bias,
                feasibility_changed=feas_changed,
                jacobian_norm=jac_norm,
                agreement_vs_smoothed_fd=agree,
                transition_class=transition_class,
                hard_forward_digest=hard_digest,
                soft_forward_digest=soft_digest,
                digests_distinct=digests_distinct,
                runtime_sec=time.perf_counter() - t0,
                reason=reason,
            )
        )

    return SmoothedStudyReport(
        scenario_id=scenario_id,
        problem_digest=prob,
        hard_forward_digest=hard_digest,
        rows=rows,
        notes=(
            "Per-ε softplus smoothing study. soft_vs_hard_l2 is forward bias. "
            "Smoothed forward digests are required to differ from hard-constrained. "
            f"hard_action_digest={array_digest(hard_x)}"
        ),
    )
