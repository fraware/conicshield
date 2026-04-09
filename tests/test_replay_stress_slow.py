"""§7.1 slow tier: large synthetic bank replay determinism and transition_bank_file schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from conicshield.bench.replay_graph_env import ReplayGraphEnvironment
from conicshield.bench.transition_bank import CandidateEdge, TransitionBank, TransitionNode
from tests._repo import repo_root

REPO = repo_root()


def _linear_bank(*, n_nodes: int) -> TransitionBank:
    nodes: dict[str, TransitionNode] = {}
    for i in range(n_nodes):
        addr = f"S{i}"
        if i == n_nodes - 1:
            nodes[addr] = TransitionNode(address=addr, coords=(float(i), 0.0), depth=i, candidates=[])
        else:
            nxt = f"S{i + 1}"
            nodes[addr] = TransitionNode(
                address=addr,
                coords=(float(i), 0.0),
                depth=i,
                candidates=[
                    CandidateEdge(
                        destination_address=nxt,
                        destination_coords=(float(i + 1), 0.0),
                        first_instruction="go",
                        action_class="go_straight",
                        duration_sec=1.0,
                        distance_m=1.0,
                    )
                ],
            )
    return TransitionBank(root_address="S0", nodes=nodes)


def _destination_trace(bank: TransitionBank, *, action: str, cap: int) -> list[str | None]:
    env = ReplayGraphEnvironment(bank=bank, rule_choice="right", max_intersections=cap)
    out: list[str | None] = []
    for _ in range(cap + 2):
        _st, _r, done, info = env.step(action)
        out.append(info.get("selected_destination_address"))
        if done:
            break
    return out


@pytest.mark.slow
def test_large_linear_bank_json_roundtrip_replay_and_schema(tmp_path: Path) -> None:
    bank0 = _linear_bank(n_nodes=120)
    path = tmp_path / "stress_bank.json"
    bank0.to_json(path)
    bank1 = TransitionBank.from_json(path)

    schema = json.loads((REPO / "schemas" / "transition_bank_file.schema.json").read_text(encoding="utf-8"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)

    action = "go_straight"
    cap = 130
    assert _destination_trace(bank0, action=action, cap=cap) == _destination_trace(bank1, action=action, cap=cap)
