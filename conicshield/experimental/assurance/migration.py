"""AssuranceBundle version migration rules (R9 — v1 semantics)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

SUPPORTED_SCHEMA_IDS: tuple[str, ...] = (
    "research.assurance_bundle.v0",
    "research.assurance_bundle.v0_legacy",
    "research.assurance_bundle.v1",
)

CURRENT_SCHEMA_ID = "research.assurance_bundle.v1"
DEPRECATED_SCHEMA_IDS: frozenset[str] = frozenset(
    {
        "research.assurance_bundle.v0",
        "research.assurance_bundle.v0_legacy",
    }
)

INVALIDATION_PRE_V1 = "pre_v1_digest_semantics"
INVALIDATION_SYNTHETIC_SENSITIVITY = "synthetic_sensitivity_fields"


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
    out["schema_id"] = "research.assurance_bundle.v0"
    return _ensure_v0_fields(out)


def migrate_v0_to_v1(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate v0 → v1 with explicit invalidation watermark (archival-safe).

    Truncated digests are recomputed to full SHA-256 where action/spec bytes
    are available. Overclaimed L3/L4 without live sensitivity / governed
    evidence are downgraded. Promotion remains fail-closed.
    """

    from conicshield.experimental.assurance.evidence import (
        array_digest,
        canonical_json_bytes,
        evidence_bundle_digest,
        forward_solution_digest,
        is_full_sha256_hex,
        problem_digest,
        sha256_hex,
        topology_digest,
    )
    from conicshield.experimental.assurance.levels import EvidenceLevel, VerificationStatus

    _ = canonical_json_bytes  # available for future spec recompute extensions

    out = _ensure_v0_fields(dict(data))
    source_schema = str(out.get("schema_id") or "research.assurance_bundle.v0")
    out["deprecated_source_schema"] = source_schema
    out["schema_id"] = CURRENT_SCHEMA_ID
    out["promotion_eligible"] = False

    reasons: list[str] = [INVALIDATION_PRE_V1]
    action = np.asarray(out.get("corrected_action") or [], dtype=np.float64)
    action_d = array_digest(action) or ""
    out["corrected_action_digest"] = action_d

    spec_digest = str(out.get("specification_digest") or "")
    if not is_full_sha256_hex(spec_digest):
        out["specification_digest"] = sha256_hex(f"v0_spec:{spec_digest}".encode("utf-8"))
        reasons.append("truncated_digest_expanded_via_watermark")

    topo = topology_digest(
        action_dim=int(action.size),
        equality_ids=(),
        inequality_ids=(),
        structural_flags={"migrated_from": source_schema},
    )
    out["topology_digest"] = topo

    prob = problem_digest(
        topology=topo,
        specification={"migrated_spec_digest": out["specification_digest"]},
        proposed_action=action,
        tolerances={},
    )
    out["problem_digest"] = prob

    prim = out.get("primal_evidence") or {}
    eq = prim.get("equality_residual") if isinstance(prim, dict) else None
    ineq = prim.get("inequality_residual") if isinstance(prim, dict) else None
    residuals_present = eq is not None and ineq is not None
    ver = out.get("verification") or {}
    if not residuals_present and isinstance(ver, dict):
        eq = ver.get("equality_residual")
        ineq = ver.get("inequality_residual")
        residuals_present = eq is not None and ineq is not None

    feasible = bool(
        (prim.get("feasible") if isinstance(prim, dict) and "feasible" in prim else None)
        if isinstance(prim, dict) and "feasible" in prim
        else (ver.get("primal_feasible") if isinstance(ver, dict) else False)
    )
    if not residuals_present:
        status = VerificationStatus.UNVERIFIED
        reasons.append("missing_residuals")
    elif feasible:
        status = VerificationStatus.VERIFIED_FEASIBLE
    else:
        status = VerificationStatus.VERIFIED_INFEASIBLE
    out["verification_status"] = str(status)

    if isinstance(prim, dict):
        prim = dict(prim)
        prim["residuals_present"] = residuals_present
        out["primal_evidence"] = prim

    forward = forward_solution_digest(
        problem=prob,
        corrected_action=action,
        equality_residual=None if eq is None else float(eq),
        inequality_residual=None if ineq is None else float(ineq),
        dual_values=None,
        canonical_status=str(out.get("canonical_status") or "unknown"),
        verification_status=str(status),
        residual_tolerance=float((ver or {}).get("residual_tolerance") or 1e-8)
        if isinstance(ver, dict)
        else 1e-8,
    )
    out["forward_solution_digest"] = forward

    sens = out.get("sensitivity_evidence")
    if isinstance(sens, dict) and sens:
        sens = dict(sens)
        if sens.get("fd_comparison_passed") is not True or sens.get("synthetic") is not False:
            sens["synthetic"] = True
            reasons.append(INVALIDATION_SYNTHETIC_SENSITIVITY)
        sens["forward_solution_digest"] = forward
        out["sensitivity_evidence"] = sens

    shadow = out.get("shadow_evidence")
    if isinstance(shadow, dict) and shadow:
        shadow = dict(shadow)
        shadow["problem_digest"] = prob
        if shadow.get("copied_from_primary") is None:
            shadow["copied_from_primary"] = shadow.get("primary_backend") == shadow.get("shadow_backend")
        out["shadow_evidence"] = shadow

    level = str(out.get("evidence_level") or EvidenceLevel.L0_RECORDED)
    if level in {EvidenceLevel.L3_SENSITIVITY_VALIDATED, EvidenceLevel.L4_REPLAYED_AND_GOVERNED}:
        sens_ok = (
            isinstance(out.get("sensitivity_evidence"), dict)
            and out["sensitivity_evidence"].get("synthetic") is False
            and out["sensitivity_evidence"].get("fd_comparison_passed") is True
        )
        gov_ok = bool((out.get("extras") or {}).get("governed_manifest"))
        if level == EvidenceLevel.L4_REPLAYED_AND_GOVERNED and not (sens_ok and gov_ok):
            if sens_ok:
                level = str(EvidenceLevel.L3_SENSITIVITY_VALIDATED)
            elif out.get("shadow_evidence"):
                level = str(EvidenceLevel.L2_SHADOW_COMPARED)
            elif status == VerificationStatus.VERIFIED_FEASIBLE:
                level = str(EvidenceLevel.L1_FEASIBILITY_VERIFIED)
            else:
                level = str(EvidenceLevel.L0_RECORDED)
            out["release_decision"] = "experimental_invalidated"
            reasons.append("downgraded_l4_without_governed_live_evidence")
        elif level == EvidenceLevel.L3_SENSITIVITY_VALIDATED and not sens_ok:
            if out.get("shadow_evidence"):
                level = str(EvidenceLevel.L2_SHADOW_COMPARED)
            elif status == VerificationStatus.VERIFIED_FEASIBLE:
                level = str(EvidenceLevel.L1_FEASIBILITY_VERIFIED)
            else:
                level = str(EvidenceLevel.L0_RECORDED)
            out["release_decision"] = "experimental_invalidated"
            reasons.append("downgraded_l3_without_live_sensitivity")
        out["evidence_level"] = level

    if status == VerificationStatus.UNVERIFIED:
        out["evidence_level"] = str(EvidenceLevel.L0_RECORDED)

    out["evidence_bundle_digest"] = evidence_bundle_digest(
        forward=forward,
        shadow=out.get("shadow_evidence") if isinstance(out.get("shadow_evidence"), dict) else None,
        sensitivity=out.get("sensitivity_evidence") if isinstance(out.get("sensitivity_evidence"), dict) else None,
        provenance=out.get("solver_provenance") if isinstance(out.get("solver_provenance"), dict) else None,
        replay={"migrated": True},
        governed_manifest=(out.get("extras") or {}).get("governed_manifest"),
    )
    if not is_full_sha256_hex(str(out.get("structural_fingerprint") or "")):
        out["structural_fingerprint"] = topo

    out["invalidation_reason"] = ";".join(dict.fromkeys(reasons))
    extras = dict(out.get("extras") or {})
    extras["migrated_to_v1"] = True
    extras["promotion_eligible"] = False
    if INVALIDATION_SYNTHETIC_SENSITIVITY in reasons:
        extras["sensitivity_fields_synthetic"] = True
    out["extras"] = extras
    return _ensure_v1_fields(out)


