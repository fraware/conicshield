#!/usr/bin/env python3
"""Write COMMUNITY_METADATA.json for every governed published bundle.

Default mode writes files. Pass ``--check`` for a read-only drift check
(CS-SOLVER-007 / verify-* paths).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from conicshield.governance.community_metadata import build_community_metadata
from conicshield.published_run_index import load_published_run_index


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _stable(obj: object) -> str:
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--check",
        action="store_true",
        help="Fail if any COMMUNITY_METADATA.json differs (read-only; no writes).",
    )
    args = p.parse_args()

    root = _repo_root()
    payload = load_published_run_index(repo_root=root)
    export_prov: dict = {}
    ep = root / "benchmarks" / "external_evidence" / "EXPORT_PROVENANCE.json"
    if ep.is_file():
        export_prov = json.loads(ep.read_text(encoding="utf-8"))
    current_path = root / "benchmarks" / "releases" / "conicshield-transition-bank-v1" / "CURRENT.json"
    current_run_id = None
    if current_path.is_file():
        current_run_id = json.loads(current_path.read_text(encoding="utf-8")).get("current_run_id")

    stale: list[str] = []
    for run in payload.get("runs", []):
        rel = str(run["repository_relative_path"]).replace("\\", "/")
        run_dir = root / rel
        meta = build_community_metadata(
            run_dir=run_dir,
            repo_root=root,
            export_provenance=export_prov,
            current_run_id=str(current_run_id) if current_run_id else None,
        )
        dest = run_dir / "COMMUNITY_METADATA.json"
        fresh = json.dumps(meta, indent=2) + "\n"
        if args.check:
            if not dest.is_file():
                stale.append(f"missing {dest}")
                continue
            existing = dest.read_text(encoding="utf-8")
            if _stable(json.loads(existing)) != _stable(meta):
                stale.append(str(dest))
            continue
        dest.write_text(fresh, encoding="utf-8")
        print(dest, file=sys.stderr)

    if args.check:
        if stale:
            for row in stale:
                print(f"stale: {row}", file=sys.stderr)
            print(
                "Run: python scripts/sync_community_metadata.py",
                file=sys.stderr,
            )
            return 2
        print("OK community metadata")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
