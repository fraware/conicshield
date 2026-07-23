"""Research-only KKT / implicit sensitivity for the public QP projection.

Mode label: ``exact_research_kkt`` — NOT native Moreau backend gradient.
Never rename or alias this to ``exact_backend_gradient``.

Fail closed when:
- forward solve is infeasible / non-optimal,
- active set is degenerate (weakly active bounds),
- KKT matrix is singular / ill-conditioned,
- active-set identity changes under a micro probe.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.experimental.gradients.capability import CapabilityStatus
from conicshield.experimental.gradients.modes import GradientMode
from conicshield.experimental.solver_assurance.backends import create_research_projector
from conicshield.specs.schema import SafetySpec
from conicshield.specs.shield_qp import parse_safety_spec_for_shield

# Relative gap from bound used to classify weakly-active / interior.
_ACTIVE_TOL = 1e-8
_WEAK_BAND = 1e-5
_COND_LIMIT = 1e12
_PROBE_H = 1e-8


@dataclass(slots=True)
class ResearchKKTGradientResult:
    mode: GradientMode = GradientMode.EXACT_RESEARCH_KKT
    available: bool = False
    status: CapabilityStatus = CapabilityStatus.UNAVAILABLE
    reason: str = ""
    jacobian: np.ndarray | None = None
    active_set: tuple[str, ...] = ()
    kkt_condition_number: float | None = None
    runtime_sec: float | None = None
    agreement_vs_central_fd: float | None = None
    assumptions: tuple[str, ...] = (
        "Fixed active-set linearization of public QP KKT system.",
        "Not a native Moreau / vendor exact_backend_gradient.",
    )
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": str(self.mode),
            "available": self.available,
            "status": str(self.status),
            "reason": self.reason,
            "jacobian": None if self.jacobian is None else self.jacobian.tolist(),
            "active_set": list(self.active_set),
            "kkt_condition_number": self.kkt_condition_number,
            "runtime_sec": self.runtime_sec,
            "agreement_vs_central_fd": self.agreement_vs_central_fd,
            "assumptions": list(self.assumptions),
            "extras": dict(self.extras),
            "evidence_kind": "research_kkt_sensitivity",
            "not_native_moreau": True,
        }


def _fail(
    reason: str,
    *,
    status: CapabilityStatus = CapabilityStatus.UNAVAILABLE,
    active_set: tuple[str, ...] = (),
    runtime_sec: float | None = None,
    extras: dict[str, Any] | None = None,
) -> ResearchKKTGradientResult:
    return ResearchKKTGradientResult(
        available=False,
        status=status,
        reason=reason,
        active_set=active_set,
        runtime_sec=runtime_sec,
        extras=dict(extras or {}),
    )


def _classify_active_bounds(
    *,
    x: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    prev: np.ndarray | None,
    max_delta: np.ndarray | None,
    allowed_mask: np.ndarray,
) -> tuple[list[tuple[str, int, np.ndarray, float]], list[str], str | None]:
    """Return active equality rows (id, coord_or_-1, row, rhs), labels, or fail reason."""

    n = x.size
    rows: list[tuple[str, int, np.ndarray, float]] = []
    labels: list[str] = []

    # Simplex equality always active
    ones = np.ones(n, dtype=np.float64)
    rows.append(("simplex", -1, ones, float(np.sum(x))))  # rhs unused for G dx=0
    labels.append("simplex")

    for i in range(n):
        if not bool(allowed_mask[i]):
            e = np.zeros(n, dtype=np.float64)
            e[i] = 1.0
            rows.append(("turn_feasibility", i, e, 0.0))
            labels.append(f"turn_feasibility[{i}]")
            continue

        dist_lo = float(x[i] - lower[i])
        dist_hi = float(upper[i] - x[i])
        if dist_lo < -_ACTIVE_TOL or dist_hi < -_ACTIVE_TOL:
            return [], [], "infeasible_bound_violation"
        # Degenerate: weakly active band without clear side
        if _ACTIVE_TOL < dist_lo < _WEAK_BAND or _ACTIVE_TOL < dist_hi < _WEAK_BAND:
            return [], [], f"degenerate_weakly_active_box[{i}]"
        if dist_lo <= _ACTIVE_TOL:
            e = np.zeros(n, dtype=np.float64)
            e[i] = 1.0
            rows.append(("box_lower", i, e, float(lower[i])))
            labels.append(f"box_lower[{i}]")
        if dist_hi <= _ACTIVE_TOL:
            e = np.zeros(n, dtype=np.float64)
            e[i] = 1.0
            rows.append(("box_upper", i, e, float(upper[i])))
            labels.append(f"box_upper[{i}]")

    if prev is not None and max_delta is not None:
        for i in range(n):
            up = float((x[i] - prev[i]) - max_delta[i])
            dn = float((prev[i] - x[i]) - max_delta[i])
            if up > _ACTIVE_TOL or dn > _ACTIVE_TOL:
                return [], [], "infeasible_rate_violation"
            near_rate = abs(float(x[i] - prev[i])) > float(max_delta[i]) - _WEAK_BAND
            if (
                (_ACTIVE_TOL < abs(up) < _WEAK_BAND or _ACTIVE_TOL < abs(dn) < _WEAK_BAND)
                and near_rate
            ):
                return [], [], f"degenerate_weakly_active_rate[{i}]"
            if abs(up) <= _ACTIVE_TOL:
                e = np.zeros(n, dtype=np.float64)
                e[i] = 1.0
                rows.append(("rate_upper", i, e, float(prev[i] + max_delta[i])))
                labels.append(f"rate_upper[{i}]")
            if abs(dn) <= _ACTIVE_TOL:
                e = np.zeros(n, dtype=np.float64)
                e[i] = 1.0
                rows.append(("rate_lower", i, e, float(prev[i] - max_delta[i])))
                labels.append(f"rate_lower[{i}]")

    return rows, labels, None


def exact_research_kkt_jacobian(
    *,
    spec: SafetySpec,
    proposed_action: np.ndarray,
    previous_action: np.ndarray | None,
    reference_action: np.ndarray | None = None,
    policy_weight: float = 1.0,
    reference_weight: float = 0.0,
    backend_id: str = "cvxpy_clarabel",
    compare_central_fd: bool = False,
    fd_h: float = 1e-5,
) -> ResearchKKTGradientResult:
    """Compute dx/dp via KKT of the public research QP under a fixed active set."""

    t0 = time.perf_counter()
    p = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
    pw = float(policy_weight)
    rw = float(reference_weight)
    if pw <= 0.0:
        return _fail("policy_weight must be positive", runtime_sec=time.perf_counter() - t0)

    projector = create_research_projector(backend_id=backend_id, spec=spec)
    fwd = projector.project(
        p,
        previous_action,
        reference_action=reference_action,
        policy_weight=pw,
        reference_weight=rw,
    )
    x = np.asarray(fwd.corrected_action, dtype=np.float64).reshape(-1)
    if not np.all(np.isfinite(x)) or "optimal" not in str(fwd.solver_status).lower():
        return _fail(
            f"forward_solve_not_optimal:{fwd.solver_status}",
            active_set=tuple(fwd.active_constraints),
            runtime_sec=time.perf_counter() - t0,
        )

    data = parse_safety_spec_for_shield(spec)
    lower = np.asarray(data.lower, dtype=np.float64)
    upper = np.asarray(data.upper, dtype=np.float64)
    prev = None if previous_action is None else np.asarray(previous_action, dtype=np.float64).reshape(-1)
    max_delta = None if prev is None else np.asarray(data.max_delta, dtype=np.float64)
    allowed = np.asarray(data.allowed_mask, dtype=bool)

    rows, labels, err = _classify_active_bounds(
        x=x,
        lower=lower,
        upper=upper,
        prev=prev,
        max_delta=max_delta,
        allowed_mask=allowed,
    )
    active_set = tuple(sorted(set(labels)))
    if err is not None:
        return _fail(err, active_set=active_set, runtime_sec=time.perf_counter() - t0)

    n = x.size
    m = len(rows)
    if m == 0:
        return _fail("empty_active_set", runtime_sec=time.perf_counter() - t0)

    G = np.stack([r[2] for r in rows], axis=0)  # (m, n)
    # Detect linearly dependent rows
    rank = int(np.linalg.matrix_rank(G, tol=1e-10))
    if rank < m:
        return _fail(
            "singular_or_redundant_active_constraints",
            active_set=active_set,
            runtime_sec=time.perf_counter() - t0,
            extras={"rank": rank, "m": m},
        )

    h_diag = pw + rw
    H = h_diag * np.eye(n, dtype=np.float64)
    kkt = np.zeros((n + m, n + m), dtype=np.float64)
    kkt[:n, :n] = H
    kkt[:n, n:] = G.T
    kkt[n:, :n] = G

    try:
        cond = float(np.linalg.cond(kkt))
    except np.linalg.LinAlgError:
        return _fail("kkt_cond_failed", active_set=active_set, runtime_sec=time.perf_counter() - t0)
    if not np.isfinite(cond) or cond > _COND_LIMIT:
        return _fail(
            "singular_kkt",
            active_set=active_set,
            runtime_sec=time.perf_counter() - t0,
            extras={"kkt_condition_number": cond},
        )

    jac = np.zeros((n, n), dtype=np.float64)
    rhs = np.zeros(n + m, dtype=np.float64)
    try:
        for j in range(n):
            rhs[:] = 0.0
            rhs[j] = pw  # H dx + G^T dν = pw e_j
            sol = np.linalg.solve(kkt, rhs)
            jac[:, j] = sol[:n]
    except np.linalg.LinAlgError:
        return _fail("kkt_solve_failed", active_set=active_set, runtime_sec=time.perf_counter() - t0)

    # Micro-probe: active set must be stable under tiny proposal perturbation
    probe = p.copy()
    probe[0] = probe[0] + _PROBE_H
    probe_res = projector.project(
        probe,
        previous_action,
        reference_action=reference_action,
        policy_weight=pw,
        reference_weight=rw,
    )
    probe_x = np.asarray(probe_res.corrected_action, dtype=np.float64).reshape(-1)
    if not np.all(np.isfinite(probe_x)):
        return _fail(
            "probe_solve_failed",
            active_set=active_set,
            runtime_sec=time.perf_counter() - t0,
        )
    _, probe_labels, probe_err = _classify_active_bounds(
        x=probe_x,
        lower=lower,
        upper=upper,
        prev=prev,
        max_delta=max_delta,
        allowed_mask=allowed,
    )
    if probe_err is not None or set(probe_labels) != set(labels):
        return _fail(
            "active_set_change_under_probe",
            active_set=active_set,
            runtime_sec=time.perf_counter() - t0,
            extras={"probe_active_set": sorted(set(probe_labels)), "probe_err": probe_err},
        )

    agree: float | None = None
    if compare_central_fd:
        from conicshield.experimental.gradients.finite_difference import (
            central_finite_difference_jacobian,
            fd_agreement_metric,
        )

        def forward(pp: np.ndarray) -> np.ndarray:
            r = create_research_projector(backend_id=backend_id, spec=spec).project(
                pp,
                previous_action,
                reference_action=reference_action,
                policy_weight=pw,
                reference_weight=rw,
            )
            return np.asarray(r.corrected_action, dtype=np.float64)

        fd = central_finite_difference_jacobian(forward, p, h=fd_h, parameter_name="proposed_action")
        if fd.failure_status is None and fd.jacobian.shape == jac.shape:
            agree = fd_agreement_metric(jac, fd.jacobian)

    return ResearchKKTGradientResult(
        available=True,
        status=CapabilityStatus.AVAILABLE,
        reason="KKT sensitivity under fixed active set (research adapter; not native Moreau).",
        jacobian=jac,
        active_set=active_set,
        kkt_condition_number=cond,
        runtime_sec=time.perf_counter() - t0,
        agreement_vs_central_fd=agree,
        extras={"n_active_equalities": m, "backend_id": backend_id},
    )
