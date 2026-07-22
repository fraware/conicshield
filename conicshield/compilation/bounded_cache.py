"""Bounded LRU cache with observable eviction."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from threading import RLock
from typing import Generic, TypeVar

from conicshield.compilation.metrics import LifecycleMetrics

K = TypeVar("K")
V = TypeVar("V")


@dataclass(slots=True)
class BoundedLRUCache(Generic[K, V]):
    """Size-bounded LRU map. Evictions are recorded on ``metrics`` when provided."""

    max_size: int = 64
    metrics: LifecycleMetrics | None = None
    on_evict: Callable[[K, V], None] | None = None
    _data: OrderedDict[K, V] = field(default_factory=OrderedDict, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        if int(self.max_size) < 1:
            raise ValueError("max_size must be >= 1")
        self.max_size = int(self.max_size)

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def __contains__(self, key: object) -> bool:
        with self._lock:
            return key in self._data

    def get(self, key: K) -> V | None:
        with self._lock:
            if key not in self._data:
                if self.metrics is not None:
                    self.metrics.record_cache_miss()
                return None
            self._data.move_to_end(key)
            if self.metrics is not None:
                self.metrics.record_cache_hit()
            return self._data[key]

    def peek(self, key: K) -> V | None:
        """Return value without updating LRU order or metrics."""
        with self._lock:
            return self._data.get(key)

    def put(self, key: K, value: V) -> list[tuple[K, V]]:
        """Insert/update ``key``. Returns list of evicted ``(key, value)`` pairs."""
        evicted: list[tuple[K, V]] = []
        with self._lock:
            if key in self._data:
                self._data[key] = value
                self._data.move_to_end(key)
            else:
                self._data[key] = value
                while len(self._data) > self.max_size:
                    ek, ev = self._data.popitem(last=False)
                    evicted.append((ek, ev))
            if evicted and self.metrics is not None:
                self.metrics.record_eviction(len(evicted))
        if self.on_evict is not None:
            for ek, ev in evicted:
                self.on_evict(ek, ev)
        return evicted

    def values(self) -> list[V]:
        with self._lock:
            return list(self._data.values())

    def items(self) -> list[tuple[K, V]]:
        with self._lock:
            return list(self._data.items())

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __iter__(self) -> Iterator[K]:
        with self._lock:
            return iter(list(self._data.keys()))
