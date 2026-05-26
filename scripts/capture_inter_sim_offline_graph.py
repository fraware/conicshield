#!/usr/bin/env python3
"""Capture ``offline_transition_graph`` JSON from pinned inter-sim-rl ``RLEnvironment``.

Writes the raw graph dict (address -> edges) suitable for
``scripts/refresh_live_upstream_export.py --graph-json``.

Example (host-realistic fork graph via upstream env API):

  python scripts/capture_inter_sim_offline_graph.py \\
    --host-realistic-fork \\
    --out benchmarks/external_evidence/live_dumps/offline_transition_graph_host_realistic.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_rl_environment(intersim_root: Path) -> type[Any]:
    sys.path.insert(0, str(intersim_root))
    try:
        from inter_sim_rl.rl_environment import RLEnvironment  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit(
            f"Cannot import RLEnvironment from {intersim_root}. "
            "Set INTERSIM_RL_ROOT or populate third_party/inter-sim-rl/checkout."
        ) from exc
    finally:
        if sys.path and sys.path[0] == str(intersim_root):
            sys.path.pop(0)
    return RLEnvironment


def _json_safe_graph(graph: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    """Tuples and numpy scalars -> JSON-serializable values."""
    out: dict[str, list[dict[str, Any]]] = {}
    for addr, edges in graph.items():
        row: list[dict[str, Any]] = []
        for edge in edges:
            e = dict(edge)
            coords = e.get("destination_coords")
            if coords is not None:
                e["destination_coords"] = [float(coords[0]), float(coords[1])]
            row.append(e)
        out[str(addr)] = row
    return out


def _capture_provenance_sidecar(
    *,
    repo: Path,
    graph_path: Path,
    intersim_root: Path,
    graph_source: str,
) -> None:
    rev_path = repo / "third_party" / "inter-sim-rl" / "REVISION"
    sha = ""
    repository = ""
    if rev_path.is_file():
        for line in rev_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("sha="):
                sha = line.split("=", 1)[1].strip()
            elif line.startswith("repository="):
                repository = line.split("=", 1)[1].strip()
    try:
        graph_rel = str(graph_path.resolve().relative_to(repo.resolve())).replace("\\", "/")
    except ValueError:
        graph_rel = str(graph_path.resolve())
    sidecar = {
        "schema_version": "conicshield_live_graph_capture/v1",
        "captured_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "graph_json": graph_rel,
        "intersim_root": str(intersim_root),
        "upstream_repository": repository or "https://github.com/fraware/inter-sim-rl",
        "upstream_sha": sha,
        "graph_source": graph_source,
        "capture_method": "RLEnvironment.offline_transition_graph after construct",
    }
    sidecar_path = graph_path.with_suffix(".provenance.json")
    sidecar_path.write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")
    print(sidecar_path, file=sys.stderr)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True, help="Output offline_transition_graph JSON.")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--host-realistic-fork",
        action="store_true",
        help="Use ConicShield host-realistic multi-branch fork (Root→NodeA/NodeB/NodeC).",
    )
    src.add_argument(
        "--upstream-test-fork",
        action="store_true",
        help="Load _fork_graph from inter-sim-rl tests/test_rl_environment_shield.py.",
    )
    p.add_argument(
        "--intersim-root",
        type=Path,
        default=None,
        help="inter-sim-rl checkout (default: INTERSIM_RL_ROOT or third_party/.../checkout).",
    )
    args = p.parse_args()

    repo = _repo_root()
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))

    from conicshield.bench.inter_sim_export import fork_graph_for_rehearsal, intersim_checkout_root

    intersim_root = args.intersim_root or intersim_checkout_root()
    if intersim_root is None:
        raise SystemExit(
            "inter-sim-rl checkout missing. Clone per third_party/inter-sim-rl/README.md "
            "or set INTERSIM_RL_ROOT."
        )

    if args.host_realistic_fork:
        graph_in = fork_graph_for_rehearsal()
        graph_source = "conicshield.bench.inter_sim_export.fork_graph_for_rehearsal"
    else:
        mod_path = intersim_root / "tests" / "test_rl_environment_shield.py"
        if not mod_path.is_file():
            raise SystemExit(f"Missing upstream test module: {mod_path}")
        spec = importlib.util.spec_from_file_location("intersim_shield_tests", mod_path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        graph_in = mod._fork_graph()
        graph_source = "inter_sim_rl.tests.test_rl_environment_shield._fork_graph"

    RLEnvironment = _load_rl_environment(intersim_root)
    sys.path.insert(0, str(intersim_root))
    try:
        env = RLEnvironment(
            starting_address="Root",
            max_intersections=8,
            rule_choice="right",
            offline_transition_graph=graph_in,
            random_seed=0,
        )
        if not callable(getattr(env, "get_shield_context", None)):
            raise SystemExit("RLEnvironment missing get_shield_context; apply M2 patch.")
        env.get_shield_context()
        raw = env.offline_transition_graph
        if raw is None:
            raise SystemExit("RLEnvironment.offline_transition_graph is None after construct.")
        graph_out = _json_safe_graph(raw)
    finally:
        if sys.path and sys.path[0] == str(intersim_root):
            sys.path.pop(0)

    out_path = args.out if args.out.is_absolute() else (repo / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(graph_out, indent=2) + "\n", encoding="utf-8")
    print(out_path)
    _capture_provenance_sidecar(
        repo=repo,
        graph_path=out_path,
        intersim_root=intersim_root,
        graph_source=graph_source,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
