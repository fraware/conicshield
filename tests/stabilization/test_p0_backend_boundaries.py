"""CS-SOLVER-006: public vs vendor backend boundary clarity."""

from __future__ import annotations

import importlib

import pytest

from conicshield.backends.base import AUTO_PRODUCTION_ENV, Backend, resolve_backend
from conicshield.backends.public_cvxpy import PublicClarabelProjector, PublicSCSProjector
from conicshield.core.solver_factory import create_projector
from conicshield.specs.compiler import CVXPYMoreauProjector
from conicshield.specs.schema import BoxConstraint, SafetySpec, SimplexConstraint


def _spec() -> SafetySpec:
    return SafetySpec(
        spec_id="stabilization/cs-solver-006",
        version="0.1.0",
        action_dim=2,
        constraints=[
            SimplexConstraint(total=1.0),
            BoxConstraint(lower=[0.0, 0.0], upper=[1.0, 1.0]),
        ],
    )


def test_create_projector_default_is_explicit_cvxpy_moreau() -> None:
    """Default factory selection is explicit CVXPY_MOREAU (not an AUTO policy)."""
    projector = create_projector(spec=_spec())
    assert isinstance(projector, CVXPYMoreauProjector)


def test_backend_enum_exposes_public_and_auto_members() -> None:
    names = {m.name for m in Backend}
    for required in (
        "AUTO",
        "PUBLIC_CLARABEL",
        "PUBLIC_SCS",
        "CVXPY_MOREAU",
        "NATIVE_MOREAU",
        "NATIVE_MOREAU_BATCH",
    ):
        assert required in names


def test_auto_backend_never_silently_selects_vendor(monkeypatch: pytest.MonkeyPatch) -> None:
    # Even if moreau appears importable, AUTO must still prefer public Clarabel.
    monkeypatch.delenv(AUTO_PRODUCTION_ENV, raising=False)
    real_find_spec = importlib.util.find_spec

    def _find_spec(name: str, package: str | None = None):  # noqa: ARG001
        if name == "moreau":
            return object()
        return real_find_spec(name)

    monkeypatch.setattr(importlib.util, "find_spec", _find_spec)
    assert resolve_backend(Backend.AUTO) is Backend.PUBLIC_CLARABEL
    projector = create_projector(spec=_spec(), backend=Backend.AUTO)
    assert type(projector).__name__ in {
        "CVXPYClarabelProjector",
        "CVXPYSCSProjector",
        "PublicClarabelProjector",
    }
    assert isinstance(projector, PublicClarabelProjector)


def test_auto_honors_explicit_production_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(AUTO_PRODUCTION_ENV, "PUBLIC_SCS")
    assert resolve_backend(Backend.AUTO) is Backend.PUBLIC_SCS
    projector = create_projector(spec=_spec(), backend=Backend.AUTO)
    assert isinstance(projector, PublicSCSProjector)


def test_auto_explicit_vendor_override_is_deliberate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vendor via AUTO is allowed only when explicitly configured — not from import."""
    monkeypatch.setenv(AUTO_PRODUCTION_ENV, "cvxpy_moreau")
    assert resolve_backend(Backend.AUTO) is Backend.CVXPY_MOREAU


def test_public_clarabel_projects_without_moreau() -> None:
    pytest.importorskip("cvxpy")
    import cvxpy as cp

    if not hasattr(cp, "CLARABEL"):
        pytest.skip("CLARABEL not available in this environment")
    projector = create_projector(spec=_spec(), backend=Backend.PUBLIC_CLARABEL)
    import numpy as np

    result = projector.project(np.array([0.9, 0.2], dtype=np.float64))
    assert result.corrected_action.shape == (2,)
    assert result.solver_provenance is not None
    assert result.solver_provenance.backend_id == "public_clarabel"
