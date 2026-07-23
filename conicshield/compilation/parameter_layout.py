"""Parameter offsets for filling preallocated numeric buffers on a fixed topology."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from conicshield.compilation.topology import ConstraintTopology


@dataclass(frozen=True, slots=True)
class ParameterLayout:
    """Maps semantic shield parameters onto CSR value / dense q,b slots.

    For the shield QP family:
    * ``P`` is diagonal — each diagonal entry is one ``P_values`` slot.
    * ``A`` entries are structural constants (``±1`` / ``1``) — values rarely change.
    * ``q`` length ``n``; ``b`` length ``m``.
    """

    n: int
    m: int
    nnz_p: int
    nnz_a: int
    #: Index into ``P_values`` for diagonal entry ``i`` (length ``n``).
    p_diag_index: np.ndarray
    #: Constant structural ``A_values`` (length ``nnz_a``); copy once at compile.
    a_const_values: np.ndarray
    b_simplex_index: int
    #: Map prohibited action index -> b offset.
    b_prohibit_index: dict[int, int]
    b_box_lower_index: np.ndarray  # length n
    b_box_upper_index: np.ndarray  # length n
    b_rate_pos_index: np.ndarray | None  # length n or None
    b_rate_neg_index: np.ndarray | None  # length n or None

    def __post_init__(self) -> None:
        object.__setattr__(self, "p_diag_index", np.asarray(self.p_diag_index, dtype=np.int64))
        object.__setattr__(self, "a_const_values", np.asarray(self.a_const_values, dtype=np.float64))
        object.__setattr__(
            self, "b_box_lower_index", np.asarray(self.b_box_lower_index, dtype=np.int64)
        )
        object.__setattr__(
            self, "b_box_upper_index", np.asarray(self.b_box_upper_index, dtype=np.int64)
        )
        if self.b_rate_pos_index is not None:
            object.__setattr__(
                self, "b_rate_pos_index", np.asarray(self.b_rate_pos_index, dtype=np.int64)
            )
        if self.b_rate_neg_index is not None:
            object.__setattr__(
                self, "b_rate_neg_index", np.asarray(self.b_rate_neg_index, dtype=np.int64)
            )


def build_parameter_layout(
    topology: ConstraintTopology,
) -> tuple[ParameterLayout, dict[str, np.ndarray]]:
    """Build layout and CSR index arrays (indptr/indices) for ``topology``.

    Returns ``(layout, csr)`` where ``csr`` has keys
    ``p_indptr``, ``p_indices``, ``a_indptr``, ``a_indices``.
    """
    n = topology.n
    # P = diagonal CSR
    p_indptr = np.arange(n + 1, dtype=np.int64)
    p_indices = np.arange(n, dtype=np.int64)
    p_diag_index = np.arange(n, dtype=np.int64)

    a_rows: list[int] = []
    a_cols: list[int] = []
    a_vals: list[float] = []

    def _add_row(row: int, cols: list[int], vals: list[float]) -> None:
        for c, v in zip(cols, vals, strict=True):
            a_rows.append(row)
            a_cols.append(c)
            a_vals.append(v)

    row = 0
    # simplex: sum x_i = total  ->  1' x = b
    _add_row(row, list(range(n)), [1.0] * n)
    b_simplex_index = row
    row += 1

    b_prohibit: dict[int, int] = {}
    for idx in topology.prohibited_indices:
        _add_row(row, [int(idx)], [1.0])
        b_prohibit[int(idx)] = row
        row += 1

    b_box_lower = np.full(n, -1, dtype=np.int64)
    b_box_upper = np.full(n, -1, dtype=np.int64)
    for i in range(n):
        # -x_i <= -lower  => A=-1
        _add_row(row, [i], [-1.0])
        b_box_lower[i] = row
        row += 1
        # x_i <= upper => A=+1
        _add_row(row, [i], [1.0])
        b_box_upper[i] = row
        row += 1

    b_rate_pos: np.ndarray | None = None
    b_rate_neg: np.ndarray | None = None
    if topology.include_rate_rows:
        b_rate_pos = np.full(n, -1, dtype=np.int64)
        b_rate_neg = np.full(n, -1, dtype=np.int64)
        for i in topology.rate_indices:
            _add_row(row, [i], [1.0])
            b_rate_pos[i] = row
            row += 1
            _add_row(row, [i], [-1.0])
            b_rate_neg[i] = row
            row += 1

    if row != topology.m:
        raise RuntimeError(f"layout row count {row} != topology.m {topology.m}")

    # Convert COO-like lists to CSR without dense intermediates.
    nnz_a = len(a_vals)
    a_indptr = np.zeros(topology.m + 1, dtype=np.int64)
    a_indices = np.zeros(nnz_a, dtype=np.int64)
    a_const = np.zeros(nnz_a, dtype=np.float64)
    # rows are appended in order; each row's entries are contiguous in construction order.
    cursor = 0
    current_row = 0
    for r, c, v in zip(a_rows, a_cols, a_vals, strict=True):
        while current_row < r:
            a_indptr[current_row + 1] = cursor
            current_row += 1
        a_indices[cursor] = int(c)
        a_const[cursor] = float(v)
        cursor += 1
    while current_row < topology.m:
        a_indptr[current_row + 1] = cursor
        current_row += 1

    layout = ParameterLayout(
        n=n,
        m=topology.m,
        nnz_p=n,
        nnz_a=nnz_a,
        p_diag_index=p_diag_index,
        a_const_values=a_const,
        b_simplex_index=b_simplex_index,
        b_prohibit_index=b_prohibit,
        b_box_lower_index=b_box_lower,
        b_box_upper_index=b_box_upper,
        b_rate_pos_index=b_rate_pos,
        b_rate_neg_index=b_rate_neg,
    )
    csr = {
        "p_indptr": p_indptr,
        "p_indices": p_indices,
        "a_indptr": a_indptr,
        "a_indices": a_indices,
    }
    return layout, csr
