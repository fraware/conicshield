from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

GateStatus = Literal["green", "red", "unknown"]
RunState = Literal["experimental", "candidate", "review-locked", "published", "deprecated"]


@dataclass(slots=True)
class PublishedRunRecord:
    run_id: str
    family_id: str
    task_contract_version: str
    fixture_version: str
    state: RunState
    artifact_gate: GateStatus
    parity_gate: GateStatus
    promotion_gate: GateStatus
    review_locked: bool
    publishable_arms: list[str]
    published_at_utc: str | None = None
    deprecated_at_utc: str | None = None
    reason: str | None = None
