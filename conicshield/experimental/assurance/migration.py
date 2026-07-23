"""AssuranceBundle version migration rules (R4)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

SUPPORTED_SCHEMA_IDS: tuple[str, ...] = (
    "research.assurance_bundle.v0",
    "research.assurance_bundle.v0_legacy",
)

CURRENT_SCHEMA_ID = "research.assurance_bundle.v0"


def migrate_v0_legacy_to_v0(data: dict[str, Any]) -> dict[str, Any]:
    """Explicit fixture migration: v0_legacy -> v0.

    Legacy differences handled:
    - ``action`` renamed to ``corrected_action``
    - ``level`` renamed to ``evidence_level``
    - missing ``schema_id`` / naming note / empty containers filled
    """

    out = dict(data)
    if "corrected_action" not in out and "action" in out:
        out["corrected_action"] = out.pop("action")
    if "evidence_level" not in out and "level" in out:
        out["evidence_level"] = out.pop("level")
    out["schema_id"] = CURRENT_SCHEMA_ID
    return _ensure_v0_fields(out)


MIGRATION_RULES: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "research.assurance_bundle.v0_legacy": migrate_v0_legacy_to_v0,
}


class AssuranceMigrationError(ValueError):
    """Raised when a bundle schema cannot be migrated."""


def normalize_bundle_dict(
    data: dict[str, Any],
    *,
    target_schema: str = CURRENT_SCHEMA_ID,
) -> dict[str, Any]:
    """Migrate or validate a serialized bundle dict toward ``target_schema``.

    Rules:
    - Missing ``schema_id`` is treated as ``research.assurance_bundle.v0``.
    - ``research.assurance_bundle.v0_legacy`` migrates via ``migrate_v0_legacy_to_v0``.
    - Unknown future schemas raise unless an explicit migration rule exists.
    - Field renames are applied conservatively; unknown extras preserved.
    """

    out = dict(data)
    schema = str(out.get("schema_id") or CURRENT_SCHEMA_ID)
    out["schema_id"] = schema

    if schema == target_schema:
        return _ensure_v0_fields(out)

    if schema in MIGRATION_RULES:
        migrated = MIGRATION_RULES[schema](out)
        if str(migrated.get("schema_id")) != target_schema:
            raise AssuranceMigrationError(f"migration from {schema!r} did not reach {target_schema!r}")
        return _ensure_v0_fields(migrated)

    if schema not in SUPPORTED_SCHEMA_IDS:
        raise AssuranceMigrationError(f"unsupported assurance schema {schema!r}; supported={SUPPORTED_SCHEMA_IDS}")

    if schema != target_schema:
        raise AssuranceMigrationError(f"cannot migrate {schema!r} -> {target_schema!r}")
    return _ensure_v0_fields(out)


def _ensure_v0_fields(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)
    out.setdefault("schema_id", CURRENT_SCHEMA_ID)
    out.setdefault("limitations", [])
    out.setdefault("assumptions", [])
    out.setdefault("fallback_history", [])
    out.setdefault("extras", {})
    out.setdefault(
        "naming_note",
        "Use 'proof-carrying' only with an explicit evidence taxonomy. "
        "Evidence levels are not universal safety guarantees.",
    )
    return out


def migration_doc() -> str:
    return (
        "AssuranceBundle migration rules\n"
        "================================\n"
        f"- Current schema: {CURRENT_SCHEMA_ID}\n"
        "- Missing schema_id => treat as v0\n"
        "- research.assurance_bundle.v0_legacy => migrate_v0_legacy_to_v0 "
        "(action->corrected_action, level->evidence_level)\n"
        "- Forward migrations must be explicit callables in MIGRATION_RULES\n"
        "- Do not silently reinterpret evidence kinds or levels\n"
        "- Evidence levels are assurance tiers, not universal safety guarantees\n"
    )
