"""Capability / availability status for gradient backends (fail closed)."""

from __future__ import annotations

from enum import StrEnum


class CapabilityStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    BLOCKED = "blocked"