MIGRATION_RULES: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "research.assurance_bundle.v0_legacy": migrate_v0_legacy_to_v0,
    "research.assurance_bundle.v0": migrate_v0_to_v1,
}


class AssuranceMigrationError(ValueError):
    """Raised when a bundle schema cannot be migrated."""


def normalize_bundle_dict(
    data: dict[str, Any],
    *,
    target_schema: str = CURRENT_SCHEMA_ID,
    archival: bool = False,
) -> dict[str, Any]:
    """Migrate or validate a serialized bundle dict toward ``target_schema``.

    Rules:
    - Missing ``schema_id`` is treated as ``research.assurance_bundle.v0``.
    - ``v0_legacy`` → ``v0`` → ``v1`` (when target is v1).
    - ``v0`` remains loadable as deprecated/invalidated when ``archival=True``.
    - Unknown future schemas raise unless an explicit migration rule exists.
    """

    out = dict(data)
    schema = str(out.get("schema_id") or "research.assurance_bundle.v0")
    out["schema_id"] = schema

    if archival and schema in DEPRECATED_SCHEMA_IDS:
        if schema == "research.assurance_bundle.v0_legacy":
            out = migrate_v0_legacy_to_v0(out)
        else:
            out = _ensure_v0_fields(out)
        out["promotion_eligible"] = False
        out["invalidation_reason"] = out.get("invalidation_reason") or INVALIDATION_PRE_V1
        extras = dict(out.get("extras") or {})
        extras["archival_load"] = True
        extras["promotion_eligible"] = False
        out["extras"] = extras
        return out

    if schema == target_schema:
        return _ensure_v1_fields(out) if target_schema == CURRENT_SCHEMA_ID else _ensure_v0_fields(out)

    current = out
    current_schema = schema
    guard = 0
    while current_schema != target_schema and guard < 5:
        guard += 1
        if current_schema == "research.assurance_bundle.v0_legacy":
            current = migrate_v0_legacy_to_v0(current)
            current_schema = str(current.get("schema_id"))
            continue
        if current_schema == "research.assurance_bundle.v0" and target_schema == CURRENT_SCHEMA_ID:
            current = migrate_v0_to_v1(current)
            current_schema = str(current.get("schema_id"))
            continue
        if current_schema in MIGRATION_RULES:
            current = MIGRATION_RULES[current_schema](current)
            current_schema = str(current.get("schema_id"))
            continue
        break

    if str(current.get("schema_id")) != target_schema:
        if current_schema not in SUPPORTED_SCHEMA_IDS:
            raise AssuranceMigrationError(
                f"unsupported assurance schema {current_schema!r}; supported={SUPPORTED_SCHEMA_IDS}"
            )
        raise AssuranceMigrationError(f"cannot migrate {schema!r} -> {target_schema!r}")

    return _ensure_v1_fields(current) if target_schema == CURRENT_SCHEMA_ID else _ensure_v0_fields(current)


