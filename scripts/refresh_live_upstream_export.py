#!/usr/bin/env python3
"""Replace committed upstream export with a live inter-sim-rl graph dump.

Updates ``benchmarks/external_evidence/offline_graph_export_upstream.json`` and
``EXPORT_PROVENANCE.json``. Run ``make upgrade-host-realistic-vendor`` afterward on a licensed host.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--graph-json",
        type=Path,
        required=True,
        help="Path to offline_transition_graph JSON from patched inter-sim-rl host.",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Export destination (default: benchmarks/external_evidence/offline_graph_export_upstream.json).",
    )
    p.add_argument(
        "--upstream-notes",
        type=str,
        default="",
        help="Optional free-text note stored in EXPORT_PROVENANCE.json.",
    )
    args = p.parse_args()

    repo = _repo_root()
    out = args.out or (repo / "benchmarks" / "external_evidence" / "offline_graph_export_upstream.json")
    if not args.graph_json.is_file():
        print(f"Graph JSON not found: {args.graph_json}", file=sys.stderr)
        return 2

    cmd = [
        sys.executable,
        str(repo / "scripts" / "export_inter_sim_offline_graph.py"),
        "--graph-json",
        str(args.graph_json),
        "--out",
        str(out),
    ]
    print("Running:", " ".join(cmd), file=sys.stderr)
    rc = subprocess.call(cmd, cwd=str(repo))
    if rc != 0:
        return rc

    prov_path = repo / "benchmarks" / "external_evidence" / "EXPORT_PROVENANCE.json"
    prov: dict[str, object] = {}
    if prov_path.is_file():
        prov = json.loads(prov_path.read_text(encoding="utf-8"))
    prov.update(
        {
            "schema_version": "conicshield_external_export_provenance/v1",
            "export_json": str(out.relative_to(repo)).replace("\\", "/"),
            "upstream_repository": prov.get("upstream_repository", "https://github.com/fraware/inter-sim-rl"),
            "upstream_revision_pin": prov.get("upstream_revision_pin", "third_party/inter-sim-rl/REVISION"),
            "export_kind": "live_upstream_dump",
            "exported_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_graph_json": str(args.graph_json),
            "flagship_run_id": "host-realistic-20260525",
            "notes": args.upstream_notes
            or "Live upstream dump replaced committed structural export. Re-run make upgrade-host-realistic-vendor.",
        }
    )
    prov_path.write_text(json.dumps(prov, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {prov_path}", file=sys.stderr)
    print("\nNext (licensed host):\n  make upgrade-host-realistic-vendor", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
