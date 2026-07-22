"""Heterogeneous batched ``CompiledSolver`` projection with complete per-row evidence."""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

import numpy as np
from numpy.typing import ArrayLike

from conicshield.backends.status import normalize_moreau_status
from conicshield.compilation.capabilities import (
    CompilationCapabilities,
    resolve_capabilities,
)
from conicshield.compilation.compiled_template import CompiledShieldTemplate, NumericBuffers
from conicshield.compilation.metrics import LifecycleMetrics
from conicshield.compilation.solver_pool import SolverPool
from conicshield.core.interfaces import ConcurrencyModel
from conicshield.core.result import BatchProjectionResult, ProjectionResult
from conicshield.core.telemetry import normalize_moreau_info
from conicshield.solver_errors import require_solver_module
from conicshield.specs.schema import SafetySpec
from conicshield.specs.shield_qp import ShieldQPData, parse_safety_spec_for_shield
from conicshield.verification.feasibility import require_verified_release
from conicshield.verification.release import provenance_for_backend
from conicshield.verification.release_policy import ReleasePolicy, intervention_threshold
from conicshield.verification.residuals import ResidualTolerances

from .moreau_compiled import NativeMoreauCompiledOptions


def _as_batch_matrix(
    value: ArrayLike | None,
    *,
    batch_size: int,
    n: int,
    name: str,
) -> np.ndarray | None:
    if value is None:
        return None
    arr = np.asarray(value, dtype=np.float64)
    if arr.ndim == 1:
        if arr.shape[0] != n:
            raise ValueError(f"{name} length {arr.shape[0]} != action_dim {n}")
        return np.broadcast_to(arr.reshape(1, n), (batch_size, n)).copy()
    if arr.ndim != 2:
        raise ValueError(f"{name} must be 1D or 2D, got shape {arr.shape}")
    if arr.shape != (batch_size, n):
        raise ValueError(f"{name} shape {arr.shape} != ({batch_size}, {n})")
    return arr


def _as_weight_vector(
    value: ArrayLike | float,
    *,
    batch_size: int,
    name: str,
) -> np.ndarray:
    arr = np.asarray(value, dtype=np.float64)
    if arr.ndim == 0:
        return np.full(batch_size, float(arr), dtype=np.float64)
    if arr.ndim == 1 and arr.shape[0] == batch_size:
        return arr.astype(np.float64, copy=True)
    raise ValueError(f"{name} must be a scalar or length-{batch_size} vector, got shape {arr.shape}")


def _override_data(
    base: ShieldQPData,
    *,
    lower_row: np.ndarray | None,
    upper_row: np.ndarray | None,
    max_delta_row: np.ndarray | None,
) -> ShieldQPData:
    lower = base.lower if lower_row is None else np.asarray(lower_row, dtype=np.float64).reshape(-1)
    upper = base.upper if upper_row is None else np.asarray(upper_row, dtype=np.float64).reshape(-1)
    max_delta = (
        base.max_delta
        if max_delta_row is None
        else np.asarray(max_delta_row, dtype=np.float64).reshape(-1)
    )
    if lower is base.lower and upper is base.upper and max_delta is base.max_delta:
        return base
    return replace(
        base,
        lower=np.asarray(lower, dtype=np.float64).copy(),
        upper=np.asarray(upper, dtype=np.float64).copy(),
        max_delta=np.asarray(max_delta, dtype=np.float64).copy(),
    )


def _objective_at(obj: Any, index: int) -> float | None:
    if obj is None:
        return None
    if isinstance(obj, list | tuple):
        if index < len(obj):
            try:
                return float(obj[index])
            except (TypeError, ValueError):
                return None
        return None
    try:
        arr = np.asarray(obj, dtype=np.float64).reshape(-1)
        if arr.size == 0:
            return None
        if index < arr.size:
            return float(arr[index])
        return float(arr[0])
    except (TypeError, ValueError):
        return None


def _status_at(raw: Any, index: int, batch_size: int) -> Any:
    if isinstance(raw, list | tuple):
        if index < len(raw):
            return raw[index]
        return raw[-1] if raw else None
    if isinstance(raw, np.ndarray) and raw.ndim >= 1 and raw.size == batch_size:
        return raw.reshape(-1)[index]
    return raw


def _iterations_at(raw: Any, index: int, batch_size: int) -> int | None:
    v = _status_at(raw, index, batch_size)
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


