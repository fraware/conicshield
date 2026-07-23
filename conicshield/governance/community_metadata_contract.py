"""Validate committed ``COMMUNITY_METADATA.json`` payloads against the public schema."""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "conicshield_community_metadata/v1"

REQUIRED_KEYS: tuple[str, ...] = (
    "schema_version",
    "run_id",
    "family_id",
    "evidence_tier",
    "host_realistic",
    "includes_native_arm",
    "projector_mode",
    "is_family_current_run",
    "parity_fixture_source",
    "export_kind",
    "source_export",
    "parity_status",
    "recommended_uses",
    "known_limitations",
)

VALID_EVIDENCE_TIERS = frozenset({"contract_fixture", "structural_export", "vendor_reference", "vendor_native"})


def validate_community_metadata(
    payload: dict[str, Any],
    *,
    expected_run_id: str | None = None,
) -> list[str]:
    """Return human-readable failure messages (empty when valid)."""
    failures: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be a JSON object"]

    for key in REQUIRED_KEYS:
        if key not in payload:
            failures.append(f"missing required field {key!r}")

    schema = payload.get("schema_version")
    if schema != SCHEMA_VERSION:
        failures.append(f"schema_version must be {SCHEMA_VERSION!r}, got {schema!r}")

    rid = payload.get("run_id")
    if expected_run_id is not None and rid != expected_run_id:
        failures.append(f"run_id {rid!r} != expected {expected_run_id!r}")

    tier = payload.get("evidence_tier")
    if tier not in VALID_EVIDENCE_TIERS:
        failures.append(f"invalid evidence_tier {tier!r}")

    for bool_key in ("host_realistic", "includes_native_arm", "is_family_current_run", "parity_fixture_source"):
        if bool_key in payload and not isinstance(payload[bool_key], bool):
            failures.append(f"{bool_key} must be a bool")

    for list_key in ("recommended_uses", "known_limitations"):
        raw = payload.get(list_key)
        if raw is not None and (not isinstance(raw, list) or not raw or not all(isinstance(x, str) for x in raw)):
            failures.append(f"{list_key} must be a non-empty list of strings")

    solver = payload.get("solver_stack")
    if solver is not None and not isinstance(solver, dict):
        failures.append("solver_stack must be an object or null")

    return failures
