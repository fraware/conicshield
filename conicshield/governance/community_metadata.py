"""Machine-readable scope metadata for published benchmark bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from conicshield.published_run_index import build_run_catalog_metadata, classify_evidence_tier


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object in {path}")
    return payload


def _recommended_uses(*, tier: str, host_realistic: bool, includes_native: bool) -> list[str]:
    uses: list[str] = ["schema validation examples", "governance state machine reference"]
    if host_realistic:
        uses.append("host-realistic export → bank → publish loop reference")
    if tier == "vendor_native" and includes_native:
        uses.append("native Moreau arm replay under published gates")
    if tier in ("vendor_reference", "vendor_native"):
        uses.append("parity comparison against reference arms in summary.json")
    return uses


def _known_limitations(*, tier: str, host_realistic: bool, export_kind: str) -> list[str]:
    limits = [
        "Not a public autograd or differentiable-shield product claim (see docs/DIFFERENTIATION_PUBLIC_STANCE.md).",
        "Batch throughput is viability-governed only; not universal speedup (see docs/SOLVER_PATHS_AND_BATCHING.md).",
    ]
    if host_realistic and export_kind == "live_upstream_dump":
        limits.append(
            "Graph is host-realistic fork topology via inter-sim RLEnvironment, not a Maps/session navigation graph."
        )
    if tier != "vendor_native":
        limits.append("Native Moreau arm may be absent or not parity-endorsed for this bundle.")
    return limits


def build_community_metadata(
    *,
    run_dir: Path,
    repo_root: Path,
    export_provenance: dict[str, Any] | None = None,
    current_run_id: str | None = None,
) -> dict[str, Any]:
    """Build COMMUNITY_METADATA.json payload for a published run directory."""
    rid = run_dir.name
    tier = classify_evidence_tier(run_dir=run_dir)
    catalog = build_run_catalog_metadata(run_dir=run_dir, repo_root=repo_root)
    prov = _load_json(run_dir / "RUN_PROVENANCE.json")
    export_kind = ""
    if export_provenance:
        export_kind = str(export_provenance.get("export_kind") or "")
    solver_stack: dict[str, str] | None = None
    if (run_dir / "solver_versions.json").is_file():
        raw = _load_json(run_dir / "solver_versions.json")
        solver_stack = {k: str(v) for k, v in raw.items()}

    host = bool(prov.get("host_realistic_evidence"))
    includes_native = bool(catalog.get("includes_native_arm"))
    parity_status = "unknown"
    if (run_dir / "parity_out" / "parity_summary.json").is_file():
        ps = _load_json(run_dir / "parity_out" / "parity_summary.json")
        parity_status = "green" if ps.get("passed") else str(ps.get("status", "present"))

    parity_fixture_source = bool(catalog.get("parity_fixture_source"))
    return {
        "schema_version": "conicshield_community_metadata/v1",
        "run_id": rid,
        "family_id": "conicshield-transition-bank-v1",
        "evidence_tier": tier,
        "host_realistic": host,
        "includes_native_arm": includes_native,
        "projector_mode": prov.get("projector_mode"),
        "is_family_current_run": bool(current_run_id) and rid == current_run_id,
        "parity_fixture_source": parity_fixture_source,
        "export_kind": export_kind or None,
        "source_export": ("benchmarks/external_evidence/offline_graph_export_upstream.json" if host else None),
        "parity_status": parity_status,
        "solver_stack": solver_stack,
        "recommended_uses": _recommended_uses(tier=tier, host_realistic=host, includes_native=includes_native),
        "known_limitations": _known_limitations(tier=tier, host_realistic=host, export_kind=export_kind or "n/a"),
    }
