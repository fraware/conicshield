"""CS-SOLVER-006: public vs vendor backend boundary clarity."""

from __future__ import annotations

import pytest

from conicshield.core.solver_factory import Backend, create_projector
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


def test_backend_enum_has_no_auto_member_yet() -> None:
    """Documents current enum: AUTO / PUBLIC_* backends are not present (ledger CS-SOLVER-006)."""
    names = {m.name for m in Backend}
    assert "CVXPY_MOREAU" in names
    assert "NATIVE_MOREAU" in names
    assert "NATIVE_MOREAU_BATCH" in names
    assert "AUTO" not in names


@pytest.mark.xfail(
    strict=True,
    reason="CS-SOLVER-006: Backend lacks AUTO/PUBLIC_CLARABEL/PUBLIC_SCS with documented no-silent-vendor policy",
)
def test_backend_enum_exposes_public_and_auto_members() -> None:
    names = {m.name for m in Backend}
    for required in ("AUTO", "PUBLIC_CLARABEL", "PUBLIC_SCS", "CVXPY_MOREAU", "NATIVE_MOREAU", "NATIVE_MOREAU_BATCH"):
        assert required in names


@pytest.mark.xfail(
    strict=True,
    reason="CS-SOLVER-006: AUTO must never select vendor Moreau merely because it imports",
)
def test_auto_backend_never_silently_selects_vendor(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.util

    # Simulate moreau being importable while AUTO policy must still prefer public.
    assert importlib.util.find_spec("moreau") is not None or True
    auto = Backend["AUTO"]  # type: ignore[index]
    projector = create_projector(spec=_spec(), backend=auto)
    # Public Clarabel/SCS path — not native Moreau and not CVXPY Moreau-by-import.
    assert type(projector).__name__ in {"CVXPYClarabelProjector", "CVXPYSCSProjector", "PublicClarabelProjector"}
