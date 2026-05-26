#!/usr/bin/env python3
"""Write ``offline_transition_graph_export/v1`` JSON from inter-sim-rl or rehearsal graph.

Structural rehearsal (deterministic fork graph, no TensorFlow):

  python scripts/export_inter_sim_offline_graph.py \\
    --rehearsal-fork \\
    --out benchmarks/external_evidence/offline_graph_export_upstream.json

From a patched-host ``offline_transition_graph`` dict saved as JSON
(``{ "Root": [ { "destination_address": ... }, ... ], ... }``):

  python scripts/export_inter_sim_offline_graph.py \\
    --graph-json /path/to/offline_transition_graph.json \\
    --out /tmp/export.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from conicshield.bench.inter_sim_export import (  # noqa: E402
    export_from_intersim_env_graph,
    export_rehearsal_fork_graph,
    write_export_json,
)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--graph-json",
        type=Path,
        help="Raw inter-sim offline_transition_graph dict JSON.",
    )
    src.add_argument(
        "--rehearsal-fork",
        action="store_true",
        help="Emit deterministic multi-branch graph (no upstream import).",
    )
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--root-address", type=str, default="Root")
    args = p.parse_args()

    if args.rehearsal_fork:
        payload = export_rehearsal_fork_graph()
    else:
        assert args.graph_json is not None
        graph = json.loads(args.graph_json.read_text(encoding="utf-8"))
        if not isinstance(graph, dict):
            raise SystemExit("--graph-json must be a JSON object")
        payload = export_from_intersim_env_graph(
            transition_graph=graph,
            root_address=args.root_address,
        )

    write_export_json(payload, args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
