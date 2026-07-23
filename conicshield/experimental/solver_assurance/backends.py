"""Research solver backends for primary/shadow comparisons.

Public Clarabel/SCS paths are implemented. Native Moreau, CUDA, and Windows
sidecar backends are stubbed clearly when unavailable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

import numpy as np

from conicshield.experimental.adapters.projection import ResearchProjectionResult
from conicshield.experimental.adapters.track1_protocols import (
    CanonicalSolverStatus,
    SolverProvenance,
)
from conicshield.specs.schema import SafetySpec
from conicshield.specs.shield_qp import parse_safety_spec_for_shield

BackendKind = Literal[
    "cvxpy_clarabel",
    "cvxpy_scs",
    "cvxpy_moreau",
    "native_moreau_cpu",
    "native_moreau_cuda",
    "windows_sidecar",
]


@dataclass(slots=True)
class BackendCapability:
    backend_id: str
    available: bool
    reason: str | None = None
    stub: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _map_status(raw: str | None) -> CanonicalSolverStatus:
    s = (raw or "").lower()
    if "optimal" in s:
        return CanonicalSolverStatus.OPTIMAL
    if "infeas" in s:
        return CanonicalSolverStatus.INFEASIBLE
    if "unbound" in s:
        return CanonicalSolverStatus.UNBOUNDED
    if "user_limit" in s or "iteration" in s:
        return CanonicalSolverStatus.ITERATION_LIMIT
    if "time" in s:
        return CanonicalSolverStatus.TIME_LIMIT
    if "numeric" in s or "error" in s:
        return CanonicalSolverStatus.NUMERICAL_FAILURE
    return CanonicalSolverStatus.UNKNOWN


def _residuals(
    *,
    x: np.ndarray,
    data: Any,
    previous: np.ndarray | None,
) -> tuple[float, float, list[str]]:
    eq = abs(float(np.sum(x) - data.simplex_total))
    ineq = 0.0
    active: list[str] = []
    lower = np.asarray(data.lower, dtype=np.float64)
    upper = np.asarray(data.upper, dtype=np.float64)
    lo_viol = np.maximum(lower - x, 0.0)
    hi_viol = np.maximum(x - upper, 0.0)
    ineq += float(np.sum(lo_viol) + np.sum(hi_viol))
    if np.any(lo_viol > 1e-8) or np.any((x - lower) <= 1e-8):
        active.append("box_lower")
    if np.any(hi_viol > 1e-8) or np.any((upper - x) <= 1e-8):
        active.append("box_upper")
    if previous is not None:
        d = np.asarray(data.max_delta, dtype=np.float64)
        rate_viol = np.maximum(np.abs(x - previous) - d, 0.0)
        ineq += float(np.sum(rate_viol))
        if np.any(np.abs(x - previous) >= d - 1e-8):
            active.append("rate")
    if np.any(~np.asarray(data.allowed_mask)):
        mask_viol = np.abs(x * (~data.allowed_mask.astype(bool)))
        ineq += float(np.sum(mask_viol))
        if np.any(~data.allowed_mask):
            active.append("turn_feasibility")
    if abs(float(np.sum(x) - data.simplex_total)) <= 1e-8:
        active.append("simplex")
    return eq, ineq, sorted(set(active))


@dataclass
class PublicCvxpyProjector:
    """Research-only public CVXPY projector (Clarabel or SCS)."""

    spec: SafetySpec
    solver_name: str = "CLARABEL"
    backend_id: str = "cvxpy_clarabel"
    max_iter: int | None = None
    time_limit: float | None = None
    warm_start: bool = False
    verbose: bool = False
    _last_x: np.ndarray | None = field(default=None, init=False, repr=False)

    def project(
        self,
        proposed_action: np.ndarray,
        previous_action: np.ndarray | None = None,
        *,
        reference_action: np.ndarray | None = None,
        policy_weight: float = 1.0,
        reference_weight: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchProjectionResult:
        import cvxpy as cp

        data = parse_safety_spec_for_shield(self.spec)
        n = data.n
        x = cp.Variable(n)
        if self.warm_start and self._last_x is not None and self._last_x.shape == (n,):
            x.value = self._last_x.copy()

        cons: list[Any] = [
            cp.sum(x) == float(data.simplex_total),
            x >= np.asarray(data.lower, dtype=np.float64),
            x <= np.asarray(data.upper, dtype=np.float64),
        ]
        for i in range(n):
            if not data.allowed_mask[i]:
                cons.append(x[i] == 0)

        prev = None
        if previous_action is not None:
            prev = np.asarray(previous_action, dtype=np.float64).reshape(-1)
            d = np.asarray(data.max_delta, dtype=np.float64)
            cons.append(x - prev <= d)
            cons.append(prev - x <= d)

        p = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
        pw = float(policy_weight)
        rw = float(reference_weight)
        if reference_action is not None and rw > 0.0:
            r = np.asarray(reference_action, dtype=np.float64).reshape(-1)
            objective = cp.Minimize(pw * cp.sum_squares(x - p) + rw * cp.sum_squares(x - r))
        else:
            objective = cp.Minimize(pw * cp.sum_squares(x - p))

        problem = cp.Problem(objective, cons)
        solver = getattr(cp, self.solver_name)
        solve_kw: dict[str, Any] = {"solver": solver, "verbose": self.verbose}
        if self.max_iter is not None:
            # Clarabel/SCS accept different kwargs; pass common ones best-effort
            if self.solver_name.upper() == "SCS":
                solve_kw["max_iters"] = int(self.max_iter)
            else:
                solve_kw["max_iter"] = int(self.max_iter)
        if self.time_limit is not None:
            solve_kw["time_limit"] = float(self.time_limit)

        status = "unknown"
        try:
            problem.solve(**solve_kw)
            status = str(problem.status)
        except Exception as exc:  # noqa: BLE001 — research harness records failures
            return ResearchProjectionResult(
                proposed_action=p,
                corrected_action=np.full(n, np.nan),
                intervened=True,
                intervention_norm=float("nan"),
                solver_status=f"error:{type(exc).__name__}",
                canonical_status=CanonicalSolverStatus.NUMERICAL_FAILURE,
                metadata={"error": str(exc), **dict(metadata or {})},
            )

        if x.value is None:
            xv = np.full(n, np.nan)
            eq: float = float("nan")
            ineq: float = float("nan")
            active: list[str] = []
            intervened = True
            diff = float("nan")
            obj = None
        else:
            xv = np.asarray(x.value, dtype=np.float64).reshape(-1)
            self._last_x = xv.copy()
            eq, ineq, active = _residuals(x=xv, data=data, previous=prev)
            diff = float(np.linalg.norm(xv - p))
            intervened = diff > 1e-8
            obj = float(problem.value) if problem.value is not None else None

        return ResearchProjectionResult(
            proposed_action=p,
            corrected_action=xv,
            intervened=intervened,
            intervention_norm=diff,
            solver_status=status,
            canonical_status=_map_status(status),
            objective_value=obj,
            active_constraints=active,
            warm_started=bool(self.warm_start),
            equality_residual=eq if eq == eq else None,  # NaN check
            inequality_residual=ineq if ineq == ineq else None,
            provenance=SolverProvenance(
                backend_id=self.backend_id,
                solver_name=self.solver_name,
                solver_version=getattr(cp, "__version__", None),
                package_distribution="cvxpy",
                package_version=getattr(cp, "__version__", None),
                device="cpu",
                algorithm=self.solver_name.lower(),
                settings={"max_iter": self.max_iter, "time_limit": self.time_limit},
                warm_start_policy="reuse_last_x" if self.warm_start else "cold",
            ),
            metadata=dict(metadata or {}),
        )


@dataclass
class StubBackendProjector:
    """Explicit stub for unavailable research backends."""

    backend_id: str
    reason: str

    def project(
        self,
        proposed_action: np.ndarray,
        previous_action: np.ndarray | None = None,
        *,
        reference_action: np.ndarray | None = None,
        policy_weight: float = 1.0,
        reference_weight: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchProjectionResult:
        p = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
        _ = (previous_action, reference_action, policy_weight, reference_weight)
        return ResearchProjectionResult(
            proposed_action=p,
            corrected_action=np.full_like(p, np.nan),
            intervened=True,
            intervention_norm=float("nan"),
            solver_status="unavailable",
            canonical_status=CanonicalSolverStatus.UNAVAILABLE,
            metadata={"stub": True, "reason": self.reason, **dict(metadata or {})},
            provenance=SolverProvenance(
                backend_id=self.backend_id,
                solver_name="stub",
                solver_version=None,
                package_distribution=None,
                package_version=None,
                platform_note=self.reason,
            ),
        )


def probe_backend_capabilities() -> list[BackendCapability]:
    caps: list[BackendCapability] = []

    try:
        import cvxpy as cp

        for name, bid in (("CLARABEL", "cvxpy_clarabel"), ("SCS", "cvxpy_scs")):
            available = getattr(cp, name, None) is not None
            caps.append(
                BackendCapability(
                    backend_id=bid,
                    available=available,
                    reason=None if available else f"cvxpy.{name} missing",
                )
            )
        moreau_solver = getattr(cp, "MOREAU", None)
        caps.append(
            BackendCapability(
                backend_id="cvxpy_moreau",
                available=moreau_solver is not None,
                reason=None if moreau_solver is not None else "cp.MOREAU unavailable (vendor)",
                stub=moreau_solver is None,
            )
        )
    except ImportError:
        for bid in ("cvxpy_clarabel", "cvxpy_scs", "cvxpy_moreau"):
            caps.append(BackendCapability(backend_id=bid, available=False, reason="cvxpy missing", stub=True))

    try:
        import moreau as moreau_pkg  # noqa: F401

        _ = moreau_pkg
        caps.append(BackendCapability(backend_id="native_moreau_cpu", available=True))
        # CUDA availability is environment-specific; treat as optional probe
        cuda_ok = False
        try:
            import torch

            cuda_ok = bool(torch.cuda.is_available())
        except Exception:
            cuda_ok = False
        caps.append(
            BackendCapability(
                backend_id="native_moreau_cuda",
                available=cuda_ok,
                reason=None if cuda_ok else "CUDA not available",
                stub=not cuda_ok,
            )
        )
    except ImportError:
        caps.append(
            BackendCapability(
                backend_id="native_moreau_cpu",
                available=False,
                reason="moreau package not installed",
                stub=True,
            )
        )
        caps.append(
            BackendCapability(
                backend_id="native_moreau_cuda",
                available=False,
                reason="moreau package not installed",
                stub=True,
            )
        )

    caps.append(
        BackendCapability(
            backend_id="windows_sidecar",
            available=False,
            reason="Windows-sidecar execution not implemented in wave 1 (stub)",
            stub=True,
        )
    )
    return caps


def create_research_projector(
    *,
    backend_id: str,
    spec: SafetySpec,
    warm_start: bool = False,
    max_iter: int | None = None,
    time_limit: float | None = None,
) -> PublicCvxpyProjector | StubBackendProjector:
    caps = {c.backend_id: c for c in probe_backend_capabilities()}
    cap = caps.get(backend_id)
    if backend_id == "cvxpy_clarabel" and cap and cap.available:
        return PublicCvxpyProjector(
            spec=spec,
            solver_name="CLARABEL",
            backend_id=backend_id,
            warm_start=warm_start,
            max_iter=max_iter,
            time_limit=time_limit,
        )
    if backend_id == "cvxpy_scs" and cap and cap.available:
        return PublicCvxpyProjector(
            spec=spec,
            solver_name="SCS",
            backend_id=backend_id,
            warm_start=warm_start,
            max_iter=max_iter,
            time_limit=time_limit,
        )
    if backend_id == "cvxpy_moreau" and cap and cap.available:
        return PublicCvxpyProjector(
            spec=spec,
            solver_name="MOREAU",
            backend_id=backend_id,
            warm_start=warm_start,
            max_iter=max_iter,
            time_limit=time_limit,
        )
    reason = cap.reason if cap else f"unknown backend {backend_id}"
    return StubBackendProjector(backend_id=backend_id, reason=reason or "unavailable")
