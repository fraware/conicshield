"""Labeled mock sidecar process for research protocol testing only.

Never use as production Moreau / Track 1 sidecar attestation. Opt-in via
``CONICSHIELD_RESEARCH_MOCK_SIDECAR=1`` and explicit ``use_mock=True``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.experimental.adapters.research_sidecar import (
    RESEARCH_SIDECAR_SCHEMA_ID,
    ResearchSidecarCapability,
    ResearchSidecarDisagreementHook,
    SidecarProbeOutcome,
)
from conicshield.experimental.gradients.capability import CapabilityStatus

MOCK_SIDECAR_LABEL = "MOCK_RESEARCH_SIDECAR_NOT_PRODUCTION"
MOCK_SIDECAR_SCHEMA_ID = "research.mock_sidecar_process.v0"


@dataclass(slots=True)
class MockSidecarProcess:
    """In-process mock worker that echoes a simplex projection of the proposal."""

    label: str = MOCK_SIDECAR_LABEL
    schema_id: str = MOCK_SIDECAR_SCHEMA_ID
    enabled: bool = False
    call_count: int = 0
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "label": self.label,
            "enabled": self.enabled,
            "call_count": self.call_count,
            "extras": dict(self.extras),
            "production_attestation": False,
            "note": "Mock sidecar for protocol tests only. Not a live Moreau worker.",
        }

    def project(self, proposed_action: np.ndarray) -> dict[str, Any]:
        self.call_count += 1
        x = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
        # Simplex projection (mock): clip + renormalize
        y = np.maximum(x, 0.0)
        s = float(np.sum(y))
        y = np.ones_like(y) / max(y.size, 1) if s <= 0 else y / s
        return {
            "schema_id": self.schema_id,
            "label": self.label,
            "available": True,
            "corrected_action": y.tolist(),
            "proposed_action": x.tolist(),
            "solver_status": "mock_optimal",
            "canonical_status": "optimal",
            "production_attestation": False,
            "fake_success": False,
            "mock": True,
        }


def mock_sidecar_env_enabled() -> bool:
    return os.environ.get("CONICSHIELD_RESEARCH_MOCK_SIDECAR", "").lower() in {"1", "true", "yes"}


def build_mock_sidecar_capability(*, platform_note: str = "mock") -> ResearchSidecarCapability:
    return ResearchSidecarCapability(
        status=CapabilityStatus.AVAILABLE,
        outcome=SidecarProbeOutcome.AVAILABLE,
        reason="mock_sidecar_process_enabled_for_protocol_tests",
        platform_note=platform_note,
        worker_reachable=True,
        extras={
            "mock": True,
            "label": MOCK_SIDECAR_LABEL,
            "production_attestation": False,
        },
    )


def research_sidecar_project_with_optional_mock(
    proposed_action: np.ndarray,
    *,
    use_mock: bool = False,
    capability: ResearchSidecarCapability | None = None,
) -> dict[str, Any]:
    """Project via mock sidecar when explicitly enabled; else fail-closed real stub."""

    from conicshield.experimental.adapters.research_sidecar import (
        probe_research_sidecar_capability,
        research_sidecar_project,
    )

    if use_mock and mock_sidecar_env_enabled():
        mock = MockSidecarProcess(enabled=True)
        cap = capability or build_mock_sidecar_capability()
        result = mock.project(proposed_action)
        hook = ResearchSidecarDisagreementHook(sidecar_backend="research_mock_sidecar")
        # Build a populated disagreement hook against identity (primary=proposed)
        primary = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
        corrected = np.asarray(result["corrected_action"], dtype=np.float64).reshape(-1)
        l2 = float(np.linalg.norm(primary - corrected))
        return {
            **result,
            "status": str(cap.status),
            "outcome": str(cap.outcome),
            "reason": cap.reason,
            "capability": cap.as_dict(),
            "mock_process": mock.as_dict(),
            "disagreement_hook": {
                **hook.as_dict(),
                "status_disagreement": False,
                "corrected_action_l2": l2,
                "corrected_action_linf": float(np.max(np.abs(primary - corrected))),
                "active_set_symmetric_difference": [],
                "sidecar_capability_status": str(cap.status),
                "sidecar_outcome": str(cap.outcome),
                "consequential": l2 >= 1e-2,
                "available": True,
                "mock": True,
                "label": MOCK_SIDECAR_LABEL,
            },
            "protocol_schema_id": RESEARCH_SIDECAR_SCHEMA_ID,
        }

    # Deterministic skip path when mock requested but env not set
    if use_mock and not mock_sidecar_env_enabled():
        cap = ResearchSidecarCapability(
            status=CapabilityStatus.UNAVAILABLE,
            outcome=SidecarProbeOutcome.SKIPPED,
            reason="mock_requested_but_CONICSHIELD_RESEARCH_MOCK_SIDECAR_not_set",
            platform_note="mock_gate",
            worker_reachable=False,
            extras={"mock_requested": True, "label": MOCK_SIDECAR_LABEL},
        )
        hook = ResearchSidecarDisagreementHook(sidecar_backend="research_mock_sidecar")
        return {
            "available": False,
            "status": str(cap.status),
            "outcome": str(cap.outcome),
            "reason": cap.reason,
            "corrected_action": None,
            "proposed_action": np.asarray(proposed_action, dtype=np.float64).tolist(),
            "disagreement_hook": hook.empty_record(capability=cap),
            "fake_success": False,
            "mock": True,
            "label": MOCK_SIDECAR_LABEL,
        }

    return research_sidecar_project(
        proposed_action,
        capability=capability or probe_research_sidecar_capability(),
    )


def describe_capability_matrix() -> dict[str, Any]:
    """Document CapabilityStatus × SidecarProbeOutcome semantics for research adapters."""

    return {
        "schema_id": "research.sidecar_capability_matrix.v0",
        "capability_status": {s.value: s.name for s in CapabilityStatus},
        "probe_outcomes": {s.value: s.name for s in SidecarProbeOutcome},
        "rules": [
            "AVAILABLE requires worker_reachable=True and attested/mock path.",
            "UNAVAILABLE + FAIL_CLOSED: refuse projection; never invent corrected_action.",
            "UNAVAILABLE + SKIPPED: non-applicable platform or missing mock env.",
            "BLOCKED: reserved for promotion-gated paths; sidecar probe uses UNAVAILABLE.",
            "Mock path must set label=MOCK_RESEARCH_SIDECAR_NOT_PRODUCTION.",
        ],
        "production_claim": False,
    }


def main() -> None:
    print(json.dumps(describe_capability_matrix(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
