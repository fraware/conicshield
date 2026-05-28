#!/usr/bin/env python3
"""Walk through host-realistic-20260525 publication artifact fields.

Audience: researcher validating the flagship bundle without governance internals.
Prerequisites: ``pip install -e .`` from repo root.
Proves: index integrity, evidence tier, host-realistic flag, native arm, governance gates, provenance.
Does not prove: Maps/session navigation graph, autograd product, or universal batch speedup.
Expected: integrity OK; printed tier/host_realistic/native/governance/verify status lines.
"""

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

    print("=== verify_run (index integrity) ===")
    verify_run(FLAGSHIP, repo_root=root)
    print("integrity OK")

    bundle = get_current_run(FAMILY, repo_root=root)
    assert bundle.run_id == FLAGSHIP

    print("\n=== README (first lines) ===")
    readme = bundle.path / "README.md"
    if readme.is_file():
        for line in readme.read_text(encoding="utf-8").splitlines()[:10]:
            print(line)

    print("\n=== COMMUNITY_METADATA.json ===")
    print("path:", (bundle.path / "COMMUNITY_METADATA.json").relative_to(root))
    if bundle.community:
        c = bundle.community
        print("evidence_tier:", c.evidence_tier)
        print("host_realistic:", c.host_realistic)
        print("includes_native_arm:", c.includes_native_arm)
        print("export_kind:", c.export_kind)
        print("parity_status:", c.parity_status)

    print("\n=== governance_status.json ===")
    gov = bundle.governance_status or {}
    print("governance state:", gov.get("state"))
    print("artifact_gate:", gov.get("artifact_gate"))
    print("parity_gate:", gov.get("parity_gate"))
    print("promotion_gate:", gov.get("promotion_gate"))
    print("publishable_arms:", gov.get("publishable_arms"))

    labels = {r.label for r in load_summary(FLAGSHIP, repo_root=root)}
    print("native arm in summary:", "shielded-native-moreau" in labels)

    prov = load_provenance(FLAGSHIP, repo_root=root)
    print("\n=== RUN_PROVENANCE.json ===")
    print("projector_mode:", prov.projector_mode)
    print("host_realistic_evidence:", prov.host_realistic_evidence)
    print("evidence_tier:", prov.evidence_tier)

    print("\n=== summary.json (arms) ===")
    for row in load_summary(FLAGSHIP, repo_root=root):
        print(f"  {row.label}: p50_ms={row.solve_time_p50_ms}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
