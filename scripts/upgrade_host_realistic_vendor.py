#!/usr/bin/env python3
"""Licensed-host upgrade: live export → vendor-backed ``host-realistic-20260525`` publish.

Requires Moreau + patched inter-sim-rl. See ``docs/REFERENCE_EVIDENCE_TIERS.md``.

Example:

  python scripts/export_inter_sim_offline_graph.py \\
    --graph-json /path/to/offline_transition_graph.json \\
    --out benchmarks/external_evidence/offline_graph_export_upstream.json

  python scripts/upgrade_host_realistic_vendor.py \\
    --export-json benchmarks/external_evidence/offline_graph_export_upstream.json
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--export-json",
        type=Path,
        default=None,
        help="offline_transition_graph_export/v1 JSON (default: benchmarks/external_evidence/...).",
    )
    p.add_argument("--run-id", type=str, default="host-realistic-20260525")
    p.add_argument("--force", action="store_true")
    p.add_argument(
        "--refresh-governance",
        action="store_true",
        help="Re-run parity + finalize on existing host-realistic bundle (no bundle rebuild).",
    )
    args = p.parse_args()

    repo = _repo_root()
    export = args.export_json or (
        repo / "benchmarks" / "external_evidence" / "offline_graph_export_upstream.json"
    )
    cmd = [
        sys.executable,
        str(repo / "scripts" / "run_host_realistic_publish.py"),
        "--export-json",
        str(export),
        "--run-id",
        args.run_id,
        "--governance-scaffold",
        "--copy-to-published",
        "--refresh-index",
    ]
    if args.refresh_governance:
        cmd.extend(["--governance-only"])
    else:
        cmd.extend(["--no-passthrough", "--include-native-arm"])
    if args.force:
        cmd.append("--force")
    print("Running:", " ".join(cmd), file=sys.stderr)
    rc = subprocess.call(cmd, cwd=str(repo))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
