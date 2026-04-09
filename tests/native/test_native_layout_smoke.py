from __future__ import annotations

import pytest

from conicshield.core.solver_factory import Backend


def test_native_backend_enum_exists() -> None:
    assert Backend.NATIVE_MOREAU.value == "native_moreau"


@pytest.mark.solver
def test_native_marker_subtree_smoke() -> None:
    # Keep a minimal native subtree test for path-based CI targeting.
    assert True
