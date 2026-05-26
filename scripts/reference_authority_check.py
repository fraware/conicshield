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


def _assert_flagship_alignment(*, root: Path) -> dict[str, Any]:
    from conicshield.governance.reference_authority import build_reference_authority_snapshot

    snapshot = build_reference_authority_snapshot(repo_root=root)
    if not snapshot.get("aligned"):
        raise AssertionError("reference authority snapshot not aligned; see build_reference_authority_snapshot")
    return {
        "family_id": snapshot["family_id"],
        "flagship_run_id": snapshot["flagship_run_id"],
        "current_state": snapshot["current_release"].get("state"),
        "evidence_tier": snapshot["flagship_provenance"].get("evidence_tier"),
        "publishable_arms": snapshot["current_release"].get("publishable_arms"),
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
        (
            "reference_authority_snapshot",
            [py, str(root / "scripts" / "generate_reference_authority_snapshot.py"), "--check"],
        ),
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
