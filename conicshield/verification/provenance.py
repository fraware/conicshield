"""Solver provenance records attached to verified projection results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SolverProvenance:
    """Traceability for the solver attempt that produced a released action."""

    backend_id: str
    solver_name: str
    solver_version: str | None = None
    package_distribution: str | None = None
    package_version: str | None = None
    device: str | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    warm_start_policy: str | None = None
    platform_note: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
