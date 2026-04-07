from __future__ import annotations

import json
from pathlib import Path

import pytest

from conicshield.bench.offline_graph_export import (
    load_offline_graph_export,
    transition_bank_from_offline_graph_export,
    validate_offline_graph_export,
)


def test_minimal_export_builds_bank_matching_demo_topology() -> None:
    path = Path(__file__).resolve().parent / "fixtures" / "offline_graph_export_minimal.json"
    payload = load_offline_graph_export(path)
    validate_offline_graph_export(payload)
    bank = transition_bank_from_offline_graph_export(payload)
    assert bank.root_address == "Root"
    assert set(bank.nodes) == {"Root", "A"}
    root = bank.nodes["Root"]
    assert len(root.candidates) == 1
    assert root.candidates[0].destination_address == "A"
    assert root.candidates[0].action_class == "turn_right"


def test_load_offline_graph_export_rejects_non_object(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    with pytest.raises(TypeError, match="JSON object"):
        load_offline_graph_export(p)


def test_bank_builds_when_child_address_omitted_from_coords(tmp_path: Path) -> None:
    """coords_by_address may omit destinations; coord_lookup returns None and BFS still closes."""
    payload = {
        "schema_version": "offline_transition_graph_export/v1",
        "root_address": "Root",
        "coords_by_address": {"Root": [0.0, 0.0]},
        "transition_graph": {
            "Root": [
                {
                    "destination_address": "A",
                    "destination_coords": [1.0, 0.0],
                    "first_instruction": "Turn right",
                    "action_class": "turn_right",
                }
            ],
            "A": [],
        },
        "max_depth": 2,
        "max_nodes": 8,
    }
    validate_offline_graph_export(payload)
    bank = transition_bank_from_offline_graph_export(payload)
    assert "A" in bank.nodes


def test_export_rejects_missing_root_coords() -> None:
    payload = load_offline_graph_export(
        Path(__file__).resolve().parent / "fixtures" / "offline_graph_export_minimal.json"
    )
    payload = dict(payload)
    payload["coords_by_address"] = {"A": [1.0, 0.0]}
    validate_offline_graph_export(payload)
    with pytest.raises(ValueError, match="root_address"):
        transition_bank_from_offline_graph_export(payload)
