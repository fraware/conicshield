"""Layer F: differentiation_check script contract (public CI + optional solver env)."""

from __future__ import annotations

import importlib.util
import json
import sys
from types import ModuleType

import pytest

from tests._repo import repo_root


def _load_differentiation_check_script() -> ModuleType:
    path = repo_root() / "scripts" / "differentiation_check.py"
    name = "_conicshield_differentiation_check_script"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load script module from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_differentiation_script_produces_valid_json_public_ci() -> None:
    mod = _load_differentiation_check_script()
    data = mod.collect_differentiation_report(
        h=1e-5,
        h_values=[1e-5, 5e-6],
        dims=[0, 1],
        include_native=False,
        probe_torch_jax=True,
        strict=False,
    )
    assert "generated_at_utc" in data
    assert data["status"] in ("deferred", "ok", "partial")
    ex = data.get("extras") or {}
    assert "torch_micrograd" in ex
    assert "jax_micrograd" in ex
    if data["status"] == "deferred":
        assert data.get("reference") is None
    else:
        assert isinstance(data.get("reference"), dict)
        assert "fd_slope" in data["reference"]
        assert isinstance(data.get("reference_grid"), list)
        assert data["reference_grid"]


@pytest.mark.solver
@pytest.mark.requires_moreau
def test_native_fd_slope_when_moreau_available() -> None:
    """Finite-difference slope on native shield path (same scalar objective as reference FD)."""
    cvxpy = pytest.importorskip("cvxpy")
    cp = cvxpy
    if getattr(cp, "MOREAU", None) is None:
        pytest.skip("cp.MOREAU not installed")
    if "MOREAU" not in {str(s).upper() for s in cp.installed_solvers()}:
        pytest.skip("MOREAU not in cvxpy.installed_solvers()")

    mod = _load_differentiation_check_script()
    data = mod.collect_differentiation_report(
        h=1e-5,
        h_values=[1e-5],
        dims=[0],
        include_native=True,
        probe_torch_jax=False,
        strict=False,
    )
    assert data["status"] in ("ok", "partial")
    nat = data.get("native")
    if nat is None:
        pytest.skip("native FD block missing (license or solver error); see errors in report")
    assert isinstance(nat, dict)
    assert "fd_slope" in nat
    assert abs(float(nat["fd_slope"])) < 1e4


@pytest.mark.solver
@pytest.mark.requires_moreau
def test_reference_fd_slope_when_moreau_available() -> None:
    cvxpy = pytest.importorskip("cvxpy")
    cp = cvxpy
    if getattr(cp, "MOREAU", None) is None:
        pytest.skip("cp.MOREAU not installed")
    if "MOREAU" not in {str(s).upper() for s in cp.installed_solvers()}:
        pytest.skip("MOREAU not in cvxpy.installed_solvers()")

    mod = _load_differentiation_check_script()
    data = mod.collect_differentiation_report(
        h=1e-5,
        h_values=[1e-5],
        dims=[0],
        include_native=False,
        probe_torch_jax=False,
        strict=True,
    )
    assert data["status"] == "ok"
    ref = data["reference"]
    assert ref is not None
    assert ref["fd_slope"] == ref["fd_slope"]  # not NaN
    assert abs(float(ref["fd_slope"])) < 1e3


def test_output_differentiation_summary_json_if_present_matches_shape() -> None:
    path = repo_root() / "output" / "differentiation_summary.json"
    if not path.is_file():
        pytest.skip("no output/differentiation_summary.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] in ("deferred", "ok", "partial", "fail")
