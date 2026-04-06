from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Callable


@dataclass(slots=True)
class CandidateEdge:
    destination_address: str
    destination_coords: tuple[float, float]
    first_instruction: str
    action_class: str
    duration_sec: float | None = None
    distance_m: float | None = None
    place: dict[str, Any] | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "CandidateEdge":
        return cls(
            destination_address=str(raw["destination_address"]),
            destination_coords=(
                float(raw["destination_coords"][0]),
                float(raw["destination_coords"][1]),
            ),
            first_instruction=str(raw.get("first_instruction", "")),
            action_class=str(raw["action_class"]),
            duration_sec=(
                float(raw["duration_sec"]) if raw.get("duration_sec") is not None else None
            ),
            distance_m=(
                float(raw["distance_m"]) if raw.get("distance_m") is not None else None
            ),
            place=raw.get("place"),
        )


@dataclass(slots=True)
class TransitionNode:
    address: str
    coords: tuple[float, float]
    depth: int
    candidates: list[CandidateEdge] = field(default_factory=list)

    def allowed_actions(self) -> list[str]:
        return sorted({c.action_class for c in self.candidates})


@dataclass(slots=True)
class TransitionBank:
    root_address: str
    nodes: dict[str, TransitionNode]

    def to_json(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "root_address": self.root_address,
            "nodes": {
                addr: {
                    "address": node.address,
                    "coords": list(node.coords),
                    "depth": node.depth,
                    "candidates": [
                        {
                            "destination_address": c.destination_address,
                            "destination_coords": list(c.destination_coords),
                            "first_instruction": c.first_instruction,
                            "action_class": c.action_class,
                            "duration_sec": c.duration_sec,
                            "distance_m": c.distance_m,
                            "place": c.place,
                        }
                        for c in node.candidates
                    ],
                }
                for addr, node in self.nodes.items()
            },
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def from_json(cls, path: str | Path) -> "TransitionBank":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        nodes: dict[str, TransitionNode] = {}
        for addr, raw in payload["nodes"].items():
            nodes[addr] = TransitionNode(
                address=str(raw["address"]),
                coords=(float(raw["coords"][0]), float(raw["coords"][1])),
                depth=int(raw["depth"]),
                candidates=[CandidateEdge.from_raw(c) for c in raw["candidates"]],
            )
        return cls(root_address=str(payload["root_address"]), nodes=nodes)


def build_transition_bank(
    *,
    root_address: str,
    candidate_builder: Callable[[str], list[dict[str, Any]]],
    coord_lookup: Callable[[str], tuple[float, float] | None],
    max_depth: int = 4,
    max_nodes: int = 400,
) -> TransitionBank:
    nodes: dict[str, TransitionNode] = {}
    queue = deque([(root_address, 0)])
    visited: set[str] = set()

    while queue and len(nodes) < max_nodes:
        address, depth = queue.popleft()
        if address in visited:
            continue
        visited.add(address)

        coords = coord_lookup(address) or (0.0, 0.0)
        raw_candidates = candidate_builder(address)
        candidates = [CandidateEdge.from_raw(c) for c in raw_candidates]

        node = TransitionNode(
            address=address,
            coords=(float(coords[0]), float(coords[1])),
            depth=depth,
            candidates=candidates,
        )
        nodes[address] = node

        if depth >= max_depth:
            continue

        for c in candidates:
            if c.destination_address not in visited and len(nodes) + len(queue) < max_nodes:
                queue.append((c.destination_address, depth + 1))

    return TransitionBank(root_address=root_address, nodes=nodes)
