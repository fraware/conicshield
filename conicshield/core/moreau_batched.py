"""True batched ``CompiledSolver.solve(qs, bs)`` for shield QPs with shared ``previous_action`` and weights."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from conicshield.solver_errors import require_solver_module
from conicshield.specs.native_moreau_builder import build_moreau_standard_form
from conicshield.specs.schema import SafetySpec
from conicshield.specs.shield_qp import parse_safety_spec_for_shield

from .moreau_compiled import (
    NativeMoreauCompiledOptions,
    _csr_structure_matches,
    _CSRStructureKey,
)


class NativeMoreauCompiledBatchProjector:
    """One ``CompiledSolver`` call per batch (``batch_size`` = number of proposals)."""

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
        self._batch_k: int | None = None
        self._compiled_settings_key: tuple[Any, ...] | None = None

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
        for opt_key in ("auto_tune", "enable_grad"):
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
        )

    def project_batch(
        self,
        proposed_batch: np.ndarray,
        previous_action: np.ndarray | None = None,
        *,
        reference_action: np.ndarray | None = None,
        policy_weight: float = 1.0,
        reference_weight: float = 0.0,
    ) -> np.ndarray:
        """Return corrected actions with shape ``(K, n)`` from a single batched solve."""
        require_solver_module("moreau", "native Moreau batch projector")
        import moreau

        if not hasattr(moreau, "CompiledSolver"):
            raise RuntimeError("moreau.CompiledSolver is required for batched shield projection")

        data = parse_safety_spec_for_shield(self.spec)
        pb = np.asarray(proposed_batch, dtype=np.float64)
        if pb.ndim != 2:
            raise ValueError("proposed_batch must have shape (batch, action_dim)")
        k_batch, n = pb.shape
        if k_batch < 1:
            raise ValueError("batch size must be >= 1")
        if n != data.n:
            raise ValueError(f"proposed_batch action_dim {n} != spec action_dim {data.n}")

        p0: sparse.csr_matrix | None = None
        a0: sparse.csr_matrix | None = None
        b0: np.ndarray | None = None
        cones0: Any = None
        key: _CSRStructureKey | None = None
        qs: list[np.ndarray] = []

        for k in range(k_batch):
            p_csr, q, a_csr, b_full, cones = build_moreau_standard_form(
                data,
                pb[k],
                previous_action,
                reference_action,
                policy_weight=policy_weight,
                reference_weight=reference_weight,
            )
            if k == 0:
                key = _CSRStructureKey.from_pair(p_csr, a_csr)
                p0, a0, b0, cones0 = p_csr, a_csr, b_full, cones
            else:
                assert key is not None and p0 is not None and a0 is not None and b0 is not None
                if not _csr_structure_matches(key, p_csr, a_csr):
                    raise ValueError("CSR structure mismatch across batch rows (same spec required)")
                if not np.allclose(p_csr.data, p0.data) or not np.allclose(a_csr.data, a0.data):
                    raise ValueError("P/A numeric values must match for a single batched CompiledSolver setup")
                if not np.allclose(b_full, b0):
                    raise ValueError(
                        "Constraint RHS mismatch across batch rows; batching requires shared previous_action"
                    )

            qs.append(np.asarray(q, dtype=np.float64).reshape(-1))

        assert p0 is not None and a0 is not None and b0 is not None and cones0 is not None and key is not None
        q_mat = np.stack(qs, axis=0)
        b_mat = np.tile(np.asarray(b0, dtype=np.float64).reshape(1, -1), (k_batch, 1))

        warm = self._warm if self.options.persist_warm_start else None
        fp = self._settings_fingerprint(moreau, batch_size=k_batch)
        need_build = (
            self._compiled is None
            or self._batch_k != k_batch
            or self._compiled_settings_key != fp
            or self._csr_key is None
            or not _csr_structure_matches(self._csr_key, p0, a0)
        )
        if need_build:
            settings = self._moreau_settings(moreau, batch_size=k_batch)
            self._compiled = moreau.CompiledSolver(
                n=key.n,
                m=key.m,
                P_row_offsets=p0.indptr,
                P_col_indices=p0.indices,
                A_row_offsets=a0.indptr,
                A_col_indices=a0.indices,
                cones=cones0,
                settings=settings,
            )
            self._csr_key = key
            self._batch_k = k_batch
            self._compiled_settings_key = fp
            self._warm = None

        solver = self._compiled
        solver.setup(np.asarray(p0.data, dtype=np.float64), np.asarray(a0.data, dtype=np.float64))
        try:
            solution = solver.solve(qs=q_mat, bs=b_mat, warm_start=warm)
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

        xbat = np.asarray(solution.x, dtype=np.float64)
        if xbat.ndim != 2 or xbat.shape[0] != k_batch:
            raise RuntimeError(f"unexpected batched solution shape: {getattr(xbat, 'shape', None)}")
        return xbat
