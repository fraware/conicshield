from __future__ import annotations

import json
from pathlib import Path

from conicshield.bench.inter_sim_export import (
    export_rehearsal_fork_graph,
    fork_graph_for_rehearsal,
    transition_graph_to_export_payload,
)
from conicshield.bench.offline_graph_export import load_offline_graph_export, transition_bank_from_offline_graph_export


def test_rehearsal_fork_matches_committed_upstream_export() -> None:
    root = Path(__file__).resolve().parents[2]
    committed = root / "benchmarks" / "external_evidence" / "offline_graph_export_upstream.json"
    generated = export_rehearsal_fork_graph()
    on_disk = json.loads(committed.read_text(encoding="utf-8"))
    assert generated["transition_graph"] == on_disk["transition_graph"]
    assert set(generated["coords_by_address"]) == set(on_disk["coords_by_address"])


def test_upstream_export_bank_differs_from_minimal_fixture() -> None:
    root = Path(__file__).resolve().parents[2]
    upstream = load_offline_graph_export(
        root / "benchmarks" / "external_evidence" / "offline_graph_export_upstream.json"
    )
    minimal = load_offline_graph_export(root / "tests" / "fixtures" / "offline_graph_export_minimal.json")
    bank_up = transition_bank_from_offline_graph_export(upstream)
    bank_min = transition_bank_from_offline_graph_export(minimal)
    assert len(bank_up.nodes) > len(bank_min.nodes)


def test_transition_graph_to_export_payload_validates() -> None:
    payload = transition_graph_to_export_payload(transition_graph=fork_graph_for_rehearsal())
    assert payload["schema_version"] == "offline_transition_graph_export/v1"
    assert "NodeA" in payload["coords_by_address"]
