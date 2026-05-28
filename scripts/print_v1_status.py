#!/usr/bin/env python3
"""Print human-readable v1 reference system status from committed artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    root = _repo_root()
    path = root / "benchmarks" / "reports" / "reference_system_status.json"
    if not path.is_file():
        print(f"Missing {path}; run: python scripts/generate_reference_system_status.py", file=sys.stderr)
        return 2
    status = json.loads(path.read_text(encoding="utf-8"))
    community = status.get("community_dataset") or {}

    print("ConicShield v1 reference system status")
    print("=" * 40)
    print("flagship_run_id:", status.get("flagship_run_id"))
    print("family_id:", status.get("family_id"))
    print("reference_authority_aligned:", status.get("reference_authority_aligned"))
    print("export_kind:", status.get("export_kind"))
    print("graph_shape:", status.get("graph_shape"))
    print("cadence_policy_ok:", status.get("cadence_policy_ok"))
    print("full_refresh_cadence_ok:", status.get("full_refresh_cadence_ok"))
    print("batch_public_narrative:", status.get("batch_public_narrative"))
    print("published_run_count:", community.get("published_run_count"))
    print("onboarding:", community.get("onboarding_doc"))
    print("api_doc:", community.get("api_doc"))
    print()
    print("Public entry:", "docs/COMMUNITY_LAYER.md")
    print("Release note:", "docs/V1_REFERENCE_RELEASE.md")
    print("Auditor checks: make verify-v1-lock-quick")
    print("Full lock gate: make verify-v1-lock")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
