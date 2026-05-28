#!/usr/bin/env python3
"""Load flagship bundle via published_runs API (typed, no governance deep-dive)."""

from __future__ import annotations

from conicshield.published_runs import (
    get_current_run,
    load_episodes,
    load_provenance,
    load_summary,
    verify_run,
)

FLAGSHIP = "host-realistic-20260525"
FAMILY = "conicshield-transition-bank-v1"


def main() -> int:
    verify_run(FLAGSHIP)
    bundle = get_current_run(FAMILY)
    assert bundle.run_id == FLAGSHIP

    prov = load_provenance(FLAGSHIP)
    print("path:", bundle.path)
    print("tier:", bundle.community.evidence_tier if bundle.community else "n/a")
    print("projector_mode:", prov.projector_mode)
    print("limitations:", (bundle.community.known_limitations[0] if bundle.community else "n/a"))

    rows = load_summary(FLAGSHIP)
    episodes = load_episodes(FLAGSHIP)
    print("arms:", len(rows), "episodes:", len(episodes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
