"""Serialize inter-sim-rl offline graphs to ``offline_transition_graph_export/v1``."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from conicshield.bench.offline_graph_export import validate_offline_graph_export


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def intersim_checkout_root() -> Path | None:
    env = os.environ.get("INTERSIM_RL_ROOT", "").strip()
    if env and Path(env).is_dir():
        return Path(env).resolve()
    sub = _repo_root() / "third_party" / "inter-sim-rl" / "checkout"
    if sub.is_dir():
        return sub.resolve()
    return None


def fork_graph_for_rehearsal() -> dict[str, list[dict[str, Any]]]:
    """Deterministic multi-branch graph used in inter-sim e2e tests (host-shaped)."""
    return {
        "Root": [
            {
                "destination_address": "NodeA",
                "destination_coords": (1.0, 0.0),
                "first_instruction": "Turn right",
                "action_class": "turn_right",
                "duration_sec": 10.0,
                "distance_m": 100.0,
            },
            {
                "destination_address": "NodeB",
                "destination_coords": (0.0, 1.0),
                "first_instruction": "Turn left",
                "action_class": "turn_left",
                "duration_sec": 12.0,
                "distance_m": 120.0,
            },
        ],
        "NodeA": [
            {
                "destination_address": "NodeC",
                "destination_coords": (2.0, 0.0),
                "first_instruction": "Go straight",
                "action_class": "go_straight",
                "duration_sec": 5.0,
                "distance_m": 50.0,
            },
        ],
        "NodeB": [],
        "NodeC": [],
    }


def transition_graph_to_export_payload(
    *,
    transition_graph: Mapping[str, list[dict[str, Any]]],
    root_address: str = "Root",
    max_depth: int | None = None,
    max_nodes: int | None = None,
) -> dict[str, Any]:
    """Build ``offline_transition_graph_export/v1`` from an inter-sim offline graph dict."""
    coords: dict[str, list[float]] = {}
    if root_address not in coords:
        coords[root_address] = [0.0, 0.0]

    export_graph: dict[str, list[dict[str, Any]]] = {}
    for src, edges in transition_graph.items():
        out_edges: list[dict[str, Any]] = []
        for edge in edges:
            dest = str(edge["destination_address"])
            raw_coords = edge.get("destination_coords")
            if raw_coords is not None:
                coord_pair = [float(raw_coords[0]), float(raw_coords[1])]
                coords[dest] = coord_pair
            elif dest not in coords:
                coords[dest] = [0.0, 0.0]
            out_edges.append(
                {
                    "destination_address": dest,
                    "destination_coords": coords[dest],
                    "first_instruction": str(edge.get("first_instruction", "")),
                    "action_class": str(edge.get("action_class", "")),
                    "duration_sec": float(edge.get("duration_sec", 0.0)),
                    "distance_m": float(edge.get("distance_m", 0.0)),
                }
            )
        export_graph[str(src)] = out_edges

    node_count = len(coords)
    depth = max_depth if max_depth is not None else max(2, len(coords))
    nodes_cap = max_nodes if max_nodes is not None else max(8, node_count * 2)
    payload: dict[str, Any] = {
        "schema_version": "offline_transition_graph_export/v1",
        "root_address": root_address,
        "coords_by_address": coords,
        "transition_graph": export_graph,
        "max_depth": depth,
        "max_nodes": nodes_cap,
    }
    validate_offline_graph_export(payload)
    return payload


def export_from_intersim_env_graph(
    *,
    transition_graph: Mapping[str, list[dict[str, Any]]],
    root_address: str = "Root",
) -> dict[str, Any]:
    """Public entry: serialize a patched-host ``offline_transition_graph`` dict."""
    return transition_graph_to_export_payload(
        transition_graph=transition_graph,
        root_address=root_address,
    )


def export_rehearsal_fork_graph() -> dict[str, Any]:
    """Host-shaped export without a live simulator (CI / structural evidence)."""
    return transition_graph_to_export_payload(transition_graph=fork_graph_for_rehearsal())


def write_export_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
