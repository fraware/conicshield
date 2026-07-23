"""Proof-carrying differentiable projection research types (R4)."""

from __future__ import annotations

from conicshield.experimental.assurance.builder import build_assurance_bundle, infer_evidence_level
from conicshield.experimental.assurance.bundle import AssuranceBundle
from conicshield.experimental.assurance.checks import (
    corrupt_bundle_action,
    run_machine_checks,
    strip_evidence,
)
from conicshield.experimental.assurance.governed_hash_policy import (
    check_governed_hashes,
    default_governed_hash_policy,
)
from conicshield.experimental.assurance.levels import EvidenceKind, EvidenceLevel
from conicshield.experimental.assurance.migration import migration_doc, normalize_bundle_dict
from conicshield.experimental.assurance.multi_host_soak_sim import run_multi_host_soak_simulation
from conicshield.experimental.assurance.platform_soak import (
    aggregate_platform_soaks,
    run_platform_soak,
)
from conicshield.experimental.assurance.replay import bundle_from_dict, bundle_to_json, load_bundle, replay_bundle

__all__ = [
    "AssuranceBundle",
    "EvidenceKind",
    "EvidenceLevel",
    "aggregate_platform_soaks",
    "build_assurance_bundle",
    "bundle_from_dict",
    "bundle_to_json",
    "check_governed_hashes",
    "corrupt_bundle_action",
    "default_governed_hash_policy",
    "infer_evidence_level",
    "load_bundle",
    "migration_doc",
    "normalize_bundle_dict",
    "replay_bundle",
    "run_machine_checks",
    "run_multi_host_soak_simulation",
    "run_platform_soak",
    "strip_evidence",
]