class NativeMoreauCompiledBatchProjector:
    """Batched native projector over a fixed ``CompiledShieldTemplate``.

    Rows share structural topology and may differ in proposals, previous /
    reference actions, weights, and numeric bounds/rates. When ``P`` / ``A``
    setup values match across the batch, one ``CompiledSolver.solve(qs, bs)``
    is used; otherwise rows are solved sequentially on a batch-size-1 compiled
    solver with setup skipping. Warm starts are keyed by stable ``row_ids``.
    """

    concurrency_model: ConcurrencyModel = ConcurrencyModel.INSTANCE_CONFINED

    def __init__(
        self,
        *,
        spec: SafetySpec,
        options: NativeMoreauCompiledOptions | None = None,
        metrics: LifecycleMetrics | None = None,
        capabilities: CompilationCapabilities | None = None,
        solver_pool: SolverPool[Any] | None = None,
    ) -> None:
        self.spec = spec
        self.options = options or NativeMoreauCompiledOptions()
        self.metrics = metrics if metrics is not None else LifecycleMetrics()
        self.capabilities = resolve_capabilities(capabilities)
        if self.capabilities.enable_direct_variable_cones:
            raise ValueError(
                "enable_direct_variable_cones is gated off until parity/benchmark gates pass"
            )
        self._solver_pool = solver_pool
        if solver_pool is not None:
            self.concurrency_model = ConcurrencyModel.POOLED_EXCLUSIVE_CHECKOUT

        base = parse_safety_spec_for_shield(spec)
        self._base_data = base
        self._template = CompiledShieldTemplate.compile(base)
        self._buffers = self._template.allocate_buffers()
        self._warm_by_row: dict[str, Any] = {}
        self._compiled_batch: Any = None
        self._compiled_single: Any = None
        self._batch_k: int | None = None
        self._batch_settings_key: tuple[Any, ...] | None = None
        self._single_settings_key: tuple[Any, ...] | None = None
        self._last_setup_fp_batch: str | None = None
        self._last_setup_fp_single: str | None = None
        self._a_constants_loaded = False

    @property
    def template(self) -> CompiledShieldTemplate:
        return self._template

    @property
    def structural_fingerprint(self) -> str:
        return self._template.structural_fingerprint

    def reset_state(self, *, scope_id: str | None = None) -> None:
        """Clear warm starts for all rows, or only those containing ``scope_id``."""
        if scope_id is None:
            self._warm_by_row.clear()
            return
        drop = [k for k in self._warm_by_row if scope_id in k]
        for k in drop:
            del self._warm_by_row[k]

    def bind_spec(self, spec: SafetySpec) -> str:
        """Refresh numeric IR / rebuild template when topology changes."""
        data = parse_safety_spec_for_shield(spec)
        new_template = CompiledShieldTemplate.compile(data)
        self.spec = spec
        self._base_data = data
        if new_template.structural_fingerprint == self._template.structural_fingerprint:
            self._template = new_template
            return "reused"
        self._template = new_template
        self._buffers = self._template.allocate_buffers()
        self._compiled_batch = None
        self._compiled_single = None
        self._batch_k = None
        self._batch_settings_key = None
        self._single_settings_key = None
        self._last_setup_fp_batch = None
        self._last_setup_fp_single = None
        self._a_constants_loaded = False
        self._warm_by_row.clear()
        self.metrics.record_solver_rebuild()
        return "rebuild"

    def _moreau_settings(self, moreau: Any, *, batch_size: int) -> Any:
        dev = self.options.device
        if dev in ("auto", ""):
            dev = "cpu"
        settings_kw: dict[str, Any] = {
            "max_iter": int(self.options.max_iter),
            "verbose": bool(self.options.verbose),
            "batch_size": int(batch_size),
        }
        if np.isfinite(self.options.time_limit) and self.options.time_limit > 0:
            settings_kw["time_limit"] = float(self.options.time_limit)
        auto_tune = bool(self.options.auto_tune)
        # Investigation flag must not enable autotune unless options also request it.
        if auto_tune:
            settings_kw["auto_tune"] = True
        if self.capabilities.enable_cpu_algorithm_autotune and not auto_tune:
            # Documented no-op: flag alone does not change solver settings.
            pass
        for opt_key in ("enable_grad",):
            val = getattr(self.options, opt_key, None)
            if val is not None:
                settings_kw[opt_key] = bool(val)
        return moreau.Settings(device=str(dev), **settings_kw)

    def _settings_fingerprint(self, moreau: Any, *, batch_size: int) -> tuple[Any, ...]:
        s = self._moreau_settings(moreau, batch_size=batch_size)
        return (
            int(batch_size),
            str(getattr(s, "device", "")),
            int(getattr(s, "max_iter", 0)),
            float(getattr(s, "time_limit", 0.0)),
            bool(getattr(s, "verbose", False)),
            bool(getattr(s, "auto_tune", False)),
            bool(getattr(s, "enable_grad", False)),
            self._template.structural_fingerprint,
        )

    def _row_ids(
        self,
        row_ids: Sequence[str] | None,
        *,
        batch_size: int,
    ) -> tuple[str, ...]:
        if row_ids is None:
            return tuple(f"__anonymous_row__:{i}" for i in range(batch_size))
        ids = tuple(str(t) for t in row_ids)
        if len(ids) != batch_size:
            raise ValueError(f"row_ids length {len(ids)} must match batch size {batch_size}")
        if len(set(ids)) != len(ids):
            raise ValueError("row_ids must be unique within a batch")
        return ids

    def _release_policy(self) -> ReleasePolicy:
        return ReleasePolicy(
            accept_optimal_inaccurate=bool(self.options.accept_optimal_inaccurate),
            accept_iteration_limit=bool(self.options.accept_iteration_limit),
            accept_time_limit=bool(self.options.accept_time_limit),
            tolerances=ResidualTolerances(
                abs_tol=float(self.options.abs_tol),
                rel_tol=float(self.options.rel_tol),
                active_tol=float(self.options.active_tol),
            ),
            intervention_abs_tol=float(self.options.intervention_abs_tol),
            intervention_rel_tol=float(self.options.intervention_rel_tol),
        )

    def _build_compiled(self, moreau: Any, *, batch_size: int) -> Any:
        settings = self._moreau_settings(moreau, batch_size=batch_size)
        cones = self._template.moreau_cones(moreau)
        return moreau.CompiledSolver(
            n=self._template.layout.n,
            m=self._template.layout.m,
            P_row_offsets=self._template.p_indptr,
            P_col_indices=self._template.p_indices,
            A_row_offsets=self._template.a_indptr,
            A_col_indices=self._template.a_indices,
            cones=cones,
            settings=settings,
        )

    def _ensure_batch_solver(self, moreau: Any, *, batch_size: int) -> tuple[Any, str]:
        fp = self._settings_fingerprint(moreau, batch_size=batch_size)
        if (
            self._compiled_batch is not None
            and self._batch_k == batch_size
            and self._batch_settings_key == fp
        ):
            return self._compiled_batch, "hit"
        self._compiled_batch = self._build_compiled(moreau, batch_size=batch_size)
        self._batch_k = batch_size
        self._batch_settings_key = fp
        self._last_setup_fp_batch = None
        self.metrics.record_solver_rebuild()
        return self._compiled_batch, "rebuild"

    def _ensure_single_solver(self, moreau: Any) -> tuple[Any, str]:
        fp = self._settings_fingerprint(moreau, batch_size=1)
        if self._compiled_single is not None and self._single_settings_key == fp:
            return self._compiled_single, "hit"
        self._compiled_single = self._build_compiled(moreau, batch_size=1)
        self._single_settings_key = fp
        self._last_setup_fp_single = None
        self.metrics.record_solver_rebuild()
        return self._compiled_single, "rebuild"

    def _setup(
        self,
        solver: Any,
        *,
        setup_fp: str,
        buffers: NumericBuffers,
        mode: str,
    ) -> tuple[float | None, bool]:
        last = self._last_setup_fp_batch if mode == "batch" else self._last_setup_fp_single
        if last == setup_fp:
            self.metrics.record_setup_reuse()
            return None, True
        t0 = time.perf_counter()
        solver.setup(buffers.p_values, buffers.a_values)
        dt = float(time.perf_counter() - t0)
        if mode == "batch":
            self._last_setup_fp_batch = setup_fp
        else:
            self._last_setup_fp_single = setup_fp
        return dt, False

    def _build_row_result(
        self,
        *,
        proposed: np.ndarray,
        corrected: np.ndarray,
        data: ShieldQPData,
        previous: np.ndarray | None,
        reference: np.ndarray | None,
        policy_weight: float,
        reference_weight: float,
        raw_status: Any,
        objective: float | None,
        iterations: int | None,
        warm_started: bool,
        row_id: str,
        release_policy: ReleasePolicy,
        provenance: Any,
        device: str | None,
        setup_time_sec: float | None,
        solve_time_sec: float | None,
    ) -> ProjectionResult:
        report = require_verified_release(
            corrected,
            data,
            raw_status=raw_status,
            previous_action=previous,
            proposed_action=proposed,
            reference_action=reference,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
            reported_objective=objective,
            policy=release_policy,
            attempt_kind="primary",
            status_normalizer=normalize_moreau_status,
        )
        diff = float(np.linalg.norm(corrected - proposed))
        thr = intervention_threshold(
            proposed,
            abs_tol=release_policy.intervention_abs_tol,
            rel_tol=release_policy.intervention_rel_tol,
        )
        tel = normalize_moreau_info(
            {
                "status": raw_status,
                "objective": objective,
                "iterations": iterations,
                "device": device,
                "solve_time": solve_time_sec,
                "setup_time": setup_time_sec,
            },
            warm_started=warm_started,
            objective_value=objective,
        )
        decision = report.classification.decision
        return ProjectionResult(
            proposed_action=proposed.copy(),
            corrected_action=corrected.copy(),
            intervened=diff > thr,
            intervention_norm=diff,
            solver_status=str(tel.get("solver_status") or report.canonical_status.value),
            objective_value=tel.get("objective_value"),
            active_constraints=list(report.active_constraints),
            warm_started=bool(tel.get("warm_started", False)),
            solve_time_sec=tel.get("solve_time_sec"),
            setup_time_sec=tel.get("setup_time_sec"),
            iterations=tel.get("iterations"),
            device=tel.get("device"),
            metadata={"row_id": row_id},
            canonical_status=report.canonical_status,
            release_decision=decision,
            verification=report,
            solver_provenance=provenance,
            fallback_history=(),
        )

    def project_batch(
        self,
        proposed_actions: ArrayLike,
        previous_actions: ArrayLike | None = None,
        *,
        reference_actions: ArrayLike | None = None,
        policy_weights: ArrayLike | float = 1.0,
        reference_weights: ArrayLike | float = 0.0,
        row_ids: Sequence[str] | None = None,
        lowers: ArrayLike | None = None,
        uppers: ArrayLike | None = None,
        max_deltas: ArrayLike | None = None,
        previous_action: ArrayLike | None = None,
        reference_action: ArrayLike | None = None,
        policy_weight: float | None = None,
        reference_weight: float | None = None,
        trajectory_ids: Sequence[str] | None = None,
    ) -> BatchProjectionResult:
        """Project ``K`` rows sharing topology; return complete per-row evidence."""
        require_solver_module("moreau", "native Moreau batch projector")
        import moreau

        if not hasattr(moreau, "CompiledSolver"):
            raise RuntimeError("moreau.CompiledSolver is required for batched shield projection")

        if previous_actions is None and previous_action is not None:
            previous_actions = previous_action
        if reference_actions is None and reference_action is not None:
            reference_actions = reference_action
        if policy_weight is not None:
            policy_weights = policy_weight
        if reference_weight is not None:
            reference_weights = reference_weight
        if row_ids is None and trajectory_ids is not None:
            row_ids = trajectory_ids

        pb = np.asarray(proposed_actions, dtype=np.float64)
        if pb.ndim != 2:
            raise ValueError("proposed_actions must have shape (batch, action_dim)")
        k_batch, n = pb.shape
        if k_batch < 1:
            raise ValueError("batch size must be >= 1")
        if n != self._template.layout.n:
            raise ValueError(
                f"proposed_actions action_dim {n} != template n {self._template.layout.n}"
            )

        prev = _as_batch_matrix(previous_actions, batch_size=k_batch, n=n, name="previous_actions")
        refs = _as_batch_matrix(reference_actions, batch_size=k_batch, n=n, name="reference_actions")
        lower_m = _as_batch_matrix(lowers, batch_size=k_batch, n=n, name="lowers")
        upper_m = _as_batch_matrix(uppers, batch_size=k_batch, n=n, name="uppers")
        delta_m = _as_batch_matrix(max_deltas, batch_size=k_batch, n=n, name="max_deltas")
        pw = _as_weight_vector(policy_weights, batch_size=k_batch, name="policy_weights")
        rw = _as_weight_vector(reference_weights, batch_size=k_batch, name="reference_weights")
        ids = self._row_ids(row_ids, batch_size=k_batch)

        row_data: list[ShieldQPData] = []
        q_rows: list[np.ndarray] = []
        b_rows: list[np.ndarray] = []
        setup_fps: list[str] = []
        p_snapshots: list[np.ndarray] = []
        a_snapshots: list[np.ndarray] = []

        for k in range(k_batch):
            data_k = _override_data(
                self._base_data,
                lower_row=None if lower_m is None else lower_m[k],
                upper_row=None if upper_m is None else upper_m[k],
                max_delta_row=None if delta_m is None else delta_m[k],
            )
            row_data.append(data_k)
            fp = self._template.fill(
                self._buffers,
                data_k,
                pb[k],
                None if prev is None else prev[k],
                None if refs is None else refs[k],
                policy_weight=float(pw[k]),
                reference_weight=float(rw[k]),
                copy_a_constants=not self._a_constants_loaded,
            )
            self._a_constants_loaded = True
            setup_fps.append(fp)
            q_rows.append(self._buffers.q.copy())
            b_rows.append(self._buffers.b.copy())
            p_snapshots.append(self._buffers.p_values.copy())
            a_snapshots.append(self._buffers.a_values.copy())

        shared_setup = all(fp == setup_fps[0] for fp in setup_fps)
        release_policy = self._release_policy()
        provenance = provenance_for_backend(
            backend_id="native_moreau_batch",
            solver_name="moreau",
            device=self.options.device,
            package_distribution="moreau",
            settings={
                "max_iter": self.options.max_iter,
                "batch_size": k_batch,
                "structural_fingerprint": self.structural_fingerprint,
            },
            warm_start_policy="persist" if self.options.persist_warm_start else "off",
        )
        device_out: str | None = str(self.options.device) if self.options.device else None

        if shared_setup:
            solver, cache_status = self._ensure_batch_solver(moreau, batch_size=k_batch)
            self._buffers.p_values[:] = p_snapshots[0]
            self._buffers.a_values[:] = a_snapshots[0]
            setup_dt, reused = self._setup(
                solver, setup_fp=setup_fps[0], buffers=self._buffers, mode="batch"
            )
            if reused and cache_status == "hit":
                cache_status = "setup_reuse"

            q_mat = np.stack(q_rows, axis=0)
            b_mat = np.stack(b_rows, axis=0)
            warm: Any | None = None
            warm_flags = [False] * k_batch
            if self.options.persist_warm_start:
                warm_key = "|".join(ids)
                warm = self._warm_by_row.get(warm_key)
                if warm is not None:
                    self.metrics.record_warm_start_hit()
                    warm_flags = [True] * k_batch
                else:
                    overlapping = [
                        k
                        for k in self._warm_by_row
                        if k != warm_key and any(rid in k.split("|") for rid in ids)
                    ]
                    if overlapping:
                        self.metrics.record_warm_start_rejection()
                        for k in overlapping:
                            del self._warm_by_row[k]

            t_solve = time.perf_counter()
            try:
                solution = solver.solve(qs=q_mat, bs=b_mat, warm_start=warm)
            except (RuntimeError, ValueError, TypeError, AttributeError, OSError):
                self._warm_by_row.pop("|".join(ids), None)
                raise
            solve_dt = float(time.perf_counter() - t_solve)

            if self.options.persist_warm_start and hasattr(solution, "to_warm_start"):
                try:
                    self._warm_by_row["|".join(ids)] = solution.to_warm_start()
                except (TypeError, ValueError, AttributeError, RuntimeError):
                    self._warm_by_row.pop("|".join(ids), None)

            xbat = np.asarray(solution.x, dtype=np.float64)
            if xbat.ndim != 2 or xbat.shape[0] != k_batch:
                raise RuntimeError(f"unexpected batched solution shape: {getattr(xbat, 'shape', None)}")
            info = getattr(solver, "info", None)
            raw_status = getattr(info, "status", None) if info is not None else None
            raw_iters = getattr(info, "iterations", None) if info is not None else None
            raw_obj = getattr(solution, "obj_val", None)
            if info is not None and getattr(info, "device", None) is not None:
                device_out = str(info.device)

            rows = tuple(
                self._build_row_result(
                    proposed=pb[k],
                    corrected=xbat[k],
                    data=row_data[k],
                    previous=None if prev is None else prev[k],
                    reference=None if refs is None else refs[k],
                    policy_weight=float(pw[k]),
                    reference_weight=float(rw[k]),
                    raw_status=_status_at(raw_status, k, k_batch),
                    objective=_objective_at(raw_obj, k),
                    iterations=_iterations_at(raw_iters, k, k_batch),
                    warm_started=warm_flags[k],
                    row_id=ids[k],
                    release_policy=release_policy,
                    provenance=provenance,
                    device=device_out,
                    setup_time_sec=setup_dt,
                    solve_time_sec=solve_dt,
                )
                for k in range(k_batch)
            )
            return BatchProjectionResult(
                rows=rows,
                batch_size=k_batch,
                setup_time_sec=setup_dt,
                solve_time_sec=solve_dt,
                device=device_out,
                cache_status=cache_status,
                structural_fingerprint=self.structural_fingerprint,
            )

        # Heterogeneous setup values (typically distinct weight scales): sequential
        # compiled solves with setup skip when consecutive rows share P/A.
        solver, cache_status = self._ensure_single_solver(moreau)
        rows_list: list[ProjectionResult] = []
        setup_time_total = 0.0
        setup_seen = False
        solve_time_total = 0.0
        for k in range(k_batch):
            self._buffers.p_values[:] = p_snapshots[k]
            self._buffers.a_values[:] = a_snapshots[k]
            self._buffers.q[:] = q_rows[k]
            self._buffers.b[:] = b_rows[k]
            setup_dt, reused = self._setup(
                solver, setup_fp=setup_fps[k], buffers=self._buffers, mode="single"
            )
            if setup_dt is not None:
                setup_time_total += setup_dt
                setup_seen = True
            if reused and cache_status == "hit":
                cache_status = "setup_reuse"

            warm = None
            warm_started = False
            if self.options.persist_warm_start:
                warm = self._warm_by_row.get(ids[k])
                if warm is not None:
                    self.metrics.record_warm_start_hit()
                    warm_started = True

            t_solve = time.perf_counter()
            try:
                solution = solver.solve(
                    qs=self._buffers.q.reshape(1, -1),
                    bs=self._buffers.b.reshape(1, -1),
                    warm_start=warm,
                )
            except (RuntimeError, ValueError, TypeError, AttributeError, OSError):
                self._warm_by_row.pop(ids[k], None)
                raise
            solve_dt = float(time.perf_counter() - t_solve)
            solve_time_total += solve_dt

            if self.options.persist_warm_start and hasattr(solution, "to_warm_start"):
                try:
                    self._warm_by_row[ids[k]] = solution.to_warm_start()
                except (TypeError, ValueError, AttributeError, RuntimeError):
                    self._warm_by_row.pop(ids[k], None)

            xbat = np.asarray(solution.x, dtype=np.float64)
            xv = xbat[0] if xbat.ndim == 2 else xbat.reshape(-1)
            info = getattr(solver, "info", None)
            raw_status = getattr(info, "status", None) if info is not None else None
            raw_iters = getattr(info, "iterations", None) if info is not None else None
            if info is not None and getattr(info, "device", None) is not None:
                device_out = str(info.device)
            rows_list.append(
                self._build_row_result(
                    proposed=pb[k],
                    corrected=xv,
                    data=row_data[k],
                    previous=None if prev is None else prev[k],
                    reference=None if refs is None else refs[k],
                    policy_weight=float(pw[k]),
                    reference_weight=float(rw[k]),
                    raw_status=_status_at(raw_status, 0, 1),
                    objective=_objective_at(getattr(solution, "obj_val", None), 0),
                    iterations=_iterations_at(raw_iters, 0, 1),
                    warm_started=warm_started,
                    row_id=ids[k],
                    release_policy=release_policy,
                    provenance=provenance,
                    device=device_out,
                    setup_time_sec=setup_dt,
                    solve_time_sec=solve_dt,
                )
            )

        return BatchProjectionResult(
            rows=tuple(rows_list),
            batch_size=k_batch,
            setup_time_sec=setup_time_total if setup_seen else None,
            solve_time_sec=solve_time_total,
            device=device_out,
            cache_status=cache_status,
            structural_fingerprint=self.structural_fingerprint,
        )
