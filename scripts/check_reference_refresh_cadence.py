#!/usr/bin/env python3
"""Fail when flagship refresh is older than policy max-days (monthly cadence guard)."""

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
    prov_path = root / "benchmarks" / "external_evidence" / "EXPORT_PROVENANCE.json"
    if not prov_path.is_file():
        print(f"Missing {prov_path}", file=sys.stderr)
        return 2
    prov = json.loads(prov_path.read_text(encoding="utf-8"))
    last = prov.get("last_flagship_refresh_at_utc")
    if not last:
        print("No last_flagship_refresh_at_utc in EXPORT_PROVENANCE.json", file=sys.stderr)
        return 1
    then = datetime.strptime(str(last), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    age_days = (datetime.now(UTC) - then).total_seconds() / 86400.0
    if age_days > args.max_days:
        print(
            f"Flagship refresh stale: {age_days:.1f} days since {last} (max {args.max_days}). "
            "Run HOST_REALISTIC_REFRESH_PROCEDURE.md on a licensed host.",
            file=sys.stderr,
        )
        return 1
    print(f"Cadence OK: last refresh {last} ({age_days:.1f} days ago)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
