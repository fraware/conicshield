from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from conicshield.bench.transition_bank import TransitionBank, build_transition_bank


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _export_schema() -> dict[str, Any]:
    path = _repo_root() / "schemas" / "offline_transition_graph_export.schema.json"
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def validate_offline_graph_export(payload: dict[str, Any]) -> None:
    Draft202012Validator(_export_schema()).validate(payload)


def transition_bank_from_offline_graph_export(payload: dict[str, Any]) -> TransitionBank:
    """Build a :class:`TransitionBank` from an inter-sim-rl style offline graph export."""
    validate_offline_graph_export(payload)
    root = str(payload["root_address"])
    graph: dict[str, Any] = dict(payload["transition_graph"])
    coords_raw: dict[str, Any] = dict(payload["coords_by_address"])
    max_depth = int(payload.get("max_depth", 4))
    max_nodes = int(payload.get("max_nodes", 400))

    def candidate_builder(address: str) -> list[dict[str, Any]]:
        edges = graph.get(address)
        if not edges:
            return []
        out: list[dict[str, Any]] = []
        for raw in edges:
            item = dict(raw)
            dc = item.get("destination_coords")
            if isinstance(dc, list | tuple) and len(dc) >= 2:
                item["destination_coords"] = [float(dc[0]), float(dc[1])]
            out.append(item)
        return out

    def coord_lookup(address: str) -> tuple[float, float] | None:
        pair = coords_raw.get(address)
        if pair is None or len(pair) < 2:
            return None
        return (float(pair[0]), float(pair[1]))

    if root not in coords_raw:
        raise ValueError("root_address must appear in coords_by_address")

    return build_transition_bank(
        root_address=root,
        candidate_builder=candidate_builder,
        coord_lookup=coord_lookup,
        max_depth=max_depth,
        max_nodes=max_nodes,
    )


def load_offline_graph_export(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("offline graph export must be a JSON object")
    return cast(dict[str, Any], data)
