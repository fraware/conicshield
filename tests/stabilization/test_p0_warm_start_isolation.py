"""CS-SOLVER-004: warm-start / projector cache not isolated across episodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pytest

from conicshield.adapters.inter_sim_rl.shield import CANONICAL_ACTION_SPACE, InterSimConicShield
from conicshield.core.result import ProjectionResult
from conicshield.core.solver_factory import Backend
from conicshield.specs.schema import SafetySpec


@dataclass
class _WarmProjector:
    """Minimal projector stand-in that retains warm-start state like native Moreau."""

    _warm: object | None = field(default=None, init=False)
    calls: list[np.ndarray | None] = field(default_factory=list)

    def project(
        self,
        proposed_action: np.ndarray,
        previous_action: np.ndarray | None = None,
        *,
        reference_action: np.ndarray | None = None,
        policy_weight: float = 1.0,
        reference_weight: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> ProjectionResult:
        del reference_action, policy_weight, reference_weight, metadata
        self.calls.append(None if previous_action is None else np.asarray(previous_action).copy())
        self._warm = object()  # simulate persist_warm_start
        x = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
        return ProjectionResult(
            proposed_action=x,
            corrected_action=x.copy(),
            intervened=False,
            intervention_norm=0.0,
            solver_status="optimal",
            active_constraints=[],
            metadata={},
            warm_started=True,
        )


@pytest.mark.xfail(
    strict=True,
    reason="CS-SOLVER-004: reset_episode clears previous action but retains cached projectors / warm-start",
)
def test_reset_episode_clears_projector_warm_start_state() -> None:
    warm_holder: dict[str, _WarmProjector] = {}

    def factory(
        spec: SafetySpec,
        backend: Backend,
        cvxpy_options: Any,
        native_options: Any,
    ) -> _WarmProjector:
        del backend, cvxpy_options, native_options
        key = spec.spec_id
        if key not in warm_holder:
            warm_holder[key] = _WarmProjector()
        return warm_holder[key]

    shield = InterSimConicShield(
        backend=Backend.CVXPY_MOREAU,
        use_geometry_prior=False,
        projector_factory=factory,  # type: ignore[arg-type]
    )
    ctx = {
        "allowed_actions": list(CANONICAL_ACTION_SPACE),
        "blocked_actions": [],
        "hazard_score": 0.0,
    }
    q = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    shield.choose_action(q_values=q, action_space=CANONICAL_ACTION_SPACE, context=ctx)
    assert shield._projector_cache
    proj = next(iter(shield._projector_cache.values()))
    assert getattr(proj, "_warm", None) is not None

    shield.reset_episode()

    assert shield._previous_distribution is None
    # Expected after fix: episode reset clears cached warm-start / projector episode state.
    cache_cleared = shield._projector_cache == {}
    warm_cleared = all(
        getattr(p, "_warm", None) is None for p in shield._projector_cache.values()
    )
    assert cache_cleared or warm_cleared
