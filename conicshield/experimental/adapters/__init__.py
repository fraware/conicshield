"""Local research adapters for Track 1 contracts (replace when Track 1 lands)."""

from __future__ import annotations

from conicshield.experimental.adapters.mock_sidecar import (
    research_sidecar_project_with_optional_mock,
)
from conicshield.experimental.adapters.projection import (
    ResearchBatchProjectionResult,
    ResearchProjectionResult,
    ResearchProjectorProtocol,
)
from conicshield.experimental.adapters.research_sidecar import (
    probe_research_sidecar_capability,
    research_sidecar_project,
)
from conicshield.experimental.adapters.track1_probe import (
    probe_track1_research_readiness,
    write_track1_probe_attestation,
)
from conicshield.experimental.adapters.track1_protocols import (
    CanonicalSolverStatus,
    ReleaseDecision,
    ResearchVerificationReport,
    SolverProvenance,
)

__all__ = [
    "CanonicalSolverStatus",
    "ReleaseDecision",
    "ResearchBatchProjectionResult",
    "ResearchProjectionResult",
    "ResearchProjectorProtocol",
    "ResearchVerificationReport",
    "SolverProvenance",
    "probe_research_sidecar_capability",
    "probe_track1_research_readiness",
    "research_sidecar_project",
    "research_sidecar_project_with_optional_mock",
    "write_track1_probe_attestation",
]
