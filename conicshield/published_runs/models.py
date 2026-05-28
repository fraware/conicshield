"""Typed views of governed published benchmark bundles."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from conicshield.published_run_index import EvidenceTier


@dataclass(frozen=True)
class IntegrityEntry:
    path: str
    sha256: str


@dataclass(frozen=True)
class CommunityMetadata:
    schema_version: str
    run_id: str
    family_id: str
    evidence_tier: EvidenceTier
    host_realistic: bool
    includes_native_arm: bool
    projector_mode: str | None
    is_family_current_run: bool
    parity_fixture_source: bool
    export_kind: str | None
    source_export: str | None
    parity_status: str
    recommended_uses: tuple[str, ...]
    known_limitations: tuple[str, ...]
    solver_stack: dict[str, str] | None = None


@dataclass(frozen=True)
class SummaryRow:
    label: str
    solve_time_p50_ms: float | None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PublishedRunIndexEntry:
    run_id: str
    repository_relative_path: str
    integrity: tuple[IntegrityEntry, ...]
    catalog: dict[str, Any]


@dataclass(frozen=True)
class RunProvenance:
    """Typed view of ``RUN_PROVENANCE.json`` for a published bundle."""

    run_id: str
    evidence_tier: str | None
    projector_mode: str | None
    host_realistic_evidence: bool
    export_source: str | None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PublishedRunBundle:
    run_id: str
    path: Path
    index_entry: PublishedRunIndexEntry
    community: CommunityMetadata | None
    governance_status: dict[str, Any] | None
    run_provenance: dict[str, Any] | None
