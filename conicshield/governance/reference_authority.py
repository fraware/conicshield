"""Reference-authority snapshot: flagship release alignment for dashboards and CI."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_FLAGSHIP_RUN_ID = "host-realistic-20260525"
_FAMILY_ID = "conicshield-transition-bank-v1"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object in {path}")
    return payload


def build_reference_authority_snapshot(*, repo_root: Path | None = None) -> dict[str, Any]:
    """Machine-readable flagship + family release state from committed artifacts."""
    root = repo_root if repo_root is not None else Path.cwd()
    current_path = root / "benchmarks" / "releases" / _FAMILY_ID / "CURRENT.json"
    current = _load_json(current_path)
    registry = _load_json(root / "benchmarks" / "registry.json")
    fam = next(f for f in registry["benchmark_families"] if f["family_id"] == _FAMILY_ID)

    flagship_dir = root / "benchmarks" / "published_runs" / _FLAGSHIP_RUN_ID
    prov = _load_json(flagship_dir / "RUN_PROVENANCE.json") if (flagship_dir / "RUN_PROVENANCE.json").is_file() else {}
    gov = (
        _load_json(flagship_dir / "governance_status.json")
        if (flagship_dir / "governance_status.json").is_file()
        else {}
    )
    export_prov_path = root / "benchmarks" / "external_evidence" / "EXPORT_PROVENANCE.json"
    export_prov = _load_json(export_prov_path) if export_prov_path.is_file() else {}

    gates_ok = all(current.get(g) == "green" for g in ("artifact_gate", "parity_gate", "promotion_gate"))
    native_ok = "shielded-native-moreau" in (current.get("publishable_arms") or [])
    bundle_ok = f"benchmarks/published_runs/{_FLAGSHIP_RUN_ID}" in (current.get("benchmark_bundle_paths") or [])
    gov_gates_ok = gov and all(gov.get(g) == "green" for g in ("parity_gate", "promotion_gate"))
    aligned = (
        current.get("current_run_id") == _FLAGSHIP_RUN_ID
        and fam.get("current_run_id") == _FLAGSHIP_RUN_ID
        and current.get("state") == "published"
        and prov.get("evidence_tier") == "vendor_native"
        and prov.get("projector_mode") == "real_projector"
        and gates_ok
        and native_ok
        and bundle_ok
        and gov_gates_ok
    )

    return {
        "schema_version": "conicshield_reference_authority_snapshot/v1",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "family_id": _FAMILY_ID,
        "flagship_run_id": _FLAGSHIP_RUN_ID,
        "aligned": aligned,
        "current_release": {
            "current_run_id": current.get("current_run_id"),
            "state": current.get("state"),
            "publishable_arms": current.get("publishable_arms"),
            "artifact_gate": current.get("artifact_gate"),
            "parity_gate": current.get("parity_gate"),
            "promotion_gate": current.get("promotion_gate"),
            "benchmark_bundle_paths": current.get("benchmark_bundle_paths"),
        },
        "flagship_provenance": {
            "evidence_tier": prov.get("evidence_tier"),
            "projector_mode": prov.get("projector_mode"),
            "source_export_json": prov.get("source_export_json"),
        },
        "flagship_governance": {
            "state": gov.get("state"),
            "parity_gate": gov.get("parity_gate"),
            "promotion_gate": gov.get("promotion_gate"),
        },
        "export_provenance": {
            "export_kind": export_prov.get("export_kind"),
            "export_json": export_prov.get("export_json"),
        },
    }