def _ensure_v0_fields(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)
    out.setdefault("schema_id", "research.assurance_bundle.v0")
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


def _ensure_v1_fields(data: dict[str, Any]) -> dict[str, Any]:
    out = _ensure_v0_fields(data)
    out["schema_id"] = CURRENT_SCHEMA_ID
    out.setdefault("topology_digest", "")
    out.setdefault("problem_digest", "")
    out.setdefault("forward_solution_digest", "")
    out.setdefault("evidence_bundle_digest", "")
    out.setdefault("verification_status", "UNVERIFIED")
    out.setdefault("promotion_eligible", False)
    out.setdefault(
        "naming_note",
        "Use 'proof-carrying' only with an explicit evidence taxonomy. "
        "Evidence levels are numerical assurance tiers, not universal safety guarantees "
        "or system-level safety proofs. L4 is numerical assurance, not a safety proof.",
    )
    return out


def migration_doc() -> str:
    return (
        "AssuranceBundle migration rules\n"
        "================================\n"
        f"- Current schema: {CURRENT_SCHEMA_ID}\n"
        "- Missing schema_id => treat as v0 (deprecated)\n"
        "- research.assurance_bundle.v0_legacy => migrate_v0_legacy_to_v0 "
        "(action->corrected_action, level->evidence_level)\n"
        "- research.assurance_bundle.v0 => migrate_v0_to_v1 "
        f"(full digests, three-valued verification, invalidate promotion; "
        f"reason={INVALIDATION_PRE_V1})\n"
        "- v0 remains loadable archival with watermark when archival=True\n"
        "- Forward migrations must be explicit callables in MIGRATION_RULES\n"
        "- Do not silently reinterpret evidence kinds or levels\n"
        "- Evidence levels are numerical assurance tiers, not universal safety guarantees\n"
        "- L4 is numerical assurance, not a system safety proof\n"
    )
