"""Concurrency: episode isolation, pool exclusive checkout, lock-protected stress."""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pytest

from conicshield.adapters.inter_sim_rl.shield import CANONICAL_ACTION_SPACE, InterSimConicShield
from conicshield.compilation.metrics import LifecycleMetrics
from conicshield.compilation.solver_pool import SolverPool, SolverPoolCheckoutError
from conicshield.core.interfaces import ConcurrencyModel
from conicshield.core.result import ProjectionResult
from conicshield.core.solver_factory import Backend
from conicshield.specs.schema import SafetySpec


@dataclass
class _ScopedWarmProjector:
    """Projector that tags warm starts with a caller-provided episode token."""

    owner_token: str
    shared_log: list[tuple[str, str]]
    _warm_owner: str | None = field(default=None, init=False)

    def reset_state(self, *, scope_id: str | None = None) -> None:
        del scope_id
        self._warm_owner = None

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
        if self._warm_owner is not None and self._warm_owner != self.owner_token:
            self.shared_log.append((self.owner_token, self._warm_owner))
            raise AssertionError(
                f"warm-start leak: episode {self.owner_token!r} saw warm from {self._warm_owner!r}"
            )
        self._warm_owner = self.owner_token
        x = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
        return ProjectionResult(
            proposed_action=x,
            corrected_action=x.copy(),
            intervened=False,
            intervention_norm=0.0,
            solver_status="optimal",
            active_constraints=[],
            metadata={"owner": self.owner_token},
            warm_started=False,
        )


def test_concurrent_episodes_do_not_exchange_warm_starts() -> None:
    leak_log: list[tuple[str, str]] = []
    barrier = threading.Barrier(2)

    def run_episode(token: str) -> None:
        def factory(
            spec: SafetySpec,
            backend: Backend,
            cvxpy_options: Any,
            native_options: Any,
        ) -> _ScopedWarmProjector:
            del spec, backend, cvxpy_options, native_options
            return _ScopedWarmProjector(owner_token=token, shared_log=leak_log)

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
        barrier.wait()
        for _ in range(20):
            shield.choose_action(q_values=q, action_space=CANONICAL_ACTION_SPACE, context=ctx)
        shield.reset_episode()
        for _ in range(5):
            shield.choose_action(q_values=q, action_space=CANONICAL_ACTION_SPACE, context=ctx)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = [pool.submit(run_episode, "A"), pool.submit(run_episode, "B")]
        for f in futs:
            f.result()
    assert leak_log == []


def test_solver_pool_exclusive_checkout_rejects_double_use() -> None:
    metrics = LifecycleMetrics()
    pool: SolverPool[list[int]] = SolverPool(max_per_key=1, max_keys=4, metrics=metrics)
    created = 0

    def factory() -> list[int]:
        nonlocal created
        created += 1
        return [created]

    h1 = pool.checkout("k", factory, block=False)
    with pytest.raises(SolverPoolCheckoutError):
        pool.checkout("k", factory, block=False)
    h1.return_to_pool()
    h2 = pool.checkout("k", factory, block=False)
    assert h2.solver is h1.solver
    assert created == 1
    h2.return_to_pool()
    with pytest.raises(SolverPoolCheckoutError):
        h2.return_to_pool()


def test_lock_protected_shield_threaded_stress() -> None:
    hits = 0
    lock = threading.Lock()

    def factory(
        spec: SafetySpec,
        backend: Backend,
        cvxpy_options: Any,
        native_options: Any,
    ) -> _ScopedWarmProjector:
        del spec, backend, cvxpy_options, native_options
        return _ScopedWarmProjector(owner_token="shared", shared_log=[])

    shield = InterSimConicShield(
        backend=Backend.CVXPY_MOREAU,
        use_geometry_prior=False,
        projector_factory=factory,  # type: ignore[arg-type]
        concurrency_model=ConcurrencyModel.LOCK_PROTECTED,
    )
    ctx = {
        "allowed_actions": list(CANONICAL_ACTION_SPACE),
        "blocked_actions": [],
        "hazard_score": 0.0,
    }
    q = np.array([1.0, 0.2, 0.1, 0.0], dtype=np.float64)

    def worker() -> None:
        nonlocal hits
        for _ in range(25):
            shield.choose_action(q_values=q, action_space=CANONICAL_ACTION_SPACE, context=ctx)
            with lock:
                hits += 1
        shield.reset_episode()

    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(worker) for _ in range(4)]
        for f in futs:
            f.result()
    assert hits == 100


def test_async_stress_with_lock_protected_shield() -> None:
    def factory(
        spec: SafetySpec,
        backend: Backend,
        cvxpy_options: Any,
        native_options: Any,
    ) -> _ScopedWarmProjector:
        del spec, backend, cvxpy_options, native_options
        return _ScopedWarmProjector(owner_token="async", shared_log=[])

    shield = InterSimConicShield(
        backend=Backend.CVXPY_MOREAU,
        use_geometry_prior=False,
        projector_factory=factory,  # type: ignore[arg-type]
        concurrency_model=ConcurrencyModel.LOCK_PROTECTED,
    )
    ctx = {
        "allowed_actions": list(CANONICAL_ACTION_SPACE),
        "blocked_actions": [],
        "hazard_score": 0.0,
    }
    q = np.array([0.5, 0.5, 0.0, 0.0], dtype=np.float64)

    async def _run() -> None:
        async def one() -> None:
            await asyncio.to_thread(
                shield.choose_action,
                q_values=q,
                action_space=CANONICAL_ACTION_SPACE,
                context=ctx,
            )

        await asyncio.gather(*[one() for _ in range(40)])

    asyncio.run(_run())
    shield.reset_episode()
    assert shield._previous_distribution is None
