#!/usr/bin/env python3
"""Write COMMUNITY_METADATA.json for every governed published bundle."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from conicshield.governance.community_metadata import build_community_metadata
from conicshield.published_run_index import load_published_run_index


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
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
        dest.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(dest, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
