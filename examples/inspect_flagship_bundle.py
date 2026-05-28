#!/usr/bin/env python3
"""Inspect host-realistic-20260525: verify index, governance, arm summary."""

from __future__ import annotations

from conicshield.published_runs import current_family_run, load_summary, verify_run

FLAGSHIP = "host-realistic-20260525"


def main() -> int:
    verify_run(FLAGSHIP)
    print(f"integrity OK: {FLAGSHIP}")

    bundle = current_family_run("conicshield-transition-bank-v1")
    assert bundle.run_id == FLAGSHIP

    gov = bundle.governance_status or {}
    print("governance state:", gov.get("state"))
    print("publishable_arms:", gov.get("publishable_arms"))
    print("gates:", {k: gov.get(k) for k in ("artifact_gate", "parity_gate", "promotion_gate")})

    if bundle.community:
        print("evidence_tier:", bundle.community.evidence_tier)
        print("export_kind:", bundle.community.export_kind)
        print("limitations:", bundle.community.known_limitations[:2], "...")

    print("\nsummary arms:")
    for row in load_summary(FLAGSHIP):
        print(f"  {row.label}: p50_ms={row.solve_time_p50_ms}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
