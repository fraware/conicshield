from __future__ import annotations

from conicshield.bench.replay_graph_env import ReplayGraphEnvironment
from conicshield.bench.transition_bank import CandidateEdge, TransitionBank, TransitionNode


def _bank_with_dead_end() -> TransitionBank:
    return TransitionBank(
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
                        duration_sec=1.0,
                        distance_m=10.0,
                    ),
                ],
            ),
            "A": TransitionNode(address="A", coords=(1.0, 0.0), depth=1, candidates=[]),
        },
    )


def _bank_oob() -> TransitionBank:
    return TransitionBank(
        root_address="Root",
        nodes={
            "Root": TransitionNode(
                address="Root",
                coords=(0.0, 0.0),
                depth=0,
                candidates=[
                    CandidateEdge(
                        destination_address="Missing",
                        destination_coords=(9.0, 9.0),
                        first_instruction="Turn right",
                        action_class="turn_right",
                        duration_sec=1.0,
                        distance_m=10.0,
                    ),
                ],
            ),
        },
    )


def test_info_normal_step_has_branch_metadata() -> None:
    env = ReplayGraphEnvironment(bank=_bank_with_dead_end(), rule_choice="right", max_intersections=5)
    _st, _r, done, info = env.step("turn_right")
    assert info["matched_action"] is True
    assert info["fallback_used"] is False
    assert info["candidate_count"] == 0
    assert info["selected_destination_address"] == "A"
    assert info["selected_action_class"] == "turn_right"
    assert "selected_duration_sec" in info
    assert "selected_distance_m" in info
    assert done is False


def test_info_out_of_bank() -> None:
    env = ReplayGraphEnvironment(bank=_bank_oob(), rule_choice="right", max_intersections=5)
    _st, _r, done, info = env.step("turn_right")
    assert info.get("out_of_bank") is True
    assert info["matched_action"] is True
    assert info["candidate_count"] == 1


def test_info_no_candidates_node() -> None:
    bank = TransitionBank(
        root_address="X",
        nodes={"X": TransitionNode(address="X", coords=(0.0, 0.0), depth=0, candidates=[])},
    )
    env = ReplayGraphEnvironment(bank=bank, rule_choice="right", max_intersections=5)
    _st, _r, done, info = env.step("turn_right")
    assert info["candidate_count"] == 0
    assert info["matched_action"] is False
    assert done is True


def test_info_on_max_intersections_termination() -> None:
    bank = TransitionBank(
        root_address="N0",
        nodes={
            "N0": TransitionNode(
                address="N0",
                coords=(0.0, 0.0),
                depth=0,
                candidates=[
                    CandidateEdge(
                        destination_address="N1",
                        destination_coords=(1.0, 0.0),
                        first_instruction="x",
                        action_class="go_straight",
                        duration_sec=1.0,
                        distance_m=1.0,
                    ),
                ],
            ),
            "N1": TransitionNode(
                address="N1",
                coords=(1.0, 0.0),
                depth=1,
                candidates=[
                    CandidateEdge(
                        destination_address="N2",
                        destination_coords=(2.0, 0.0),
                        first_instruction="y",
                        action_class="go_straight",
                        duration_sec=1.0,
                        distance_m=1.0,
                    ),
                ],
            ),
            "N2": TransitionNode(address="N2", coords=(2.0, 0.0), depth=2, candidates=[]),
        },
    )
    env = ReplayGraphEnvironment(bank=bank, rule_choice="right", max_intersections=1)
    _st, _r, done, info = env.step("go_straight")
    assert done is True
    assert info["matched_action"] is True
    assert info["candidate_count"] == 1


def test_info_fallback_picks_canonical_branch() -> None:
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
                        first_instruction="x",
                        action_class="turn_right",
                        duration_sec=2.0,
                        distance_m=20.0,
                    ),
                    CandidateEdge(
                        destination_address="B",
                        destination_coords=(0.0, 1.0),
                        first_instruction="y",
                        action_class="turn_right",
                        duration_sec=1.0,
                        distance_m=10.0,
                    ),
                ],
            ),
            "A": TransitionNode(address="A", coords=(1.0, 0.0), depth=1, candidates=[]),
            "B": TransitionNode(address="B", coords=(0.0, 1.0), depth=1, candidates=[]),
        },
    )
    env = ReplayGraphEnvironment(bank=bank, rule_choice="right", max_intersections=5)
    _st, _r, _d, info = env.step("turn_right")
    assert info["matched_action"] is True
    assert info["selected_destination_address"] == "B"
