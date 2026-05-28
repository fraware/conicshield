#!/usr/bin/env python3
"""Load flagship bundle via published_runs API (typed, no governance deep-dive)."""

from __future__ import annotations

from conicshield.published_runs import load_episodes, load_run, load_summary


def main() -> int:
    bundle = load_run("host-realistic-20260525")
    print("path:", bundle.path)
    print("tier:", bundle.community.evidence_tier if bundle.community else "n/a")
    rows = load_summary(bundle.run_id)
    episodes = load_episodes(bundle.run_id)
    print("arms:", len(rows), "episodes:", len(episodes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
