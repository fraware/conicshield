"""S1 native lower/upper bound encoding parity with CVXPY IR semantics."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from conicshield.specs.native_moreau_builder import build_moreau_standard_form
from conicshield.specs.schema import BoxConstraint, RateConstraint, SafetySpec, SimplexConstraint
from conicshield.specs.shield_qp import parse_safety_spec_for_shield


def _effective_box_bounds(
    a_full: Any, b_full: np.ndarray, n_eq: int, n: int
) -> tuple[np.ndarray, np.ndarray]:
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


def _build_with_stub_moreau(monkeypatch: pytest.MonkeyPatch, data, proposed):
    import sys

    stub = SimpleNamespace(Cones=lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setitem(sys.modules, "moreau", stub)
    return build_moreau_standard_form(
        data,
        proposed,
        None,
        None,
        policy_weight=1.0,
        reference_weight=0.0,
    )


@pytest.mark.parametrize(
    "lower,upper",
    [
        ([-0.2, 0.0, 0.05, 0.0], [1.0, 1.0, 1.0, 1.0]),
        ([0.0, 0.0, 0.0, 0.0], [1.0, 0.8, 0.5, 1.0]),
        ([-1.0, -0.5, 0.0, 0.25], [0.5, 0.5, 0.5, 1.0]),
    ],
)
def test_native_encodes_declared_box_bounds(
    monkeypatch: pytest.MonkeyPatch,
    lower: list[float],
    upper: list[float],
) -> None:
    spec = SafetySpec(
        spec_id="native-box",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            BoxConstraint(lower=lower, upper=upper),
        ],
    )
    data = parse_safety_spec_for_shield(spec)
    proposed = np.full(4, 0.25, dtype=np.float64)
    _p, _q, a_csr, b, cones = _build_with_stub_moreau(monkeypatch, data, proposed)
    n_eq = int(cones.num_zero_cones)
    eff_lower, eff_upper = _effective_box_bounds(a_csr, b, n_eq, data.n)
    np.testing.assert_allclose(eff_lower, np.asarray(lower, dtype=np.float64))
    np.testing.assert_allclose(eff_upper, np.asarray(upper, dtype=np.float64))


def test_native_does_not_add_extra_nonnegativity_beyond_declared_lower(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Negative declared lower must not be strengthened to 0."""
    lower = [-0.3, -0.1, 0.0, 0.2]
    upper = [1.0, 1.0, 1.0, 1.0]
    spec = SafetySpec(
        spec_id="no-extra-nn",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            BoxConstraint(lower=lower, upper=upper),
        ],
    )
    data = parse_safety_spec_for_shield(spec)
    _p, _q, a_csr, b, cones = _build_with_stub_moreau(
        monkeypatch, data, np.full(4, 0.25, dtype=np.float64)
    )
    n_eq = int(cones.num_zero_cones)
    eff_lower, _ = _effective_box_bounds(a_csr, b, n_eq, data.n)
    assert eff_lower[0] == pytest.approx(-0.3)
    assert eff_lower[1] == pytest.approx(-0.1)
    assert eff_lower[0] < 0.0


def test_native_rate_rows_with_previous(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = SafetySpec(
        spec_id="rate-rows",
        action_dim=2,
        constraints=[
            SimplexConstraint(total=1.0),
            BoxConstraint(lower=[0.0, 0.0], upper=[1.0, 1.0]),
            RateConstraint(max_delta=[0.1, 0.25]),
        ],
    )
    data = parse_safety_spec_for_shield(spec)
    import sys

    stub = SimpleNamespace(Cones=lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setitem(sys.modules, "moreau", stub)
    prev = np.array([0.4, 0.6], dtype=np.float64)
    _p, _q, a_csr, b, cones = build_moreau_standard_form(
        data,
        np.array([0.5, 0.5], dtype=np.float64),
        prev,
        None,
        policy_weight=1.0,
        reference_weight=0.0,
    )
    # 1 simplex eq + 2 lower + 2 upper + 4 rate = cones
    assert cones.num_zero_cones == 1
    assert cones.num_nonneg_cones == 2 + 2 + 4
    assert a_csr.shape[0] == cones.num_zero_cones + cones.num_nonneg_cones
    assert b.shape[0] == a_csr.shape[0]
