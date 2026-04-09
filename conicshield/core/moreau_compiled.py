from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from conicshield.core.result import ProjectionResult
from conicshield.core.telemetry import normalize_moreau_info, telemetry_into_projection_fields
from conicshield.solver_errors import require_solver_module
from conicshield.specs.native_moreau_builder import build_moreau_standard_form
from conicshield.specs.schema import SafetySpec
from conicshield.specs.shield_qp import parse_safety_spec_for_shield


@dataclass(frozen=True, slots=True)
class _CSRStructureKey:
    n: int
    m: int
    p_indptr: np.ndarray
    p_indices: np.ndarray
    a_indptr: np.ndarray
    a_indices: np.ndarray

    @staticmethod
    def from_pair(p_csr: sparse.csr_matrix, a_csr: sparse.csr_matrix) -> _CSRStructureKey:
        return _CSRStructureKey(
            n=int(p_csr.shape[0]),
            m=int(a_csr.shape[0]),
            p_indptr=np.asarray(p_csr.indptr, dtype=np.int64),
            p_indices=np.asarray(p_csr.indices, dtype=np.int64),
            a_indptr=np.asarray(a_csr.indptr, dtype=np.int64),
            a_indices=np.asarray(a_csr.indices, dtype=np.int64),
        )


def _csr_structure_matches(key: _CSRStructureKey, p_csr: sparse.csr_matrix, a_csr: sparse.csr_matrix) -> bool:
    if int(p_csr.shape[0]) != key.n or int(a_csr.shape[0]) != key.m:
        return False
    return (
        np.array_equal(p_csr.indptr, key.p_indptr)
        and np.array_equal(p_csr.indices, key.p_indices)
        and np.array_equal(a_csr.indptr, key.a_indptr)
        and np.array_equal(a_csr.indices, key.a_indices)
    )


def _batched_first_objective(solution: Any) -> float | None:
    ov = getattr(solution, "obj_val", None)
    if ov is None:
        return None
    if isinstance(ov, list | tuple) and ov:
        try:
            return float(ov[0])
        except (TypeError, ValueError):
            return None
    try:
        arr = np.asarray(ov, dtype=np.float64)
        if arr.size == 0:
            return None
        return float(arr.reshape(-1)[0])
    except (TypeError, ValueError):
        return None


def _batched_info_status_for_unbatch(info: Any) -> Any:
    if info is None:
        return None
    st = getattr(info, "status", None)
    if isinstance(st, list | tuple) and st:
        return st[0]
    return st


def _batched_info_iterations_for_unbatch(info: Any) -> Any:
    if info is None:
        return None
    it = getattr(info, "iterations", None)
    if isinstance(it, list | tuple) and it:
        return it[0]
    return it


@dataclass(slots=True)
class NativeMoreauCompiledOptions:
    device: str = "cpu"
    auto_tune: bool = False
    enable_grad: bool = False
    max_iter: int = 200
    time_limit: float = float("inf")
    verbose: bool = False
    active_tol: float = 1e-6
    persist_warm_start: bool = True
    policy_weight: float = 1.0
    reference_weight: float = 0.0
    #: Use ``moreau.CompiledSolver`` (shared-structure path). Set False to force legacy ``Solver``.
    use_compiled_solver: bool = True


