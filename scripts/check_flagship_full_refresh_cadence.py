#!/usr/bin/env python3
"""Fail when no live-export-full refresh with authority_ok occurred within max-days."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--max-days", type=int, default=35)
    args = p.parse_args()
    root = _repo_root()
    prov = json.loads(
        (root / "benchmarks" / "external_evidence" / "EXPORT_PROVENANCE.json").read_text(encoding="utf-8")
    )
    history = prov.get("refresh_history") or []
    full = [
        h
        for h in history
        if h.get("workflow") == "live-export-full" and h.get("authority_ok") is True
    ]
    if not full:
        print("No live-export-full refresh with authority_ok in history.", file=sys.stderr)
        return 1
    last = full[-1]
    completed = str(last.get("completed_at_utc", ""))
    then = datetime.strptime(completed, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    age = (datetime.now(UTC) - then).total_seconds() / 86400.0
    if age > args.max_days:
        print(
            f"Last full refresh {completed} is {age:.1f} days old (max {args.max_days}). "
            "Run: make host-realistic-refresh-cycle-licensed",
            file=sys.stderr,
        )
        return 1
    print(f"Full refresh cadence OK: {completed} ({age:.1f} days ago)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
