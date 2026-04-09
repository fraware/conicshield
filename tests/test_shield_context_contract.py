from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from conicshield.adapters.inter_sim_rl.context_model import ShieldContextModel
from conicshield.adapters.inter_sim_rl.context_validate import validate_shield_context_dict
from conicshield.bench.replay_graph_env import ReplayGraphEnvironment
from conicshield.bench.transition_bank import CandidateEdge, TransitionBank, TransitionNode
from tests._repo import repo_root


def _minimal_valid_context() -> dict:
    return {
        "allowed_actions": ["turn_right"],
        "blocked_actions": ["turn_left", "go_straight", "turn_back"],
        "action_upper_bounds": {
            "turn_left": 0.0,
            "turn_right": 1.0,
            "go_straight": 0.0,
            "turn_back": 0.0,
        },
        "rule_choice": "right",
        "previous_instruction": "turn right",
        "hazard_score": 0.2,
    }


def test_shield_context_json_schema_accepts_minimal() -> None:
    validate_shield_context_dict(_minimal_valid_context())


def test_shield_context_json_schema_rejects_missing_field() -> None:
    ctx = _minimal_valid_context()
    del ctx["hazard_score"]
    with pytest.raises(ValidationError):
        validate_shield_context_dict(ctx)


def test_shield_context_pydantic_roundtrip() -> None:
    m = ShieldContextModel.from_mapping(_minimal_valid_context())
    assert m.allowed_actions == ["turn_right"]
    assert m.hazard_score == 0.2


def test_replay_env_context_validates_against_schema() -> None:
    bank = TransitionBank(
        root_address="Root",
        nodes={
            "Root": TransitionNode(
                address="Root",
                coords=(0.0, 0.0),
                depth=0,
                candidates=[
                    CandidateEdge(
                        destination_address="A",
                        destination_coords=(1.0, 0.0),
                        first_instruction="Turn right",
                        action_class="turn_right",
                        duration_sec=10.0,
                        distance_m=100.0,
                    )
                ],
            ),
            "A": TransitionNode(address="A", coords=(1.0, 0.0), depth=1, candidates=[]),
        },
    )
    env = ReplayGraphEnvironment(bank=bank, rule_choice="right", max_intersections=1)
    ctx = env.get_shield_context()
    validate_shield_context_dict(ctx)


def test_shield_context_schema_file_is_valid_json() -> None:
    path = repo_root() / "schemas" / "shield_context.schema.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["title"]


def test_shield_context_model_non_dict_bounds_becomes_empty() -> None:
    ctx = _minimal_valid_context()
    ctx["action_upper_bounds"] = "not-a-dict"
    m = ShieldContextModel.from_mapping(ctx)
    assert m.action_upper_bounds == {}


def test_shield_context_model_skips_non_dict_transition_candidates() -> None:
    ctx = _minimal_valid_context()
    ctx["transition_candidates"] = [
        "bad",
        {
            "destination_address": "X",
            "destination_coords": [1.0, 2.0],
            "first_instruction": "go",
            "action_class": "go_straight",
        },
    ]
    m = ShieldContextModel.from_mapping(ctx)
    assert m.transition_candidates is not None
    assert len(m.transition_candidates) == 1
    assert m.transition_candidates[0].destination_address == "X"


def test_fixture_shield_metadata_passes_schema_and_pydantic() -> None:
    line = Path("tests/fixtures/parity_reference/episodes.jsonl").read_text(encoding="utf-8").splitlines()[2]
    ep = json.loads(line)
    snap = ep["steps"][0]["metadata"]["shield_context_snapshot"]
    validate_shield_context_dict(snap)
    m = ShieldContextModel.from_mapping(snap)
    assert m.allowed_actions
    assert m.hazard_score >= 0.0
