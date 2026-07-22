"""Fixed-structure compiled shield template with sparse parameter fills."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from conicshield.compilation.parameter_layout import ParameterLayout, build_parameter_layout
from conicshield.compilation.structural_fingerprint import setup_values_fingerprint
from conicshield.compilation.topology import (
    ConstraintTopology,
    assert_data_matches_topology,
    topology_from_shield_qp,
)
from conicshield.specs.shield_qp import ShieldQPData, validate_objective_weights
from conicshield.verification.residuals import ResidualReport, evaluate_residuals


@dataclass(slots=True)
class NumericBuffers:
    """Preallocated numeric arrays for one solve (or one batch row)."""

    p_values: np.ndarray
    a_values: np.ndarray
    q: np.ndarray
    b: np.ndarray


@dataclass(frozen=True, slots=True)
class CompiledShieldTemplate:
    """Immutable CSR topology + parameter layout for the shield QP family.

    Runtime fills mutate caller-owned ``NumericBuffers`` only. Structure changes
    require compiling a new template (different ``structural_fingerprint``).
    """

    topology: ConstraintTopology
    layout: ParameterLayout
    p_indptr: np.ndarray
    p_indices: np.ndarray
    a_indptr: np.ndarray
    a_indices: np.ndarray
    structural_fingerprint: str

    @staticmethod
    def compile(
        data: ShieldQPData,
        *,
        include_rate_rows: bool | None = None,
    ) -> CompiledShieldTemplate:
        """Compile immutable structure from canonical IR."""
        topology = topology_from_shield_qp(data, include_rate_rows=include_rate_rows)
        layout, csr = build_parameter_layout(topology)
        return CompiledShieldTemplate(
            topology=topology,
            layout=layout,
            p_indptr=np.asarray(csr["p_indptr"], dtype=np.int64).copy(),
            p_indices=np.asarray(csr["p_indices"], dtype=np.int64).copy(),
            a_indptr=np.asarray(csr["a_indptr"], dtype=np.int64).copy(),
            a_indices=np.asarray(csr["a_indices"], dtype=np.int64).copy(),
            structural_fingerprint=topology.structural_fingerprint,
        )

    def allocate_buffers(self) -> NumericBuffers:
        """Allocate fresh numeric buffers sized to this template."""
        return NumericBuffers(
            p_values=np.zeros(self.layout.nnz_p, dtype=np.float64),
            a_values=np.zeros(self.layout.nnz_a, dtype=np.float64),
            q=np.zeros(self.layout.n, dtype=np.float64),
            b=np.zeros(self.layout.m, dtype=np.float64),
        )

    def moreau_cones(self, moreau_module: Any) -> Any:
        """Build a vendor ``Cones`` object from immutable topology counts."""
        return moreau_module.Cones(
            num_zero_cones=int(self.topology.num_zero_cones),
            num_nonneg_cones=int(self.topology.num_nonneg_cones),
        )

    def fill(
        self,
        buffers: NumericBuffers,
        data: ShieldQPData,
        proposed: np.ndarray,
        previous: np.ndarray | None,
        reference: np.ndarray | None,
        *,
        policy_weight: float,
        reference_weight: float,
        copy_a_constants: bool = True,
    ) -> str:
        """Fill ``buffers`` in place; return setup-values fingerprint.

        Avoids dense ``P`` / ``A`` matrix intermediates. When
        ``copy_a_constants`` is False, ``a_values`` is assumed already correct
        (same topology) and only ``P``, ``q``, ``b`` are refreshed.
        """
        assert_data_matches_topology(data, self.topology)
        n = self.layout.n
        proposed_v = np.asarray(proposed, dtype=np.float64).reshape(-1)
        if proposed_v.shape[0] != n:
            raise ValueError(f"proposed_action length {proposed_v.shape[0]} != action_dim {n}")

        pw, rw = validate_objective_weights(
            policy_weight,
            reference_weight,
            reference_present=reference is not None,
        )
        scale = float(pw + rw)
        # P diagonal = 2 * scale
        buffers.p_values.fill(2.0 * scale)

        if copy_a_constants:
            np.copyto(buffers.a_values, self.layout.a_const_values)

        # q = -2 pw p - 2 rw r
        buffers.q[:] = -2.0 * pw * proposed_v
        if reference is not None and rw > 0.0:
            ref_v = np.asarray(reference, dtype=np.float64).reshape(-1)
            if ref_v.shape[0] != n:
                raise ValueError(f"reference_action length {ref_v.shape[0]} != action_dim {n}")
            buffers.q -= 2.0 * rw * ref_v

        buffers.b.fill(0.0)
        buffers.b[self.layout.b_simplex_index] = float(data.simplex_total)
        for _idx, b_i in self.layout.b_prohibit_index.items():
            buffers.b[b_i] = 0.0

        lower = np.asarray(data.lower, dtype=np.float64).reshape(-1)
        upper = np.asarray(data.upper, dtype=np.float64).reshape(-1)
        if lower.shape[0] != n or upper.shape[0] != n:
            raise ValueError("box bound length mismatch against action_dim")
        for i in range(n):
            lo = float(lower[i])
            hi = float(upper[i])
            if not np.isfinite(lo) or not np.isfinite(hi):
                raise ValueError(f"box bounds must be finite at index {i}")
            buffers.b[int(self.layout.b_box_lower_index[i])] = float(-lo)
            buffers.b[int(self.layout.b_box_upper_index[i])] = float(hi)

        if self.topology.include_rate_rows:
            if self.layout.b_rate_pos_index is None or self.layout.b_rate_neg_index is None:
                raise RuntimeError("rate layout indices missing")
            max_delta = np.asarray(data.max_delta, dtype=np.float64).reshape(-1)
            if previous is None:
                # Keep CSR topology fixed: inactive rate rows (do not rebuild without rates).
                for i in self.topology.rate_indices:
                    buffers.b[int(self.layout.b_rate_pos_index[i])] = 1e12
                    buffers.b[int(self.layout.b_rate_neg_index[i])] = 1e12
            else:
                prev = np.asarray(previous, dtype=np.float64).reshape(-1)
                if prev.shape[0] != n:
                    raise ValueError("previous_action length mismatch")
                for i in self.topology.rate_indices:
                    d = float(max_delta[i])
                    if not (np.isfinite(d) and d >= 0.0):
                        d = 1e12
                    buffers.b[int(self.layout.b_rate_pos_index[i])] = float(prev[i] + d)
                    buffers.b[int(self.layout.b_rate_neg_index[i])] = float(d - prev[i])

        return str(setup_values_fingerprint(buffers.p_values, buffers.a_values))

    def evaluate_residuals(
        self,
        candidate: np.ndarray,
        data: ShieldQPData,
        *,
        previous_action: np.ndarray | None = None,
        proposed_action: np.ndarray | None = None,
        reference_action: np.ndarray | None = None,
        policy_weight: float = 1.0,
        reference_weight: float = 0.0,
        reported_objective: float | None = None,
    ) -> ResidualReport:
        """S2 residual hook — delegates to backend-independent residual evaluator."""
        assert_data_matches_topology(data, self.topology)
        return evaluate_residuals(
            candidate,
            data,
            previous_action=previous_action,
            proposed_action=proposed_action,
            reference_action=reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
            reported_objective=reported_objective,
        )

    def sparse_ax_residual(self, buffers: NumericBuffers, x: np.ndarray) -> np.ndarray:
        """Compute ``A @ x - b`` using CSR structure (no dense A)."""
        xv = np.asarray(x, dtype=np.float64).reshape(-1)
        if xv.shape[0] != self.layout.n:
            raise ValueError("x length mismatch")
        m = self.layout.m
        out = np.empty(m, dtype=np.float64)
        indptr = self.a_indptr
        indices = self.a_indices
        vals = buffers.a_values
        for r in range(m):
            start = int(indptr[r])
            end = int(indptr[r + 1])
            acc = 0.0
            for k in range(start, end):
                acc += float(vals[k]) * float(xv[int(indices[k])])
            out[r] = acc - float(buffers.b[r])
        return out
