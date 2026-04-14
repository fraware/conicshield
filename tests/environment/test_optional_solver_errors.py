from __future__ import annotations

import pytest

from conicshield.solver_errors import MissingSolverExtraError, require_solver_module


def test_require_solver_module_raises_missing_solver_extra() -> None:
    with pytest.raises(MissingSolverExtraError) as ei:
        require_solver_module("definitely_missing_module_conicshield_xyz", "unit test feature")
    assert "definitely_missing_module_conicshield_xyz" in str(ei.value)
    assert "unit test feature" in str(ei.value)
    assert "pip install" in str(ei.value).lower() or ".[solver" in str(ei.value)


def test_missing_solver_extra_is_import_error() -> None:
    assert issubclass(MissingSolverExtraError, ImportError)
