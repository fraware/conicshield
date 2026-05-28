#!/usr/bin/env python3
"""Single auditor-facing status artifact for the v1 reference system."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _inter_sim_revision(repo: Path) -> str | None:
    rev = repo / "third_party" / "inter-sim-rl" / "REVISION"
    if not rev.is_file():
        return None
    for line in rev.read_text(encoding="utf-8").splitlines():
        if line.startswith("sha="):
            return line.split("=", 1)[1].strip()
    return None


def _full_refresh_within_days(last_full_at: str | None, *, max_days: float) -> bool:
    if not last_full_at:
        return False
    then = datetime.strptime(str(last_full_at), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    age = (datetime.now(UTC) - then).total_seconds() / 86400.0
    return age <= max_days


def _cadence_days(repo: Path) -> float | None:
    prov_path = repo / "benchmarks" / "external_evidence" / "EXPORT_PROVENANCE.json"
    if not prov_path.is_file():
        return None
    last = _load_json(prov_path).get("last_flagship_refresh_at_utc")
    if not last:
        return None
    then = datetime.strptime(str(last), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    return (datetime.now(UTC) - then).total_seconds() / 86400.0


def build_reference_system_status(*, repo_root: Path) -> dict[str, Any]:
    from conicshield.governance.reference_authority import build_reference_authority_snapshot

    root = repo_root
    snapshot = build_reference_authority_snapshot(repo_root=root)
    prov = _load_json(root / "benchmarks" / "external_evidence" / "EXPORT_PROVENANCE.json")
    history = list(prov.get("refresh_history") or [])
    full_cycles = [h for h in history if h.get("workflow") == "live-export-full" and h.get("authority_ok")]
    last_full_at = full_cycles[-1].get("completed_at_utc") if full_cycles else None
    batch_path = root / "benchmarks" / "reports" / "batch_solve_report.latest.json"
    batch_story = None
    if batch_path.is_file():
        batch_story = _load_json(batch_path).get("batch_story")
    batch_public_narrative = "viability_only"

    age = _cadence_days(root)
    cadence_ok = age is not None and age <= 35.0

    from conicshield.published_run_index import load_published_run_index

    index = load_published_run_index(repo_root=root)
    published_run_count = len(index.get("runs") or [])

    return {
        "schema_version": "conicshield_reference_system_status/v1",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "flagship_run_id": snapshot.get("flagship_run_id"),
        "family_id": snapshot.get("family_id"),
        "reference_authority_aligned": snapshot.get("aligned"),
        "export_kind": prov.get("export_kind"),
        "graph_shape": prov.get("graph_shape"),
        "last_flagship_refresh_at_utc": prov.get("last_flagship_refresh_at_utc"),
        "refresh_count": len(history),
        "full_cycle_refresh_count": len(full_cycles),
        "last_full_refresh_at_utc": last_full_at,
        "cadence_age_days": age,
        "cadence_policy_ok": cadence_ok,
        "full_refresh_cadence_ok": _full_refresh_within_days(last_full_at, max_days=35.0),
        "batch_story": batch_story,
        "batch_public_narrative": batch_public_narrative,
        "community_dataset": {
            "api_module": "conicshield.published_runs",
            "cli_entry": "conicshield-published-runs",
            "community_metadata_schema": "conicshield_community_metadata/v1",
            "published_run_count": published_run_count,
            "verify_make_target": "community-verify",
            "finalize_script": "scripts/finalize_community_dataset.py",
            "onboarding_doc": "docs/COMMUNITY_LAYER.md",
            "api_doc": "docs/PUBLISHED_RUNS_API.md",
            "v1_release_doc": "docs/V1_REFERENCE_RELEASE.md",
        },
        "inter_sim_revision": _inter_sim_revision(root),
        "ci_merge_checks": [
            "quality",
            "conic-trusted-shape",
            "governance-audit",
            "reference-authority",
            "solver-touch",
        ],
        "public_claims": {
            "batch": "true batch path exists; viability-governed; not universal speedup",
            "differentiation": "validation only; not public autograd product",
            "host_realistic_graph": "fork via inter-sim RLEnvironment; not Maps/session navigation",
        },
        "docs": [
            "docs/COMMUNITY_LAYER.md",
            "docs/V1_REFERENCE_RELEASE.md",
            "docs/PUBLISHED_RUNS_API.md",
            "docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md",
            "docs/PUBLIC_CLAIMS.md",
            "docs/QUICKSTART_RESEARCHER.md",
            "docs/QUICKSTART_INTEGRATOR.md",
            "docs/DEVENV.md",
        ],
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Default: benchmarks/reports/reference_system_status.json",
    )
    p.add_argument("--check", action="store_true", help="Fail if committed file differs.")
    args = p.parse_args()

    root = _repo_root()
    out = args.out or (root / "benchmarks" / "reports" / "reference_system_status.json")
    payload = build_reference_system_status(repo_root=root)
    fresh = json.dumps(payload, indent=2) + "\n"

    def _key(text: str) -> str:
        data = json.loads(text)
        data.pop("generated_at_utc", None)
        data.pop("cadence_age_days", None)
        data.pop("full_refresh_cadence_ok", None)
        return json.dumps(data, sort_keys=True)

    if args.check:
        if not out.is_file():
            print(f"Missing {out}; run: python {Path(__file__).name}", file=sys.stderr)
            return 2
        if _key(out.read_text(encoding="utf-8")) != _key(fresh):
            print(f"Stale {out}; run: python {Path(__file__).name}", file=sys.stderr)
            return 2
        print(f"OK {out}")
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(fresh, encoding="utf-8")
    print(out)
    if not payload.get("reference_authority_aligned"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
