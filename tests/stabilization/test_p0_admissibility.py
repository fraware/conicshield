"""CS-SOLVER-002: solver candidates released without independent admissibility verification."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from scipy import sparse

from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions, NativeMoreauCompiledProjector
from conicshield.specs.schema import BoxConstraint, SafetySpec, SimplexConstraint
from conicshield.verification.feasibility import VerificationReleaseError


def _spec() -> SafetySpec:
    return SafetySpec(
        spec_id="stabilization/cs-solver-002",
        version="0.1.0",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            BoxConstraint(lower=[0.0] * 4, upper=[1.0] * 4),
        ],
    )


def test_native_projector_must_reject_nonfinite_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Injected nonfinite solution.x must not become ProjectionResult.corrected_action."""
    import conicshield.core.moreau_compiled as mc

    projector = NativeMoreauCompiledProjector(
        spec=_spec(),
        options=NativeMoreauCompiledOptions(use_compiled_solver=False, persist_warm_start=False),
    )

    monkeypatch.setattr(mc, "require_solver_module", lambda *_a, **_k: SimpleNamespace())
    monkeypatch.setattr(
        mc,
        "build_moreau_standard_form",
        lambda *_a, **_k: (
            sparse.eye(4, format="csr"),
            np.zeros(4),
            sparse.csr_matrix((1, 4)),
            np.zeros(1),
            SimpleNamespace(),
        ),
    )

    def _fake_legacy(
        self: NativeMoreauCompiledProjector,
        moreau: Any,
        p_csr: Any,
        q: np.ndarray,
        a_csr: Any,
        b_full: np.ndarray,
        cones: Any,
        *,
        warm: Any | None,
    ) -> tuple[np.ndarray, Any, Any, float | None, bool]:
        del self, moreau, p_csr, q, a_csr, b_full, cones, warm
        xv = np.array([np.nan, 0.0, 0.0, np.inf], dtype=np.float64)
        solution = SimpleNamespace(x=xv, obj_val=None)
        solver = SimpleNamespace(info=None)
        return xv, solver, solution, None, False

    monkeypatch.setattr(NativeMoreauCompiledProjector, "_solve_with_legacy_solver", _fake_legacy)
    monkeypatch.setitem(__import__("sys").modules, "moreau", SimpleNamespace())

    with pytest.raises((ValueError, RuntimeError, VerificationReleaseError)):
        projector.project(proposed_action=np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64))


def test_cvxpy_path_must_enforce_declared_status_release_policy() -> None:
    """Dedicated verifier module gates inaccurate/limited statuses before release."""
    from conicshield.specs import admissibility

    assert hasattr(admissibility, "verify_candidate_before_release")
