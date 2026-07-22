"""State isolation: structural keys, bounded cache, episode reset."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.adapters.inter_sim_rl.shield import CANONICAL_ACTION_SPACE, InterSimConicShield
from conicshield.compilation.bounded_cache import BoundedLRUCache
from conicshield.compilation.metrics import LifecycleMetrics
from conicshield.compilation.structural_keys import numerical_signature, structural_fingerprint
from conicshield.core.result import ProjectionResult
from conicshield.core.solver_factory import Backend
from conicshield.specs.schema import (
    BoxConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)


def _base_spec(*, rate: float = 0.8, allowed: list[int] | None = None) -> SafetySpec:
    return SafetySpec(
        spec_id="state-test",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=allowed or [0, 1, 2, 3]),
            BoxConstraint(lower=[0.0] * 4, upper=[1.0] * 4),
            RateConstraint(max_delta=[rate] * 4),
        ],
    )


def test_structural_fingerprint_ignores_numeric_rates_and_bounds() -> None:
    a = _base_spec(rate=0.2)
    b = SafetySpec(
        spec_id="state-test",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[0, 1, 2, 3]),
            BoxConstraint(lower=[0.0] * 4, upper=[0.5, 1.0, 1.0, 1.0]),
            RateConstraint(max_delta=[0.9] * 4),
        ],
    )
    assert structural_fingerprint(a).digest == structural_fingerprint(b).digest
    assert numerical_signature(a).digest != numerical_signature(b).digest


def test_structural_fingerprint_changes_with_allowed_mask() -> None:
    a = _base_spec(allowed=[0, 1, 2, 3])
    b = _base_spec(allowed=[1])
    assert structural_fingerprint(a).digest != structural_fingerprint(b).digest


def test_bounded_lru_evicts_and_records_metrics() -> None:
    metrics = LifecycleMetrics()
    evicted: list[str] = []
    cache: BoundedLRUCache[str, int] = BoundedLRUCache(
        max_size=2,
        metrics=metrics,
        on_evict=lambda k, _v: evicted.append(k),
    )
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == 1
    cache.put("c", 3)
    assert "b" in evicted
    assert "b" not in cache
    assert len(cache) == 2
    snap = metrics.snapshot()
    assert snap["evictions"] >= 1
    assert snap["cache_hits"] >= 1
    assert snap["cache_misses"] >= 0


@dataclass
class _CountingProjector:
    created_id: int
    _warm: object | None = field(default=None, init=False)
    project_count: int = 0

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
        del previous_action, reference_action, policy_weight, reference_weight, metadata
        self.project_count += 1
        self._warm = object()
        x = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
        return ProjectionResult(
            proposed_action=x,
            corrected_action=x.copy(),
            intervened=False,
            intervention_norm=0.0,
            solver_status="optimal",
            active_constraints=[],
            metadata={},
            warm_started=False,
        )


def test_shield_reuses_projector_across_hazard_rate_changes() -> None:
    created: list[_CountingProjector] = []

    def factory(
        spec: SafetySpec,
        backend: Backend,
        cvxpy_options: Any,
        native_options: Any,
    ) -> _CountingProjector:
        del spec, backend, cvxpy_options, native_options
        proj = _CountingProjector(created_id=len(created))
        created.append(proj)
        return proj

    shield = InterSimConicShield(
        backend=Backend.CVXPY_MOREAU,
        use_geometry_prior=False,
        projector_factory=factory,  # type: ignore[arg-type]
        projector_cache_max_size=8,
    )
    q = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    ctx0 = {
        "allowed_actions": list(CANONICAL_ACTION_SPACE),
        "blocked_actions": [],
        "hazard_score": 0.0,
    }
    ctx1 = {**ctx0, "hazard_score": 0.9}
    shield.choose_action(q_values=q, action_space=CANONICAL_ACTION_SPACE, context=ctx0)
    shield.choose_action(q_values=q, action_space=CANONICAL_ACTION_SPACE, context=ctx1)
    assert len(created) == 1
    assert shield.lifecycle_metrics.snapshot()["cache_hits"] >= 1


def test_shield_cache_bounded_under_adversarial_masks() -> None:
    created = 0

    def factory(
        spec: SafetySpec,
        backend: Backend,
        cvxpy_options: Any,
        native_options: Any,
    ) -> _CountingProjector:
        nonlocal created
        del spec, backend, cvxpy_options, native_options
        created += 1
        return _CountingProjector(created_id=created)

    max_size = 3
    shield = InterSimConicShield(
        backend=Backend.CVXPY_MOREAU,
        use_geometry_prior=False,
        projector_factory=factory,  # type: ignore[arg-type]
        projector_cache_max_size=max_size,
    )
    q = np.array([1.0, 0.2, 0.1, 0.0], dtype=np.float64)
    for i in range(8):
        allowed = [CANONICAL_ACTION_SPACE[i % 4]]
        ctx = {
            "allowed_actions": allowed,
            "blocked_actions": [a for a in CANONICAL_ACTION_SPACE if a not in allowed],
            "hazard_score": 0.0,
        }
        shield.choose_action(q_values=q, action_space=CANONICAL_ACTION_SPACE, context=ctx)
    assert len(shield._projector_cache) <= max_size
    assert shield.lifecycle_metrics.snapshot()["evictions"] >= 1
