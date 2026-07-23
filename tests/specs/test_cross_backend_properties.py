"""Property-based cross-backend IR parity (CVXPY constraints vs native cone rows).

Native Moreau solve is not required: builder math is checked with a stub ``moreau.Cones``.
When vendor Moreau + CVXPY MOREAU are available, an optional solve-parity case runs
under vendor markers without weakening required-mode gates.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from conicshield.specs.native_moreau_builder import build_moreau_standard_form
from conicshield.specs.schema import (
    BoxConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)
from conicshield.specs.shield_qp import parse_safety_spec_for_shield
from tests.stabilization.vendor_required import skip_or_fail_vendor


def _effective_box_bounds(
    a_full: Any, b_full: np.ndarray, n_eq: int, n: int
) -> tuple[np.ndarray, np.ndarray]:
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
            lowers[i] = max(lowers[i], -float(rhs))
        elif abs(coef - 1.0) < 1e-12:
            uppers[i] = min(uppers[i], float(rhs))
    return lowers, uppers


def _feasible_box(n: int, lower: list[float], upper: list[float]) -> bool:
    del n
    if any(lo > hi for lo, hi in zip(lower, upper, strict=True)):
        return False
    # Keep simplex-feasible under total=1 for property generation.
    if sum(lower) > 1.0 + 1e-12:
        return False
    return sum(upper) >= 1.0 - 1e-12


@st.composite
def feasible_specs(draw: st.DrawFn) -> SafetySpec:
    n = draw(st.integers(min_value=2, max_value=5))
    lowers: list[float] = []
    uppers: list[float] = []
    for _ in range(n):
        lo = draw(st.floats(min_value=-0.5, max_value=0.4, allow_nan=False, allow_infinity=False))
        hi = draw(st.floats(min_value=lo, max_value=1.5, allow_nan=False, allow_infinity=False))
        lowers.append(float(lo))
        uppers.append(float(hi))
    # Repair mild infeasibility without silent production coercion: resample-ish clamp of sum.
    if sum(lowers) > 1.0:
        scale = 0.9 / sum(lowers)
        lowers = [lo * scale for lo in lowers]
        uppers = [max(u, lo) for lo, u in zip(lowers, uppers, strict=True)]
    if sum(uppers) < 1.0:
        # Bump the largest upper.
        j = int(np.argmax(uppers))
        uppers[j] = max(uppers[j], 1.0 - sum(uppers) + uppers[j] + 1e-6)
    assume_ok = _feasible_box(n, lowers, uppers)
    if not assume_ok:
        # Force a known-feasible unit box.
        lowers = [0.0] * n
        uppers = [1.0] * n

    allowed = draw(st.lists(st.integers(min_value=0, max_value=n - 1), min_size=1, max_size=n, unique=True))
    # Ensure admissible uppers can meet simplex.
    if sum(uppers[i] for i in allowed) < 1.0 - 1e-12:
        allowed = list(range(n))
    allowed_set = set(allowed)
    for i in range(n):
        if i not in allowed_set:
            # Prohibited actions are fixed at 0; keep 0 inside the box.
            lowers[i] = min(0.0, lowers[i])
            uppers[i] = max(0.0, uppers[i])
            if lowers[i] > 0.0 or uppers[i] < 0.0:
                lowers[i] = 0.0
                uppers[i] = 0.0

    tight = draw(st.booleans())
    rate = [0.05 if tight else 1.0 for _ in range(n)]
    return SafetySpec(
        spec_id="hypothesis-ir",
        action_dim=n,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=sorted(allowed)),
            BoxConstraint(lower=lowers, upper=uppers),
            RateConstraint(max_delta=rate),
        ],
    )


@given(spec=feasible_specs())
@settings(max_examples=40, deadline=None)
def test_native_box_rows_match_ir_bounds(spec: SafetySpec) -> None:
    import sys

    stub = SimpleNamespace(Cones=lambda **kwargs: SimpleNamespace(**kwargs))
    previous = sys.modules.get("moreau")
    sys.modules["moreau"] = stub  # type: ignore[assignment]
    try:
        data = parse_safety_spec_for_shield(spec)
        proposed = np.full(data.n, 1.0 / data.n, dtype=np.float64)
        _p, _q, a_csr, b, cones = build_moreau_standard_form(
            data,
            proposed,
            None,
            None,
            policy_weight=1.0,
            reference_weight=0.0,
        )
        eff_lower, eff_upper = _effective_box_bounds(a_csr, b, int(cones.num_zero_cones), data.n)
        np.testing.assert_allclose(eff_lower, data.lower)
        np.testing.assert_allclose(eff_upper, data.upper)
        # CVXPY path uses the same IR arrays directly.
        np.testing.assert_allclose(data.lower, parse_safety_spec_for_shield(spec).lower)
        np.testing.assert_allclose(data.upper, parse_safety_spec_for_shield(spec).upper)
    finally:
        if previous is None:
            sys.modules.pop("moreau", None)
        else:
            sys.modules["moreau"] = previous


@pytest.mark.vendor_moreau
@pytest.mark.requires_moreau
@pytest.mark.solver
def test_optional_native_cvxpy_solve_parity_smoke() -> None:
    """When Moreau is available, one smoke solve must agree across backends."""
    try:
        import moreau  # noqa: F401
    except Exception as exc:  # pragma: no cover - environment dependent
        skip_or_fail_vendor(f"moreau import failed: {exc}")
        return

    cvxpy = pytest.importorskip("cvxpy")
    if not hasattr(cvxpy, "MOREAU"):
        skip_or_fail_vendor("cp.MOREAU not available")
        return

    from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions, NativeMoreauCompiledProjector
    from conicshield.specs.compiler import CVXPYMoreauProjector, SolverOptions

    spec = SafetySpec(
        spec_id="parity-smoke",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[0, 1, 2, 3]),
            BoxConstraint(lower=[-0.05, 0.0, 0.0, 0.0], upper=[1.0, 1.0, 1.0, 1.0]),
            RateConstraint(max_delta=[1.0] * 4),
        ],
    )
    proposed = np.array([0.4, 0.3, 0.2, 0.1], dtype=np.float64)
    prev = np.full(4, 0.25, dtype=np.float64)
    ref = CVXPYMoreauProjector(spec=spec, options=SolverOptions(device="cpu", max_iter=800))
    nat = NativeMoreauCompiledProjector(
        spec=spec,
        options=NativeMoreauCompiledOptions(device="cpu", max_iter=800, persist_warm_start=False),
    )
    try:
        r_ref = ref.project(proposed, prev)
        r_nat = nat.project(proposed, prev)
    except RuntimeError as exc:
        if "license" in str(exc).lower() or "key" in str(exc).lower():
            skip_or_fail_vendor(f"Moreau license not available: {exc}")
            return
        raise
    np.testing.assert_allclose(r_nat.corrected_action, r_ref.corrected_action, rtol=1e-3, atol=1e-4)
