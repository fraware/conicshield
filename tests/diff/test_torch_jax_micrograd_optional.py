"""Optional torch/jax: micrograd vs FD (same probes as differentiation_check)."""

from __future__ import annotations

import importlib.util
import sys
from types import ModuleType

import pytest

from tests._repo import repo_root


def _load_differentiation_check_script() -> ModuleType:
    path = repo_root() / "scripts" / "differentiation_check.py"
    name = "_conicshield_differentiation_check_script_torchjax"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load script module from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_torch_micrograd_probe_when_installed() -> None:
    torch = pytest.importorskip("torch")
    assert torch is not None
    mod = _load_differentiation_check_script()
    out = mod._micrograd_fd_torch(h=1e-6)
    assert out["import_ok"] is True
    assert out.get("fd_ok") is True


def test_jax_micrograd_probe_when_installed() -> None:
    pytest.importorskip("jax")
    mod = _load_differentiation_check_script()
    out = mod._micrograd_fd_jax(h=1e-6)
    assert out["import_ok"] is True
    assert out.get("fd_ok") is True
