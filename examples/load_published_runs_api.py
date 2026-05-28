#!/usr/bin/env python3
"""End-to-end walkthrough of the v1 ``conicshield.published_runs`` public API.

Audience: researcher or tool author consuming published bundles.
Prerequisites: ``pip install -e .`` from repo root; no vendor Moreau.
Proves: index listing, integrity verify, current family run, summary + provenance load.
Does not prove: publish pipeline, parity replay, or scientific superiority claims.
Expected: exit 0; prints run ids, OK verify, flagship metadata lines.
"""

from __future__ import annotations

from conicshield.published_runs import (
    get_current_run,
    list_runs,
    load_provenance,
    load_summary,
    verify_run,
)

FAMILY = "conicshield-transition-bank-v1"


def main() -> int:
    print("=== list_runs ===")
    for entry in list_runs():
        print(f"  {entry.run_id}")

    bundle = get_current_run(FAMILY)
    rid = bundle.run_id
    print("\n=== get_current_run ===")
    print("current_run_id:", rid)

    print("\n=== verify_run ===")
    verify_run(rid)
    print("integrity OK")

    print("\n=== load_summary (first two arms) ===")
    for row in load_summary(rid)[:2]:
        print(f"  {row.label}: p50_ms={row.solve_time_p50_ms}")

    prov = load_provenance(rid)
    print("\n=== load_provenance ===")
    print("  tier:", prov.evidence_tier)
    print("  projector_mode:", prov.projector_mode)
    print("  host_realistic:", prov.host_realistic_evidence)

    if bundle.community:
        print("\n=== COMMUNITY_METADATA (limitations excerpt) ===")
        print(" ", bundle.community.known_limitations[0])

    print("\nDone. See docs/PUBLISHED_RUNS_API.md for v1 stability guarantees.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
