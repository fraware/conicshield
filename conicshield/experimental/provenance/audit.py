"""Provenance §7 completeness audit for Track 2 experiments."""

from __future__ import annotations

from typing import Any, Protocol


class _ProvenanceLike(Protocol):
    def as_dict(self) -> dict[str, Any]: ...


# Directive section 7 required fields (experiment provenance).
SECTION7_REQUIRED_FIELDS: tuple[str, ...] = (
    "repository_commit",
    "dirty_worktree",
    "scenario_corpus_version",
    "solver_distribution",
    "solver_version",
    "package_source",
    "package_hash",
    "python_version",
    "operating_system",
    "cpu_info",
    "gpu_info",
    "cuda_runtime",
    "cuda_driver",
    "backend",
    "algorithm",
    "solver_settings",
    "random_seeds",
    "batch_size",
    "warm_start_policy",
    "tolerances",
    "fallback_policy",
    "exact_command",
    "start_time_utc",
    "completion_time_utc",
    "output_artifact_hashes",
)


def audit_provenance_completeness(provenance: _ProvenanceLike | dict[str, Any]) -> dict[str, Any]:
    """Return present/missing/nullable map for section-7 provenance fields."""

    data = provenance.as_dict() if hasattr(provenance, "as_dict") else dict(provenance)
    present: list[str] = []
    missing_keys: list[str] = []
    null_allowed: list[str] = []
    null_unexpected: list[str] = []
    nullable = {
        "repository_commit",
        "solver_distribution",
        "solver_version",
        "package_source",
        "package_hash",
        "cpu_info",
        "gpu_info",
        "cuda_runtime",
        "cuda_driver",
        "algorithm",
        "batch_size",
        "warm_start_policy",
        "fallback_policy",
        "completion_time_utc",
    }
    required_non_null = {
        "dirty_worktree",
        "scenario_corpus_version",
        "python_version",
        "operating_system",
        "backend",
        "solver_settings",
        "random_seeds",
        "tolerances",
        "exact_command",
        "start_time_utc",
    }
    for key in SECTION7_REQUIRED_FIELDS:
        if key not in data:
            missing_keys.append(key)
            continue
        present.append(key)
        val = data[key]
        if val is None or val == "":
            if key in nullable:
                null_allowed.append(key)
            elif key in required_non_null:
                null_unexpected.append(key)
            else:
                null_allowed.append(key)
        elif val == {} and key not in {
            "solver_settings",
            "random_seeds",
            "tolerances",
            "output_artifact_hashes",
        }:
            if key in nullable:
                null_allowed.append(key)
            else:
                null_allowed.append(key)
    return {
        "schema": "research.provenance_section7_audit.v0",
        "present": present,
        "missing_keys": missing_keys,
        "null_allowed": null_allowed,
        "null_unexpected": null_unexpected,
        "complete": not missing_keys and not null_unexpected,
        "notes": (
            "Null solver/package fields are allowed when the backend is a stub or "
            "distribution metadata is unavailable; backend/command/corpus must be non-null."
        ),
    }
