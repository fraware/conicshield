"""Build ``P, q, A, b`` and ``Cones`` for ``moreau.Solver`` (shield simplex QP)."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import sparse  # type: ignore[import-untyped]

from conicshield.specs.shield_qp import ShieldQPData, objective_pq


def build_moreau_standard_form(
    data: ShieldQPData,
    proposed: np.ndarray,
    previous: np.ndarray | None,
    reference: np.ndarray | None,
    *,
    policy_weight: float,
    reference_weight: float,
) -> tuple[sparse.csr_matrix, np.ndarray, sparse.csr_matrix, np.ndarray, Any]:
    """Return ``P_csr, q, A_csr, b, cones`` for ``moreau.Solver``."""
    import moreau

    n = data.n
    p_mat, q = objective_pq(
        proposed,
        reference,
        policy_weight=policy_weight,
        reference_weight=reference_weight,
        n=n,
    )
    p_csr = sparse.csr_matrix(p_mat)

    a_eq: list[np.ndarray] = []
    b_eq: list[float] = []

    row = np.ones(n, dtype=np.float64)
    a_eq.append(row)
    b_eq.append(float(data.simplex_total))

    for i in range(n):
        if not data.allowed_mask[i]:
            e = np.zeros(n, dtype=np.float64)
            e[i] = 1.0
            a_eq.append(e)
            b_eq.append(0.0)

    a_nn: list[np.ndarray] = []
    b_nn: list[float] = []

    for i in range(n):
        r = np.zeros(n, dtype=np.float64)
        r[i] = -1.0
        a_nn.append(r)
        b_nn.append(0.0)

    for i in range(n):
        r = np.zeros(n, dtype=np.float64)
        r[i] = 1.0
        a_nn.append(r)
        b_nn.append(float(data.upper[i]))

    for i in range(n):
        if data.lower[i] > 1e-15:
            r = np.zeros(n, dtype=np.float64)
            r[i] = -1.0
            a_nn.append(r)
            b_nn.append(float(-data.lower[i]))

    if previous is not None:
        pv = np.asarray(previous, dtype=np.float64).reshape(-1)
        if pv.shape[0] != n:
            raise ValueError("previous_action length mismatch")
        for i in range(n):
            d = float(data.max_delta[i])
            if np.isfinite(d) and d >= 0.0:
                r = np.zeros(n, dtype=np.float64)
                r[i] = 1.0
                a_nn.append(r)
                b_nn.append(float(pv[i] + d))
                r2 = np.zeros(n, dtype=np.float64)
                r2[i] = -1.0
                a_nn.append(r2)
                b_nn.append(float(d - pv[i]))

    a_eq_m = np.vstack(a_eq) if a_eq else np.zeros((0, n))
    b_eq_v = np.array(b_eq, dtype=np.float64)
    a_nn_m = np.vstack(a_nn) if a_nn else np.zeros((0, n))
    b_nn_v = np.array(b_nn, dtype=np.float64)

    if a_nn_m.shape[0] == 0:
        a_full = sparse.csr_matrix(a_eq_m)
        b_full = b_eq_v
        cones = moreau.Cones(num_zero_cones=a_eq_m.shape[0], num_nonneg_cones=0)
    else:
        a_full = sparse.vstack(
            [sparse.csr_matrix(a_eq_m), sparse.csr_matrix(a_nn_m)],
            format="csr",
        )
        b_full = np.concatenate([b_eq_v, b_nn_v])
        cones = moreau.Cones(num_zero_cones=a_eq_m.shape[0], num_nonneg_cones=a_nn_m.shape[0])

    return p_csr, q, a_full, b_full, cones
