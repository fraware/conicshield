"""Governed hash policy — research adapter only (R4).

Defines schema + machine checks for artifact digests that a future production
release toolchain could consume. Does **not** claim production governed release
integration or alter release policy.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

GOVERNED_HASH_POLICY_SCHEMA_ID = "research.governed_hash_policy.v0"
GOVERNED_HASH_CHECK_SCHEMA_ID = "research.governed_hash_check.v0"
POLICY_VERSION = "ghp-v0.1.0"


@dataclass(slots=True)
class GovernedHashPolicy:
    """Research-local hash policy for soak / assurance artifacts."""

    schema_id: str = GOVERNED_HASH_POLICY_SCHEMA_ID
    policy_version: str = POLICY_VERSION
    hash_algorithm: str = "sha256"
    required_artifact_keys: tuple[str, ...] = (
        "assurance_bundle.json",
        "provenance.json",
        "sealed_corrected_action_digest",
    )
    allow_dirty_worktree: bool = False
    require_multi_host_agreement: bool = True
    production_release_integrated: bool = False
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "policy_version": self.policy_version,
            "hash_algorithm": self.hash_algorithm,
            "required_artifact_keys": list(self.required_artifact_keys),
            "allow_dirty_worktree": self.allow_dirty_worktree,
            "require_multi_host_agreement": self.require_multi_host_agreement,
            "production_release_integrated": self.production_release_integrated,
            "notes": list(self.notes)
            or [
                "Research adapter only. Not wired into production release tooling.",
                "Passing these checks does not constitute a governed production release.",
            ],
        }


@dataclass(slots=True)
class GovernedHashCheckResult:
    schema_id: str = GOVERNED_HASH_CHECK_SCHEMA_ID
    policy_version: str = POLICY_VERSION
    passed: bool = False
    missing_keys: list[str] = field(default_factory=list)
    digest_mismatches: list[str] = field(default_factory=list)
    dirty_worktree_blocked: bool = False
    details: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "policy_version": self.policy_version,
            "passed": self.passed,
            "missing_keys": list(self.missing_keys),
            "digest_mismatches": list(self.digest_mismatches),
            "dirty_worktree_blocked": self.dirty_worktree_blocked,
            "details": dict(self.details),
            "blockers": list(self.blockers),
            "production_claim": False,
        }


def default_governed_hash_policy() -> GovernedHashPolicy:
    return GovernedHashPolicy()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def check_governed_hashes(
    *,
    artifact_hashes: dict[str, str],
    sealed_corrected_action_digest: str | None,
    dirty_worktree: bool = False,
    peer_sealed_digests: list[str] | None = None,
    policy: GovernedHashPolicy | None = None,
) -> GovernedHashCheckResult:
    """Validate artifact hash presence / multi-host agreement under research policy."""

    pol = policy or default_governed_hash_policy()
    missing: list[str] = []
    for key in pol.required_artifact_keys:
        if key == "sealed_corrected_action_digest":
            if not sealed_corrected_action_digest:
                missing.append(key)
        elif key not in artifact_hashes or not artifact_hashes[key]:
            missing.append(key)

    mismatches: list[str] = []
    peers = list(peer_sealed_digests or [])
    if pol.require_multi_host_agreement and peers and sealed_corrected_action_digest:
        disagree = sorted({d for d in peers if d != sealed_corrected_action_digest})
        if disagree:
            mismatches.append(
                f"sealed_corrected_action_digest disagrees with peers: local="
                f"{sealed_corrected_action_digest} peers={disagree}"
            )

    dirty_blocked = bool(dirty_worktree and not pol.allow_dirty_worktree)
    blockers: list[str] = []
    if missing:
        blockers.append(f"missing required hash keys: {missing}")
    if mismatches:
        blockers.append("multi-host sealed digest mismatch under research policy")
    if dirty_blocked:
        blockers.append("dirty worktree not allowed by research governed hash policy")
    if not pol.production_release_integrated:
        blockers.append(
            "production release tooling not integrated (research adapter only; expected)"
        )

    # Research adapter "passed" means local schema checks OK excluding the
    # intentional production-integration blocker.
    local_ok = not missing and not mismatches and not dirty_blocked
    return GovernedHashCheckResult(
        policy_version=pol.policy_version,
        passed=local_ok,
        missing_keys=missing,
        digest_mismatches=mismatches,
        dirty_worktree_blocked=dirty_blocked,
        details={
            "artifact_hashes": dict(artifact_hashes),
            "sealed_corrected_action_digest": sealed_corrected_action_digest,
            "peer_count": len(peers),
            "production_release_integrated": pol.production_release_integrated,
        },
        blockers=blockers,
    )


def write_governed_hash_policy(*, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(default_governed_hash_policy().as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path
