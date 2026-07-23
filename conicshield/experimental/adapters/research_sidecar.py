"""Research-local Windows sidecar / cross-platform protocol stub (adapter-level).

Fail-closed when a live sidecar worker is unavailable. Does **not** compete with
Track 1 production ``conicshield.platform.sidecar_protocol`` contracts; records
``CapabilityStatus`` and disagreement-schema hooks for research experiments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np

from conicshield.experimental.gradients.capability import CapabilityStatus

RESEARCH_SIDECAR_SCHEMA_ID = "research.windows_sidecar_protocol_stub.v0"


def research_sidecar_client_config() -> Any:
    """Build SidecarClientConfig honoring research/operator env overrides.

    Honors ``CONICSHIELD_WSL_PYTHON``, ``CONICSHIELD_WSL_DISTRO``, and
    ``CONICSHIELD_REPO_ROOT`` (same contract as ``start_sidecar_from_env``).
    Does not invent a Moreau worker — only selects the WSL interpreter path.
    """

    import os
    from pathlib import Path

    from conicshield.platform.sidecar_protocol import FallbackPolicy
    from conicshield.platform.windows_sidecar_client import SidecarClientConfig

    cfg = SidecarClientConfig(
        fallback_policy=FallbackPolicy.PUBLIC_CLARABEL,
        require_moreau_on_hello=True,
        max_restarts=0,
        hello_timeout_sec=20.0,
        python_executable=os.environ.get("CONICSHIELD_WSL_PYTHON", "python3"),
        wsl_distro=os.environ.get("CONICSHIELD_WSL_DISTRO") or None,
    )
    root = os.environ.get("CONICSHIELD_REPO_ROOT")
    if root:
        cfg.repo_root = Path(root)
    return cfg


class SidecarProbeOutcome(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    SKIPPED = "skipped"
    FAIL_CLOSED = "fail_closed"


@dataclass(slots=True)
class ResearchSidecarCapability:
    status: CapabilityStatus
    outcome: SidecarProbeOutcome
    reason: str
    platform_note: str
    worker_reachable: bool = False
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": RESEARCH_SIDECAR_SCHEMA_ID,
            "status": str(self.status),
            "outcome": str(self.outcome),
            "reason": self.reason,
            "platform_note": self.platform_note,
            "worker_reachable": self.worker_reachable,
            "extras": dict(self.extras),
            "production_claim": False,
            "note": (
                "Research adapter stub only. Not a production Moreau sidecar client. "
                "Fail closed / skip when worker unavailable — never fake success."
            ),
        }


@dataclass(slots=True)
class ResearchSidecarDisagreementHook:
    """Schema hook for primary-vs-sidecar disagreement records."""

    schema_id: str = "research.sidecar_disagreement_hook.v0"
    primary_backend: str = "cvxpy_clarabel"
    sidecar_backend: str = "research_windows_sidecar_stub"
    fields: tuple[str, ...] = (
        "status_disagreement",
        "corrected_action_l2",
        "corrected_action_linf",
        "active_set_symmetric_difference",
        "sidecar_capability_status",
        "sidecar_outcome",
        "consequential",
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "primary_backend": self.primary_backend,
            "sidecar_backend": self.sidecar_backend,
            "fields": list(self.fields),
        }

    def empty_record(self, *, capability: ResearchSidecarCapability) -> dict[str, Any]:
        """Fail-closed empty disagreement record when sidecar is unavailable."""

        return {
            "schema_id": self.schema_id,
            "status_disagreement": None,
            "corrected_action_l2": None,
            "corrected_action_linf": None,
            "active_set_symmetric_difference": None,
            "sidecar_capability_status": str(capability.status),
            "sidecar_outcome": str(capability.outcome),
            "consequential": False,
            "available": False,
            "reason": capability.reason,
        }


def probe_research_sidecar_capability(
    *,
    force_unavailable: bool = False,
    force_skip: bool = False,
) -> ResearchSidecarCapability:
    """Probe research sidecar availability; never claim success without a live worker.

    CapabilityStatus semantics (research adapter):
    - AVAILABLE: only when an attested live worker is reachable (not implemented here)
      or an explicitly labeled mock path is used via ``mock_sidecar``.
    - UNAVAILABLE: worker missing / not attested / import failure (fail-closed).
    - BLOCKED: reserved for promotion-gated paths; not used by the default probe.
    """

    import sys

    if force_unavailable:
        return ResearchSidecarCapability(
            status=CapabilityStatus.UNAVAILABLE,
            outcome=SidecarProbeOutcome.UNAVAILABLE,
            reason="forced_unavailable_for_tests",
            platform_note=sys.platform,
            worker_reachable=False,
            extras={"capability_semantics": "fail_closed"},
        )
    if force_skip:
        return ResearchSidecarCapability(
            status=CapabilityStatus.UNAVAILABLE,
            outcome=SidecarProbeOutcome.SKIPPED,
            reason="forced_skip_for_tests",
            platform_note=sys.platform,
            worker_reachable=False,
            extras={"capability_semantics": "deterministic_skip"},
        )

    # Prefer reusing Track 1 probe signals when present, but stay research-local.
    try:
        from conicshield.platform import windows_sidecar_client as wsc

        has_client = hasattr(wsc, "WindowsSidecarClient")
    except Exception as exc:  # noqa: BLE001
        return ResearchSidecarCapability(
            status=CapabilityStatus.UNAVAILABLE,
            outcome=SidecarProbeOutcome.UNAVAILABLE,
            reason=f"platform_import_failed:{type(exc).__name__}",
            platform_note=sys.platform,
            worker_reachable=False,
            extras={"capability_semantics": "fail_closed"},
        )

    if sys.platform != "win32":
        return ResearchSidecarCapability(
            status=CapabilityStatus.UNAVAILABLE,
            outcome=SidecarProbeOutcome.SKIPPED,
            reason="non_windows_host_skip",
            platform_note=sys.platform,
            worker_reachable=False,
            extras={
                "has_track1_client_symbol": has_client,
                "capability_semantics": "deterministic_skip",
            },
        )

    # On Windows, still fail closed unless an explicit env opt-in + live worker exists.
    import os

    if os.environ.get("CONICSHIELD_RESEARCH_SIDECAR_ENABLE", "").lower() not in {"1", "true", "yes"}:
        return ResearchSidecarCapability(
            status=CapabilityStatus.UNAVAILABLE,
            outcome=SidecarProbeOutcome.FAIL_CLOSED,
            reason="research_sidecar_not_enabled_via_CONICSHIELD_RESEARCH_SIDECAR_ENABLE",
            platform_note=sys.platform,
            worker_reachable=False,
            extras={
                "has_track1_client_symbol": has_client,
                "capability_semantics": "fail_closed",
                "hint_mock": "set CONICSHIELD_RESEARCH_MOCK_SIDECAR=1 for labeled mock protocol tests",
                "hint_live": (
                    "set CONICSHIELD_RESEARCH_SIDECAR_ENABLE=1 to attempt a live "
                    "WindowsSidecarClient hello (still fail-closed without Moreau worker)"
                ),
            },
        )

    # Opt-in: attempt a real hello; never invent success if the worker is absent.
    try:
        from conicshield.platform.windows_sidecar_client import WindowsSidecarClient

        cfg = research_sidecar_client_config()
        with WindowsSidecarClient(config=cfg) as client:
            running = bool(getattr(client, "is_running", False))
            worker_id = getattr(client, "_worker_id", None)
            if running and worker_id:
                return ResearchSidecarCapability(
                    status=CapabilityStatus.AVAILABLE,
                    outcome=SidecarProbeOutcome.AVAILABLE,
                    reason="live_moreau_sidecar_worker_hello_attested",
                    platform_note=sys.platform,
                    worker_reachable=True,
                    extras={
                        "has_track1_client_symbol": has_client,
                        "capability_semantics": "live_attested",
                        "worker_id_present": True,
                        "s5_s6_status": "live_worker_reachable_research_only",
                        "production_claim": False,
                    },
                )
    except Exception as exc:  # noqa: BLE001
        return ResearchSidecarCapability(
            status=CapabilityStatus.UNAVAILABLE,
            outcome=SidecarProbeOutcome.FAIL_CLOSED,
            reason=f"live_sidecar_hello_failed:{type(exc).__name__}",
            platform_note=sys.platform,
            worker_reachable=False,
            extras={
                "has_track1_client_symbol": has_client,
                "capability_semantics": "fail_closed",
                "hello_error": str(exc),
                "s5_s6_status": "blocked_pending_track1_live_moreau_sidecar",
            },
        )

    return ResearchSidecarCapability(
        status=CapabilityStatus.UNAVAILABLE,
        outcome=SidecarProbeOutcome.FAIL_CLOSED,
        reason="live_moreau_sidecar_worker_not_attested_for_research_stub",
        platform_note=sys.platform,
        worker_reachable=False,
        extras={
            "has_track1_client_symbol": has_client,
            "capability_semantics": "fail_closed",
            "s5_s6_status": "blocked_pending_track1_live_moreau_sidecar",
        },
    )


def research_sidecar_project(
    proposed_action: np.ndarray,
    *,
    capability: ResearchSidecarCapability | None = None,
) -> dict[str, Any]:
    """Attempt a research sidecar projection; fail closed when unavailable."""

    cap = capability or probe_research_sidecar_capability()
    hook = ResearchSidecarDisagreementHook()
    if cap.status != CapabilityStatus.AVAILABLE or not cap.worker_reachable:
        return {
            "available": False,
            "status": str(cap.status),
            "outcome": str(cap.outcome),
            "reason": cap.reason,
            "corrected_action": None,
            "proposed_action": np.asarray(proposed_action, dtype=np.float64).tolist(),
            "disagreement_hook": hook.empty_record(capability=cap),
            "fake_success": False,
        }
    # Live-attested worker: attempt a real project via Track 1 WindowsSidecarClient.
    # Still fail closed on any error; never invent corrected actions.
    try:
        from conicshield.backends.base import Backend
        from conicshield.platform.windows_sidecar_client import WindowsSidecarClient
        from conicshield.specs.schema import BoxConstraint, SafetySpec, SimplexConstraint

        proposed = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
        dim = int(proposed.size)
        spec = SafetySpec(
            spec_id="research/sidecar_live_project",
            version="0.1.0",
            action_dim=dim,
            constraints=[
                SimplexConstraint(total=1.0),
                BoxConstraint(lower=[0.0] * dim, upper=[1.0] * dim),
            ],
        )
        cfg = research_sidecar_client_config()
        with WindowsSidecarClient(config=cfg) as client:
            result = client.project(spec, proposed, backend=Backend.NATIVE_MOREAU)
        corrected = np.asarray(result.corrected_action, dtype=np.float64)
        delta = float(np.linalg.norm(corrected - proposed))
        return {
            "available": True,
            "status": str(CapabilityStatus.AVAILABLE),
            "outcome": str(SidecarProbeOutcome.AVAILABLE),
            "reason": "live_moreau_sidecar_project_attested",
            "corrected_action": corrected.tolist(),
            "proposed_action": proposed.tolist(),
            "intervention_norm": delta,
            "disagreement_hook": {
                "schema_id": hook.schema_id,
                "status_disagreement": None,
                "corrected_action_l2": delta,
                "corrected_action_linf": float(np.max(np.abs(corrected - proposed))),
                "active_set_symmetric_difference": None,
                "sidecar_capability_status": str(CapabilityStatus.AVAILABLE),
                "sidecar_outcome": str(SidecarProbeOutcome.AVAILABLE),
                "consequential": delta > 1e-12,
                "available": True,
                "production_claim": False,
            },
            "fake_success": False,
            "production_claim": False,
        }
    except Exception as exc:  # noqa: BLE001
        fail_cap = ResearchSidecarCapability(
            status=CapabilityStatus.UNAVAILABLE,
            outcome=SidecarProbeOutcome.FAIL_CLOSED,
            reason=f"live_sidecar_project_failed:{type(exc).__name__}",
            platform_note=cap.platform_note,
            worker_reachable=False,
            extras={"error": str(exc)},
        )
        return {
            "available": False,
            "status": str(fail_cap.status),
            "outcome": str(fail_cap.outcome),
            "reason": fail_cap.reason,
            "corrected_action": None,
            "proposed_action": np.asarray(proposed_action, dtype=np.float64).tolist(),
            "disagreement_hook": hook.empty_record(capability=fail_cap),
            "fake_success": False,
        }
