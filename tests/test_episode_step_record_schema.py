from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from conicshield.bench.episode_runner import EpisodeRecord, StepRecord


def _episode_record_validator() -> jsonschema.Draft202012Validator:
    schema_path = Path("schemas/episodes.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    episode_record_schema: dict = {
        "$ref": "#/$defs/episodeRecord",
        "$defs": schema["$defs"],
    }
    return jsonschema.Draft202012Validator(episode_record_schema)


def test_step_record_as_dict_matches_episode_schema_for_shielded_arm() -> None:
    v = _episode_record_validator()
    step = StepRecord(
        step=0,
        current_address="Root",
        current_location=(0.0, 0.0),
        previous_instruction="turn_right",
        available_actions=["turn_right"],
        chosen_action="turn_right",
        reward=1.0,
        intervened=True,
        intervention_norm=0.0,
        objective_value=0.0,
        raw_q_values=[0.1, 3.0, 0.0, -1.0],
        proposed_distribution=[0.05, 0.9, 0.03, 0.02],
        corrected_distribution=[0.0, 1.0, 0.0, 0.0],
        active_constraints=["turn_feasibility"],
        matched_action=True,
        fallback_used=False,
        selected_action_class="turn_right",
        selected_destination_address="A",
        selected_duration_sec=10.0,
        selected_distance_m=100.0,
        solver_status="optimal",
        iterations=1,
        solve_time_sec=0.001,
        setup_time_sec=0.0001,
        construction_time_sec=0.0,
        device="cpu",
        warm_started=True,
        metadata={
            "shield_context_snapshot": {"rule_choice": "right"},
            "canonical_action_space": ["turn_left", "turn_right", "go_straight", "turn_back"],
            "spec_id": "inter-sim-rl/shield-context-v0",
            "cache_key": "k",
        },
    )
    ep = EpisodeRecord(
        episode_id="e1",
        arm_label="shielded-rules-plus-geometry",
        backend="cvxpy_moreau",
        root_address="Root",
        rule_choice="right",
        bank_id="b",
        policy_id="p",
        policy_checkpoint=None,
        seed=1,
        started_at_utc="2026-04-06T00:00:00Z",
        steps=[step],
    )
    ep.finalize()
    payload = ep.as_dict()
    v.validate(payload)


def test_fixture_shielded_episode_lines_validate_against_schema() -> None:
    v = _episode_record_validator()
    path = Path("tests/fixtures/parity_reference/episodes.jsonl")
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ep = json.loads(line)
        if ep["arm_label"] not in ("shielded-rules-only", "shielded-rules-plus-geometry", "shielded-native-moreau"):
            continue
        v.validate(ep)
        for s in ep["steps"]:
            assert s.get("raw_q_values") is not None
            assert s.get("proposed_distribution") is not None
            assert s.get("corrected_distribution") is not None
            assert s.get("metadata", {}).get("shield_context_snapshot") is not None
            assert s.get("metadata", {}).get("canonical_action_space") is not None
