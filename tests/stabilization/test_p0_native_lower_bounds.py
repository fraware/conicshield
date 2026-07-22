"""CS-SOLVER-001: native Moreau builder lower-bound semantics vs CVXPY."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from conicshield.specs.schema import BoxConstraint, SafetySpec, SimplexConstraint
from conicshield.specs.shield_qp import parse_safety_spec_for_shield


def _effective_box_bounds(a_full: Any, b_full: np.ndarray, n_eq: int, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Interpret native inequality block ``A x <= b`` for unit-vector box rows."""
    a_nn = np.asarray(a_full.toarray()[n_eq:], dtype=np.float64)
    b_nn = np.asarray(b_full[n_eq:], dtype=np.float64)
    lowers = np.full(n, -np.inf, dtype=np.float64)
    uppers = np.full(n, np.inf, dtype=np.float64)
    for row, rhs in zip(a_nn, b_nn, strict=True):
        nz = np.flatnonzero(np.abs(row) > 1e-15)
        if nz.size != 1:
            continue
        i = int(nz[0])
        coef = float(row[i])
        if abs(coef + 1.0) < 1e-12:
            # -x_i <= rhs  =>  x_i >= -rhs
            lowers[i] = max(lowers[i], -float(rhs))
        elif abs(coef - 1.0) < 1e-12:
            # x_i <= rhs
            uppers[i] = min(uppers[i], float(rhs))
    return lowers, uppers


@pytest.mark.xfail(
    strict=True,
    reason="CS-SOLVER-001: native builder adds unconditional x>=0 and skips negative BoxConstraint.lower",
)
def test_native_builder_encodes_negative_lower_bounds_like_cvxpy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Negative lower bounds must compile to x_i >= lower_i, matching CVXPY (not stronger x_i >= 0)."""
    import sys

    stub = SimpleNamespace(Cones=lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setitem(sys.modules, "moreau", stub)

    from conicshield.specs.native_moreau_builder import build_moreau_standard_form

    lower = [-0.2, 0.0, 0.05, 0.0]
    upper = [1.0, 1.0, 1.0, 1.0]
    spec = SafetySpec(
        spec_id="stabilization/cs-solver-001",
        version="0.1.0",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            BoxConstraint(lower=lower, upper=upper),
        ],
    )
    data = parse_safety_spec_for_shield(spec)
    proposed = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64)

    _p, _q, a_csr, b, cones = build_moreau_standard_form(
        data,
        proposed,
        None,
        None,
        policy_weight=1.0,
        reference_weight=0.0,
    )
    n_eq = int(cones.num_zero_cones)
    eff_lower, _eff_upper = _effective_box_bounds(a_csr, b, n_eq, data.n)
    assert eff_lower[0] == pytest.approx(-0.2)
    assert eff_lower[2] == pytest.approx(0.05)
