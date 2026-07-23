"""Observable lifecycle counters for caches, setup reuse, and warm starts."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass(slots=True)
class LifecycleMetrics:
    """Thread-safe counters for S3 isolation / caching observability."""

    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    setup_reuse: int = 0
    solver_rebuilds: int = 0
    warm_start_hits: int = 0
    warm_start_rejections: int = 0
    cold_retries: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record_cache_hit(self) -> None:
        with self._lock:
            self.cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self.cache_misses += 1

    def record_eviction(self, n: int = 1) -> None:
        with self._lock:
            self.evictions += int(n)

    def record_setup_reuse(self) -> None:
        with self._lock:
            self.setup_reuse += 1

    def record_solver_rebuild(self) -> None:
        with self._lock:
            self.solver_rebuilds += 1

    def record_warm_start_hit(self) -> None:
        with self._lock:
            self.warm_start_hits += 1

    def record_warm_start_rejection(self) -> None:
        with self._lock:
            self.warm_start_rejections += 1

    def record_cold_retry(self) -> None:
        with self._lock:
            self.cold_retries += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "evictions": self.evictions,
                "setup_reuse": self.setup_reuse,
                "solver_rebuilds": self.solver_rebuilds,
                "warm_start_hits": self.warm_start_hits,
                "warm_start_rejections": self.warm_start_rejections,
                "cold_retries": self.cold_retries,
            }

    def reset(self) -> None:
        with self._lock:
            self.cache_hits = 0
            self.cache_misses = 0
            self.evictions = 0
            self.setup_reuse = 0
            self.solver_rebuilds = 0
            self.warm_start_hits = 0
            self.warm_start_rejections = 0
            self.cold_retries = 0
