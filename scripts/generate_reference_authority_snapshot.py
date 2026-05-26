#!/usr/bin/env python3
"""Write benchmarks/reports/reference_authority_snapshot.json from committed release state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from conicshield.governance.reference_authority import build_reference_authority_snapshot


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default: benchmarks/reports/reference_authority_snapshot.json).",
    )
    p.add_argument("--check", action="store_true", help="Fail if on-disk file differs from fresh snapshot.")
    args = p.parse_args()

    root = _repo_root()
    out = args.out or (root / "benchmarks" / "reports" / "reference_authority_snapshot.json")
    payload = build_reference_authority_snapshot(repo_root=root)
    fresh = json.dumps(payload, indent=2) + "\n"

    def _semantic_key(text: str) -> str:
        data = json.loads(text)
        data.pop("generated_at_utc", None)
        return json.dumps(data, indent=2, sort_keys=True)

    if args.check:
        if not out.is_file():
            print(f"Missing {out}; run: python {Path(__file__).name}", flush=True)
            return 2
        if _semantic_key(out.read_text(encoding="utf-8")) != _semantic_key(fresh):
            print(f"Stale {out}; run: python {Path(__file__).name}", flush=True)
            return 2
        print(f"OK {out}")
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(fresh, encoding="utf-8")
    print(out)
    if not payload.get("aligned"):
        print("warning: flagship alignment check failed in snapshot", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
