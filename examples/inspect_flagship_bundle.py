#!/usr/bin/env python3
"""Inspect the flagship published bundle end to end (metadata, governance, metrics).

Audience: researcher validating ``host-realistic-20260525`` before citing it.
Prerequisites: ``pip install -e .`` from repo root.
Proves: index integrity, COMMUNITY_METADATA scope, governance gates, summary arms, provenance.
Does not prove: Maps/session navigation graph, autograd product, or universal batch speedup.
Expected: green gates; vendor_native tier; native arm in summary; integrity OK.
"""

from __future__ import annotations

import json

from _common import FAMILY_ID, FLAGSHIP_RUN_ID, configure_stdio, repo_root, section

from conicshield.published_runs import (
    get_current_run,
    load_provenance,
    load_summary,
    verify_run,
)


def main() -> int:
    configure_stdio()
    root = repo_root()

    section("verify_run (SHA-256 vs index)")
    verify_run(FLAGSHIP_RUN_ID, repo_root=root)
    print("integrity OK")

    bundle = get_current_run(FAMILY_ID, repo_root=root)
    if bundle.run_id != FLAGSHIP_RUN_ID:
        print(f"family current is {bundle.run_id!r}, expected {FLAGSHIP_RUN_ID!r}")
        return 1

    section("Bundle README (excerpt)")
    readme = bundle.path / "README.md"
    if readme.is_file():
        for line in readme.read_text(encoding="utf-8").splitlines()[:8]:
            print(line)
    else:
        print("(missing README.md)")

    section("COMMUNITY_METADATA.json")
    meta_path = bundle.path / "COMMUNITY_METADATA.json"
    print("path:", meta_path.relative_to(root))
    if bundle.community:
        c = bundle.community
        print("evidence_tier:", c.evidence_tier)
        print("projector_mode:", c.projector_mode)
        print("host_realistic:", c.host_realistic)
        print("includes_native_arm:", c.includes_native_arm)
        print("export_kind:", c.export_kind)
        print("parity_status:", c.parity_status)
        print("is_family_current_run:", c.is_family_current_run)
        if c.recommended_uses:
            print("recommended_uses[0]:", c.recommended_uses[0])

    section("governance_status.json")
    gov = bundle.governance_status or {}
    print("state:", gov.get("state"))
    for gate in ("artifact_gate", "parity_gate", "promotion_gate"):
        print(f"{gate}:", gov.get(gate))
    arms = gov.get("publishable_arms") or []
    print("publishable_arms:", ", ".join(arms) if isinstance(arms, list) else arms)

    section("parity_out (if present)")
    parity_path = bundle.path / "parity_out" / "parity_summary.json"
    if parity_path.is_file():
        ps = json.loads(parity_path.read_text(encoding="utf-8"))
        print("passed:", ps.get("passed"), "status:", ps.get("status"))
    else:
        print("(no parity_summary.json)")

    section("RUN_PROVENANCE.json")
    prov = load_provenance(FLAGSHIP_RUN_ID, repo_root=root)
    print("projector_mode:", prov.projector_mode)
    print("host_realistic_evidence:", prov.host_realistic_evidence)
    print("evidence_tier:", prov.evidence_tier)

    section("summary.json (all arms)")
    labels = set()
    for row in load_summary(FLAGSHIP_RUN_ID, repo_root=root):
        labels.add(row.label)
        print(f"  {row.label}: p50_ms={row.solve_time_p50_ms}")
    print("native arm present:", "shielded-native-moreau" in labels)

    section("Done")
    print("Cite using docs/CITING_CONICSHIELD_ARTIFACTS.md (run_id + commit SHA).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
