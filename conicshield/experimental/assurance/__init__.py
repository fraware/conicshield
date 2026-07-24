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
    verify_artifact_hashes_on_disk,
)
from conicshield.experimental.assurance.levels import EvidenceKind, EvidenceLevel, VerificationStatus
from conicshield.experimental.assurance.migration import CURRENT_SCHEMA_ID, migration_doc, normalize_bundle_dict
from conicshield.experimental.assurance.multi_host_soak_sim import run_multi_host_soak_simulation
from conicshield.experimental.assurance.platform_soak import (
    REQUIRED_MATRIX_ROLES,
    aggregate_platform_soaks,
    run_platform_soak,
)
from conicshield.experimental.assurance.proof_carrying import (
    DEFAULT_LIMITATIONS,
    PUBLIC_CLAIM,
    PUBLIC_CLAIM_NONCLAIM,
    FlagshipDemoReport,
    FlagshipPromotionGateResult,
    GovernedManifest,
    ProblemManifest,
    ProofCarryingProjection,
    ReplayEvidence,
    VerifiedProjection,
    assemble_proof_carrying_projection,
    evaluate_flagship_promotion_gate,
    run_flagship_demo,
)
from conicshield.experimental.assurance.replay import bundle_from_dict, bundle_to_json, load_bundle, replay_bundle

__all__ = [
    "CURRENT_SCHEMA_ID",
    "DEFAULT_LIMITATIONS",
    "AssuranceBundle",
    "EvidenceKind",
    "EvidenceLevel",
    "FlagshipDemoReport",
    "FlagshipPromotionGateResult",
    "GovernedManifest",
    "PUBLIC_CLAIM",
    "PUBLIC_CLAIM_NONCLAIM",
    "ProblemManifest",
    "ProofCarryingProjection",
    "REQUIRED_MATRIX_ROLES",
    "ReplayEvidence",
    "VerificationStatus",
    "VerifiedProjection",
    "aggregate_platform_soaks",
    "assemble_proof_carrying_projection",
    "build_assurance_bundle",
    "bundle_from_dict",
    "bundle_to_json",
    "check_governed_hashes",
    "corrupt_bundle_action",
    "default_governed_hash_policy",
    "evaluate_flagship_promotion_gate",
    "infer_evidence_level",
    "load_bundle",
    "migration_doc",
    "normalize_bundle_dict",
    "replay_bundle",
    "run_flagship_demo",
    "run_machine_checks",
    "run_multi_host_soak_simulation",
    "run_platform_soak",
    "strip_evidence",
    "verify_artifact_hashes_on_disk",
]
