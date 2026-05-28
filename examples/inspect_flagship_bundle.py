#!/usr/bin/env python3
"""Walk through host-realistic-20260525: README, metadata, governance, summary."""

from __future__ import annotations

import sys
from pathlib import Path

from conicshield.published_runs import (
    get_current_run,
    load_provenance,
    load_summary,
    verify_run,
)

FLAGSHIP = "host-realistic-20260525"
FAMILY = "conicshield-transition-bank-v1"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass
    root = Path.cwd()
    verify_run(FLAGSHIP, repo_root=root)
    print(f"integrity OK: {FLAGSHIP}\n")

    bundle = get_current_run(FAMILY, repo_root=root)
    assert bundle.run_id == FLAGSHIP

    readme = bundle.path / "README.md"
    print("=== README (first lines) ===")
    if readme.is_file():
        for line in readme.read_text(encoding="utf-8").splitlines()[:12]:
            print(line)
    print()

    meta_path = bundle.path / "COMMUNITY_METADATA.json"
    print("=== COMMUNITY_METADATA.json ===")
    print("path:", meta_path.relative_to(root))
    if bundle.community:
        c = bundle.community
        print("evidence_tier:", c.evidence_tier)
        print("host_realistic:", c.host_realistic)
        print("includes_native_arm:", c.includes_native_arm)
        print("export_kind:", c.export_kind)
        print("parity_status:", c.parity_status)
        print("recommended_uses:", c.recommended_uses[:2], "...")
        print("known_limitations:", c.known_limitations[0])
    print()

    print("=== governance_status.json ===")
    gov = bundle.governance_status or {}
    print("state:", gov.get("state"))
    print("publishable_arms:", gov.get("publishable_arms"))
    print("gates:", {k: gov.get(k) for k in ("artifact_gate", "parity_gate", "promotion_gate")})
    native_in_summary = "shielded-native-moreau" in {r.label for r in load_summary(FLAGSHIP, repo_root=root)}
    print("native arm in summary.json:", native_in_summary)
    print()

    prov = load_provenance(FLAGSHIP, repo_root=root)
    print("=== RUN_PROVENANCE.json ===")
    print("projector_mode:", prov.projector_mode)
    print("host_realistic_evidence:", prov.host_realistic_evidence)
    print("export_source:", prov.export_source)
    print()

    print("=== summary.json arms ===")
    for row in load_summary(FLAGSHIP, repo_root=root):
        print(f"  {row.label}: p50_ms={row.solve_time_p50_ms}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
