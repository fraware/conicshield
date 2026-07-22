"""Exclusive-checkout solver pool for mutable native solver instances.

Concurrency model: ``pooled_exclusive_checkout`` — a checked-out handle is owned
by exactly one caller until ``return_handle``; concurrent use of the same
underlying solver object is rejected.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Condition, RLock
from typing import Any, Generic, TypeVar

from conicshield.compilation.metrics import LifecycleMetrics

T = TypeVar("T")


class SolverPoolCheckoutError(RuntimeError):
    """Raised when a solver cannot be checked out under the declared policy."""


@dataclass(slots=True)
class _PoolEntry(Generic[T]):
    key: str
    solver: T
    in_use: bool = False
    generation: int = 0


@dataclass(slots=True)
class SolverCheckout(Generic[T]):
    """Exclusive ownership token for a pooled solver instance."""

    key: str
    solver: T
    _pool: SolverPool[T]
    _entry_id: int
    _returned: bool = field(default=False, init=False, repr=False)

    def return_to_pool(self, *, clear_state: Callable[[T], None] | None = None) -> None:
        self._pool.return_handle(self, clear_state=clear_state)


@dataclass(slots=True)
class SolverPool(Generic[T]):
    """Bounded per-key pool with exclusive checkout.

    Production caches should check out a solver for the duration of ``solve`` and
    return it before another caller may use the same instance.
    """

    max_per_key: int = 2
    max_keys: int = 64
    metrics: LifecycleMetrics | None = None
    _entries: dict[str, list[_PoolEntry[T]]] = field(default_factory=dict, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)
    _cv: Condition = field(init=False, repr=False)
    _next_id: int = field(default=0, init=False, repr=False)
    _id_to_entry: dict[int, _PoolEntry[T]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if int(self.max_per_key) < 1:
            raise ValueError("max_per_key must be >= 1")
        if int(self.max_keys) < 1:
            raise ValueError("max_keys must be >= 1")
        self.max_per_key = int(self.max_per_key)
        self.max_keys = int(self.max_keys)
        self._cv = Condition(self._lock)

    def checkout(
        self,
        key: str,
        factory: Callable[[], T],
        *,
        timeout_sec: float | None = None,
        block: bool = True,
    ) -> SolverCheckout[T]:
        """Obtain exclusive ownership of a solver for ``key``.

        Creates a new instance via ``factory`` when capacity remains. When all
        instances for ``key`` are busy, waits (if ``block``) or raises
        :class:`SolverPoolCheckoutError`.
        """
        deadline_remaining = None if timeout_sec is None else float(timeout_sec)
        with self._cv:
            while True:
                bucket = self._entries.get(key)
                if bucket is None:
                    if len(self._entries) >= self.max_keys and key not in self._entries:
                        # Evict an idle key with no in-use entries.
                        evicted = self._evict_idle_key_locked(exclude=key)
                        if not evicted:
                            raise SolverPoolCheckoutError(
                                f"solver pool at max_keys={self.max_keys}; no idle key to evict"
                            )
                    bucket = []
                    self._entries[key] = bucket

                for entry in bucket:
                    if not entry.in_use:
                        entry.in_use = True
                        entry_id = self._register_locked(entry)
                        if self.metrics is not None:
                            self.metrics.record_cache_hit()
                        return SolverCheckout(key=key, solver=entry.solver, _pool=self, _entry_id=entry_id)

                if len(bucket) < self.max_per_key:
                    solver = factory()
                    entry = _PoolEntry(key=key, solver=solver, in_use=True)
                    bucket.append(entry)
                    entry_id = self._register_locked(entry)
                    if self.metrics is not None:
                        self.metrics.record_cache_miss()
                        self.metrics.record_solver_rebuild()
                    return SolverCheckout(key=key, solver=entry.solver, _pool=self, _entry_id=entry_id)

                if not block:
                    raise SolverPoolCheckoutError(
                        f"all {self.max_per_key} solvers busy for key={key!r}"
                    )
                if deadline_remaining is not None and deadline_remaining <= 0.0:
                    raise SolverPoolCheckoutError(
                        f"timeout waiting for solver checkout key={key!r}"
                    )
                if deadline_remaining is None:
                    self._cv.wait()
                else:
                    self._cv.wait(timeout=deadline_remaining)
                    # Condition.wait does not report remaining time portably; one wait is enough.
                    deadline_remaining = 0.0

    def return_handle(
        self,
        handle: SolverCheckout[T],
        *,
        clear_state: Callable[[T], None] | None = None,
    ) -> None:
        with self._cv:
            if handle._returned:
                raise SolverPoolCheckoutError("solver checkout already returned")
            entry = self._id_to_entry.get(handle._entry_id)
            if entry is None or entry.solver is not handle.solver:
                raise SolverPoolCheckoutError("solver checkout does not belong to this pool")
            if clear_state is not None:
                clear_state(entry.solver)
            entry.in_use = False
            handle._returned = True
            self._cv.notify_all()

    def _register_locked(self, entry: _PoolEntry[T]) -> int:
        self._next_id += 1
        entry_id = self._next_id
        self._id_to_entry[entry_id] = entry
        return entry_id

    def _evict_idle_key_locked(self, *, exclude: str) -> bool:
        for k, bucket in list(self._entries.items()):
            if k == exclude:
                continue
            if any(e.in_use for e in bucket):
                continue
            del self._entries[k]
            if self.metrics is not None:
                self.metrics.record_eviction(len(bucket))
            return True
        return False

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "keys": len(self._entries),
                "max_keys": self.max_keys,
                "max_per_key": self.max_per_key,
                "in_use": sum(1 for b in self._entries.values() for e in b if e.in_use),
                "pooled": sum(len(b) for b in self._entries.values()),
            }
