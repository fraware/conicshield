from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("moreau")
pytestmark = pytest.mark.vendor_moreau

from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions, NativeMoreauCompiledProjector
from conicshield.specs.compiler import CVXPYMoreauProjector, SolverOptions
from conicshield.specs.schema import (
    BoxConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)


def _spec() -> SafetySpec:
    return SafetySpec(
        spec_id="native-parity-test",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[1]),
            BoxConstraint(lower=[0.0] * 4, upper=[1.0] * 4),
            RateConstraint(max_delta=[1.0] * 4),
        ],
    )


@pytest.mark.requires_moreau
@pytest.mark.solver
def test_native_matches_reference_within_tolerance() -> None:
    cvxpy = pytest.importorskip("cvxpy")
    if not hasattr(cvxpy, "MOREAU"):
        pytest.skip("cp.MOREAU not available")

    spec = _spec()
    proposed = np.array([0.85, 0.1, 0.03, 0.02], dtype=np.float64)
    prev = np.full(4, 0.25, dtype=np.float64)

    ref = CVXPYMoreauProjector(spec=spec, options=SolverOptions(device="cpu", max_iter=800, verbose=False))
    nat = NativeMoreauCompiledProjector(spec=spec, options=NativeMoreauCompiledOptions(device="cpu", max_iter=800))

    try:
        r_ref = ref.project(proposed, prev)
        r_nat = nat.project(proposed, prev)
    except RuntimeError as exc:
        if "license" in str(exc).lower() or "key" in str(exc).lower():
            pytest.skip(f"Moreau license not available: {exc}")
        raise

    np.testing.assert_allclose(r_nat.corrected_action, r_ref.corrected_action, rtol=1e-3, atol=1e-4)
    assert r_ref.solver_status
    assert r_nat.solver_status
    if r_ref.iterations is not None:
        assert r_ref.iterations >= 1
    if r_nat.iterations is not None:
        assert r_nat.iterations >= 1


@pytest.mark.requires_moreau
@pytest.mark.solver
def test_native_compiled_and_legacy_match_reference() -> None:
    """Guard both ``CompiledSolver`` (default) and legacy ``Solver`` paths against CVXPY and each other."""
    moreau = pytest.importorskip("moreau")
    cvxpy = pytest.importorskip("cvxpy")
    if not hasattr(cvxpy, "MOREAU"):
        pytest.skip("cp.MOREAU not available")
    if not hasattr(moreau, "CompiledSolver"):
        pytest.skip("moreau.CompiledSolver not available in this moreau build")

    spec = _spec()
    proposed = np.array([0.85, 0.1, 0.03, 0.02], dtype=np.float64)
    prev = np.full(4, 0.25, dtype=np.float64)

    ref = CVXPYMoreauProjector(spec=spec, options=SolverOptions(device="cpu", max_iter=800, verbose=False))
    nat_compiled = NativeMoreauCompiledProjector(
        spec=spec,
        options=NativeMoreauCompiledOptions(device="cpu", max_iter=800, verbose=False, use_compiled_solver=True),
    )
    nat_legacy = NativeMoreauCompiledProjector(
        spec=spec,
        options=NativeMoreauCompiledOptions(device="cpu", max_iter=800, verbose=False, use_compiled_solver=False),
    )

    try:
        r_ref = ref.project(proposed, prev)
        r_compiled = nat_compiled.project(proposed, prev)
        r_legacy = nat_legacy.project(proposed, prev)
    except RuntimeError as exc:
        if "license" in str(exc).lower() or "key" in str(exc).lower():
            pytest.skip(f"Moreau license not available: {exc}")
        raise

    np.testing.assert_allclose(r_compiled.corrected_action, r_ref.corrected_action, rtol=1e-3, atol=1e-4)
    np.testing.assert_allclose(r_legacy.corrected_action, r_ref.corrected_action, rtol=1e-3, atol=1e-4)
    np.testing.assert_allclose(r_compiled.corrected_action, r_legacy.corrected_action, rtol=1e-4, atol=1e-5)
    assert r_ref.solver_status
    assert r_compiled.solver_status
    assert r_legacy.solver_status


_TELEMETRY_KEYS = frozenset(
    {
        "solver_status",
        "objective_value",
        "warm_started",
        "solve_time_sec",
        "setup_time_sec",
        "iterations",
        "construction_time_sec",
        "device",
    }
)
_OPTIONAL_TIMING = frozenset({"solve_time_sec", "setup_time_sec", "construction_time_sec"})
# CVXPY reference path may omit iterations (None) while native Moreau reports them; device may differ.
_OPTIONAL_REFERENCE_NATIVE_DIFF = _OPTIONAL_TIMING | frozenset({"iterations", "device"})


def _telemetry_present_keys(d: dict) -> frozenset[str]:
    return frozenset(k for k in _TELEMETRY_KEYS if d.get(k) is not None)


def _status_success_like(status: str) -> bool:
    """CVXPY uses strings like 'optimal'; native Moreau may return vendor codes (e.g. '1')."""
    s = str(status).strip().lower()
    if s in ("1", "true", "ok"):
        return True
    return "optimal" in s or s in ("solved", "success", "converged")


@pytest.mark.requires_moreau
@pytest.mark.solver
def test_reference_native_projection_telemetry_key_parity() -> None:
    cvxpy = pytest.importorskip("cvxpy")
    if not hasattr(cvxpy, "MOREAU"):
        pytest.skip("cp.MOREAU not available")

    spec = _spec()
    proposed = np.array([0.85, 0.1, 0.03, 0.02], dtype=np.float64)
    prev = np.full(4, 0.25, dtype=np.float64)

    ref = CVXPYMoreauProjector(spec=spec, options=SolverOptions(device="cpu", max_iter=800, verbose=False))
    nat = NativeMoreauCompiledProjector(spec=spec, options=NativeMoreauCompiledOptions(device="cpu", max_iter=800))

    try:
        r_ref = ref.project(proposed, prev)
        r_nat = nat.project(proposed, prev)
    except RuntimeError as exc:
        if "license" in str(exc).lower() or "key" in str(exc).lower():
            pytest.skip(f"Moreau license not available: {exc}")
        raise

    ref_keys = _telemetry_present_keys(r_ref.as_dict())
    nat_keys = _telemetry_present_keys(r_nat.as_dict())
    assert ref_keys ^ nat_keys <= _OPTIONAL_REFERENCE_NATIVE_DIFF, (ref_keys, nat_keys)
    assert _status_success_like(r_ref.solver_status) == _status_success_like(r_nat.solver_status)


@pytest.mark.requires_moreau
def test_native_warm_start_second_call() -> None:
    spec = _spec()
    proposed = np.array([0.6, 0.2, 0.1, 0.1], dtype=np.float64)
    prev = np.full(4, 0.25, dtype=np.float64)
    proj = NativeMoreauCompiledProjector(
        spec=spec,
        options=NativeMoreauCompiledOptions(device="cpu", max_iter=500, persist_warm_start=True),
    )
    try:
        a = proj.project(proposed, prev)
        b = proj.project(proposed, prev)
    except RuntimeError as exc:
        if "license" in str(exc).lower():
            pytest.skip(str(exc))
        raise
    np.testing.assert_allclose(a.corrected_action, b.corrected_action, rtol=1e-5, atol=1e-6)
    assert a.solver_status
    assert b.solver_status
    if a.iterations is not None:
        assert a.iterations >= 1
    if b.iterations is not None:
        assert b.iterations >= 1
