#!/usr/bin/env python3
"""Single maintainer/CI gate for reference-authority invariants.

Runs published-run index checks, canonical evidence tiers, strict governance audit,
and flagship release alignment (``host-realistic-20260525`` as family ``current_run_id``).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_flagship_alignment(*, root: Path) -> dict[str, Any]:
    family_id = "conicshield-transition-bank-v1"
    flagship = "host-realistic-20260525"
    current_path = root / "benchmarks" / "releases" / family_id / "CURRENT.json"
    current = _load_json(current_path)
    registry = _load_json(root / "benchmarks" / "registry.json")
    fam = next(f for f in registry["benchmark_families"] if f["family_id"] == family_id)

    errors: list[str] = []
    if current.get("current_run_id") != flagship:
        errors.append(f"CURRENT.current_run_id={current.get('current_run_id')!r} expected {flagship!r}")
    if fam.get("current_run_id") != flagship:
        errors.append(f"registry current_run_id={fam.get('current_run_id')!r} expected {flagship!r}")
    if current.get("state") != "published":
        errors.append(f"CURRENT.state={current.get('state')!r} expected 'published'")

    gov_path = root / "benchmarks" / "published_runs" / flagship / "governance_status.json"
    if not gov_path.is_file():
        errors.append(f"missing {gov_path}")
    else:
        gov = _load_json(gov_path)
        for gate in ("artifact_gate", "parity_gate", "promotion_gate"):
            if current.get(gate) != gov.get(gate):
                errors.append(f"CURRENT.{gate}={current.get(gate)!r} != governance {gov.get(gate)!r}")
        if "shielded-native-moreau" not in (current.get("publishable_arms") or []):
            errors.append("CURRENT.publishable_arms missing shielded-native-moreau")

    prov_path = root / "benchmarks" / "published_runs" / flagship / "RUN_PROVENANCE.json"
    if prov_path.is_file():
        prov = _load_json(prov_path)
        if prov.get("evidence_tier") != "vendor_native":
            errors.append(f"flagship evidence_tier={prov.get('evidence_tier')!r} expected vendor_native")
        if prov.get("projector_mode") != "real_projector":
            errors.append(f"flagship projector_mode={prov.get('projector_mode')!r} expected real_projector")

    bundle = f"benchmarks/published_runs/{flagship}"
    if bundle not in (current.get("benchmark_bundle_paths") or []):
        errors.append(f"{bundle} not in CURRENT.benchmark_bundle_paths")

    if errors:
        raise AssertionError("; ".join(errors))

    return {
        "family_id": family_id,
        "flagship_run_id": flagship,
        "current_state": current.get("state"),
        "evidence_tier": _load_json(prov_path).get("evidence_tier") if prov_path.is_file() else None,
        "publishable_arms": current.get("publishable_arms"),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", action="store_true", help="Emit machine-readable summary on stdout.")
    args = p.parse_args()
    root = _repo_root()
    py = sys.executable
    failures: list[str] = []

    steps: list[tuple[str, list[str]]] = [
        ("published_run_index", [py, str(root / "scripts" / "refresh_published_run_index.py"), "--check"]),
        ("governance_audit_strict", [py, "-m", "conicshield.governance.audit_cli", "--strict"]),
    ]
    for name, cmd in steps:
        rc = subprocess.call(cmd, cwd=str(root))
        if rc != 0:
            failures.append(f"{name} exited {rc}")

    try:
        from conicshield.published_run_index import assert_canonical_evidence_tiers

        assert_canonical_evidence_tiers(repo_root=root)
    except Exception as exc:
        failures.append(f"canonical_evidence_tiers: {exc}")

    flagship_summary: dict[str, Any] | None = None
    try:
        flagship_summary = _assert_flagship_alignment(root=root)
    except Exception as exc:
        failures.append(f"flagship_alignment: {exc}")

    summary = {
        "ok": not failures,
        "failures": failures,
        "flagship": flagship_summary,
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        if flagship_summary:
            print(
                f"Flagship: {flagship_summary['flagship_run_id']} "
                f"({flagship_summary.get('evidence_tier')}, state={flagship_summary.get('current_state')})"
            )
        if failures:
            print("FAILURES:", file=sys.stderr)
            for item in failures:
                print(f"  - {item}", file=sys.stderr)
        else:
            print("reference_authority_check: OK")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
