"""CS-SOLVER-004: warm-start / projector cache isolated across episodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.adapters.inter_sim_rl.shield import CANONICAL_ACTION_SPACE, InterSimConicShield
from conicshield.core.result import ProjectionResult
from conicshield.core.solver_factory import Backend
from conicshield.specs.schema import SafetySpec


@dataclass
class _WarmProjector:
    """Minimal projector stand-in that retains warm-start state like native Moreau."""

    _warm: object | None = field(default=None, init=False)
    calls: list[np.ndarray | None] = field(default_factory=list)
    first_solve_outputs: list[np.ndarray] = field(default_factory=list)

    def reset_state(self, *, scope_id: str | None = None) -> None:
        del scope_id
        self._warm = None

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
        x = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
        # Simulate warm-start bias: when warm is present, nudge the correction.
        if self._warm is not None:
            corrected = x.copy()
            corrected[0] = min(1.0, corrected[0] + 0.05)
            corrected = corrected / float(np.sum(corrected))
            warm_started = True
        else:
            corrected = x.copy()
            warm_started = False
            self.first_solve_outputs.append(corrected.copy())
        self._warm = object()
        return ProjectionResult(
            proposed_action=x,
            corrected_action=corrected,
            intervened=not np.allclose(x, corrected),
            intervention_norm=float(np.linalg.norm(corrected - x)),
            solver_status="optimal",
            active_constraints=[],
            metadata={},
            warm_started=warm_started,
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
    assert len(shield._projector_cache) > 0
    cached = next(iter(shield._projector_cache.values()))
    proj = cached.projector
    assert getattr(proj, "_warm", None) is not None

    shield.reset_episode()

    assert shield._previous_distribution is None
    warm_cleared = all(
        getattr(c.projector, "_warm", None) is None for c in shield._projector_cache.values()
    )
    assert warm_cleared


def test_reset_episode_first_solve_matches_fresh_projector() -> None:
    """New episode first-solve must match a fresh projector (no retained warm bias)."""

    def factory(
        spec: SafetySpec,
        backend: Backend,
        cvxpy_options: Any,
        native_options: Any,
    ) -> _WarmProjector:
        del spec, backend, cvxpy_options, native_options
        return _WarmProjector()

    ctx = {
        "allowed_actions": list(CANONICAL_ACTION_SPACE),
        "blocked_actions": [],
        "hazard_score": 0.0,
    }
    q = np.array([2.0, 0.5, 0.1, 0.0], dtype=np.float64)

    fresh = InterSimConicShield(
        backend=Backend.CVXPY_MOREAU,
        use_geometry_prior=False,
        projector_factory=factory,  # type: ignore[arg-type]
    )
    d_fresh = fresh.choose_action(q_values=q, action_space=CANONICAL_ACTION_SPACE, context=ctx)

    reused = InterSimConicShield(
        backend=Backend.CVXPY_MOREAU,
        use_geometry_prior=False,
        projector_factory=factory,  # type: ignore[arg-type]
    )
    reused.choose_action(q_values=q, action_space=CANONICAL_ACTION_SPACE, context=ctx)
    # Second step would warm-start if state leaked across reset.
    reused.choose_action(
        q_values=np.array([0.5, 2.0, 0.1, 0.0], dtype=np.float64),
        action_space=CANONICAL_ACTION_SPACE,
        context=ctx,
    )
    reused.reset_episode()
    d_reset = reused.choose_action(q_values=q, action_space=CANONICAL_ACTION_SPACE, context=ctx)

    np.testing.assert_allclose(
        d_reset.corrected_distribution,
        d_fresh.corrected_distribution,
        rtol=0.0,
        atol=1e-12,
    )
    assert d_reset.projection.warm_started is False
    assert d_fresh.projection.warm_started is False
