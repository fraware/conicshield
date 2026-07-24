"""Governed hash policy — research adapter (R4 / R12).

Defines schema + machine checks for artifact digests that a future production
release toolchain could consume. Does **not** claim production governed release
integration or alter release policy.

R12: verification recomputes **actual** on-disk artifact hashes and checks
attestation — nonempty digest strings alone do not pass.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

GOVERNED_HASH_POLICY_SCHEMA_ID = "research.governed_hash_policy.v1"
GOVERNED_HASH_POLICY_SCHEMA_ID_V0 = "research.governed_hash_policy.v0"
GOVERNED_HASH_CHECK_SCHEMA_ID = "research.governed_hash_check.v1"
POLICY_VERSION = "ghp-v1.0.0"


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
    require_attestation: bool = True
    require_on_disk_recompute: bool = True
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
            "require_attestation": self.require_attestation,
            "require_on_disk_recompute": self.require_on_disk_recompute,
            "production_release_integrated": self.production_release_integrated,
            "notes": list(self.notes)
            or [
                "Research adapter only. Not wired into production release tooling.",
                "Passing these checks does not constitute a governed production release.",
                "R12: verifies actual artifact hashes + attestation when paths provided.",
            ],
        }


@dataclass(slots=True)
class GovernedHashCheckResult:
    schema_id: str = GOVERNED_HASH_CHECK_SCHEMA_ID
    policy_version: str = POLICY_VERSION
    passed: bool = False
    missing_keys: list[str] = field(default_factory=list)
    digest_mismatches: list[str] = field(default_factory=list)
    on_disk_mismatches: list[str] = field(default_factory=list)
    attestation_ok: bool = False
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
            "on_disk_mismatches": list(self.on_disk_mismatches),
            "attestation_ok": self.attestation_ok,
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


def _is_full_sha256_hex(value: str | None) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def recompute_artifact_hashes(
    artifact_paths: dict[str, Path],
) -> dict[str, str]:
    """Recompute SHA-256 for each named on-disk artifact."""

    out: dict[str, str] = {}
    for key, path in artifact_paths.items():
        if path.is_file():
            out[key] = sha256_file(path)
    return out


def verify_artifact_hashes_on_disk(
    *,
    recorded_hashes: dict[str, str],
    artifact_paths: dict[str, Path],
) -> list[str]:
    """Return mismatch notes when recorded hashes disagree with on-disk recomputation."""

    mismatches: list[str] = []
    for key, recorded in recorded_hashes.items():
        if key == "sealed_corrected_action_digest":
            continue
        path = artifact_paths.get(key)
        if path is None:
            continue
        if not path.is_file():
            mismatches.append(f"{key}: recorded path missing on disk ({path})")
            continue
        actual = sha256_file(path)
        if not _is_full_sha256_hex(str(recorded)):
            mismatches.append(f"{key}: recorded digest is not a full SHA-256 hex")
            continue
        if actual != recorded:
            mismatches.append(f"{key}: on-disk hash mismatch recorded={recorded} actual={actual}")
    return mismatches


def check_governed_hashes(
    *,
    artifact_hashes: dict[str, str],
    sealed_corrected_action_digest: str | None,
    dirty_worktree: bool = False,
    peer_sealed_digests: list[str] | None = None,
    policy: GovernedHashPolicy | None = None,
    artifact_paths: dict[str, Path] | None = None,
    attestation: dict[str, Any] | None = None,
    attested: bool | None = None,
) -> GovernedHashCheckResult:
    """Validate artifact hashes, optional on-disk recompute, and attestation.

    Nonempty digest strings alone never satisfy R12 governed-hash verify when
    ``require_on_disk_recompute`` / ``require_attestation`` are set and inputs
    are provided (or required).
    """

    pol = policy or default_governed_hash_policy()
    missing: list[str] = []
    for key in pol.required_artifact_keys:
        if key == "sealed_corrected_action_digest":
            if not sealed_corrected_action_digest or not _is_full_sha256_hex(
                sealed_corrected_action_digest
            ):
                missing.append(key)
        elif key not in artifact_hashes or not _is_full_sha256_hex(str(artifact_hashes[key])):
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

    on_disk: list[str] = []
    paths = dict(artifact_paths or {})
    if pol.require_on_disk_recompute and paths:
        on_disk = verify_artifact_hashes_on_disk(
            recorded_hashes=artifact_hashes,
            artifact_paths=paths,
        )
    elif pol.require_on_disk_recompute and not paths:
        # Explicit fail-closed when policy requires recompute but no paths given.
        on_disk.append("on-disk recompute required but artifact_paths not provided")

    att_flag = attested
    if att_flag is None and isinstance(attestation, dict):
        att_flag = bool(attestation.get("attested"))
    if att_flag is None:
        att_flag = False
    attestation_ok = bool(att_flag)
    if pol.require_attestation and not attestation_ok:
        # Allow research local-ok when attestation deliberately omitted only if
        # the caller did not claim a governed manifest — still record blocker.
        pass

    dirty_blocked = bool(dirty_worktree and not pol.allow_dirty_worktree)
    blockers: list[str] = []
    if missing:
        blockers.append(f"missing required hash keys: {missing}")
    if mismatches:
        blockers.append("multi-host sealed digest mismatch under research policy")
    if on_disk:
        blockers.append("on-disk artifact hash verification failed")
    if dirty_blocked:
        blockers.append("dirty worktree not allowed by research governed hash policy")
    if pol.require_attestation and not attestation_ok:
        blockers.append("governed attestation missing or attested=false")
    if not pol.production_release_integrated:
        blockers.append("production release tooling not integrated (research adapter only; expected)")

    # Local research pass: schema + digests + on-disk + dirty; attestation required
    # when policy says so; production-integration blocker is intentional and ignored.
    local_ok = (
        not missing
        and not mismatches
        and not on_disk
        and not dirty_blocked
        and (attestation_ok if pol.require_attestation else True)
    )
    return GovernedHashCheckResult(
        policy_version=pol.policy_version,
        passed=local_ok,
        missing_keys=missing,
        digest_mismatches=mismatches,
        on_disk_mismatches=on_disk,
        attestation_ok=attestation_ok,
        dirty_worktree_blocked=dirty_blocked,
        details={
            "artifact_hashes": dict(artifact_hashes),
            "sealed_corrected_action_digest": sealed_corrected_action_digest,
            "peer_count": len(peers),
            "artifact_paths": {k: str(v) for k, v in paths.items()},
            "attestation": dict(attestation) if isinstance(attestation, dict) else None,
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