class NativeMoreauCompiledProjector:
    """Shield projector via Moreau ``CompiledSolver`` (batch size 1) when available; else ``Solver``."""

    def __init__(
        self,
        *,
        spec: SafetySpec,
        options: NativeMoreauCompiledOptions | None = None,
    ) -> None:
        self.spec = spec
        self.options = options or NativeMoreauCompiledOptions()
        self._warm: Any = None
        self._compiled: Any = None
        self._csr_key: _CSRStructureKey | None = None
        self._compiled_settings_key: tuple[Any, ...] | None = None

    def _moreau_settings(self, moreau: Any) -> Any:
        dev = self.options.device
        if dev in ("auto", ""):
            dev = "cpu"
        settings_kw: dict[str, Any] = {
            "max_iter": int(self.options.max_iter),
            "verbose": bool(self.options.verbose),
            "batch_size": 1,
        }
        if np.isfinite(self.options.time_limit) and self.options.time_limit > 0:
            settings_kw["time_limit"] = float(self.options.time_limit)
        for opt_key in ("auto_tune", "enable_grad"):
            val = getattr(self.options, opt_key, None)
            if val is not None:
                settings_kw[opt_key] = bool(val)
        return moreau.Settings(device=str(dev), **settings_kw)

    def _compiled_settings_fingerprint(self, moreau: Any) -> tuple[Any, ...]:
        s = self._moreau_settings(moreau)
        return (
            str(getattr(s, "device", "")),
            int(getattr(s, "max_iter", 0)),
            float(getattr(s, "time_limit", 0.0)),
            bool(getattr(s, "verbose", False)),
            bool(getattr(s, "auto_tune", False)),
            bool(getattr(s, "enable_grad", False)),
            int(getattr(s, "batch_size", 1)),
        )

    def _solve_with_compiled(
        self,
        moreau: Any,
        p_csr: sparse.csr_matrix,
        q: np.ndarray,
        a_csr: sparse.csr_matrix,
        b_full: np.ndarray,
        cones: Any,
        *,
        warm: Any | None,
    ) -> tuple[np.ndarray, Any, Any, float | None, bool]:
        settings = self._moreau_settings(moreau)
        fp = self._compiled_settings_fingerprint(moreau)
        key = _CSRStructureKey.from_pair(p_csr, a_csr)
        need_build = (
            self._compiled is None
            or self._compiled_settings_key != fp
            or self._csr_key is None
            or not _csr_structure_matches(self._csr_key, p_csr, a_csr)
        )
        if need_build:
            self._compiled = moreau.CompiledSolver(
                n=key.n,
                m=key.m,
                P_row_offsets=p_csr.indptr,
                P_col_indices=p_csr.indices,
                A_row_offsets=a_csr.indptr,
                A_col_indices=a_csr.indices,
                cones=cones,
                settings=settings,
            )
            self._csr_key = key
            self._compiled_settings_key = fp
            self._warm = None

        solver = self._compiled
        solver.setup(np.asarray(p_csr.data, dtype=np.float64), np.asarray(a_csr.data, dtype=np.float64))
        q2 = np.asarray(q, dtype=np.float64).reshape(1, -1)
        b2 = np.asarray(b_full, dtype=np.float64).reshape(1, -1)
        solution = solver.solve(qs=q2, bs=b2, warm_start=warm)
        xbat = np.asarray(solution.x, dtype=np.float64)
        xv = (
            xbat[0].reshape(-1)
            if xbat.ndim == 2 and xbat.shape[0] >= 1
            else xbat.reshape(-1)
        )
        obj = _batched_first_objective(solution)
        warm_started = warm is not None
        return xv, solver, solution, obj, warm_started

    def _solve_with_legacy_solver(
        self,
        moreau: Any,
        p_csr: sparse.csr_matrix,
        q: np.ndarray,
        a_csr: sparse.csr_matrix,
        b_full: np.ndarray,
        cones: Any,
        *,
        warm: Any | None,
    ) -> tuple[np.ndarray, Any, Any, float | None, bool]:
        settings = self._moreau_settings(moreau)
        solver = moreau.Solver(p_csr, q, a_csr, b_full, cones=cones, settings=settings)
        warm_started = warm is not None
        solution = solver.solve(warm_start=warm)
        xv = np.asarray(solution.x, dtype=np.float64).reshape(-1)
        obj = None
        if hasattr(solution, "obj_val"):
            try:
                obj = float(solution.obj_val)
            except (TypeError, ValueError):
                obj = None
        return xv, solver, solution, obj, warm_started

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
        require_solver_module("moreau", "native Moreau projector")
        import moreau

        data = parse_safety_spec_for_shield(self.spec)
        p_csr, q, a_csr, b_full, cones = build_moreau_standard_form(
            data,
            proposed_action,
            previous_action,
            reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
        )

        warm = self._warm if self.options.persist_warm_start else None
        use_compiled = bool(self.options.use_compiled_solver) and hasattr(moreau, "CompiledSolver")

        try:
            if use_compiled:
                xv, solver, solution, obj, warm_started = self._solve_with_compiled(
                    moreau, p_csr, q, a_csr, b_full, cones, warm=warm
                )
            else:
                self._compiled = None
                self._csr_key = None
                self._compiled_settings_key = None
                xv, solver, solution, obj, warm_started = self._solve_with_legacy_solver(
                    moreau, p_csr, q, a_csr, b_full, cones, warm=warm
                )
        except Exception:
            self._warm = None
            raise

        if self.options.persist_warm_start and hasattr(solution, "to_warm_start"):
            try:
                self._warm = solution.to_warm_start()
            except Exception:
                self._warm = None
        elif not self.options.persist_warm_start:
            self._warm = None

        proposed = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
        diff = float(np.linalg.norm(xv - proposed))
        intervened = diff > 1e-8

        info = getattr(solver, "info", None)
        if use_compiled and info is not None:
            info_view = {
                "status": _batched_info_status_for_unbatch(info),
                "objective": _batched_first_objective(solution),
                "obj_val": _batched_first_objective(solution),
                "solve_time": getattr(info, "solve_time", None),
                "solve_time_sec": getattr(info, "solve_time", None),
                "setup_time": getattr(info, "setup_time", None),
                "setup_time_sec": getattr(info, "setup_time", None),
                "construction_time": getattr(info, "construction_time", None),
                "construction_time_sec": getattr(info, "construction_time", None),
                "iterations": _batched_info_iterations_for_unbatch(info),
                "device": getattr(info, "device", None),
            }
            tel = normalize_moreau_info(info_view, warm_started=warm_started, objective_value=obj)
        else:
            tel = normalize_moreau_info(info, warm_started=warm_started, objective_value=obj)
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
