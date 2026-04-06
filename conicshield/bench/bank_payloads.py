from __future__ import annotations

from typing import Any

from conicshield.bench.transition_bank import TransitionBank


def transition_bank_payload(bank: TransitionBank, *, bank_id: str) -> dict[str, Any]:
    return {
        "bank_id": bank_id,
        "root_address": bank.root_address,
        "nodes": {
            addr: {
                "address": node.address,
                "coords": list(node.coords),
                "depth": node.depth,
                "allowed_actions": node.allowed_actions(),
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
            for addr, node in bank.nodes.items()
        },
    }
