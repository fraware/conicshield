from conicshield.bench.replay_graph_env import ReplayGraphEnvironment
from conicshield.bench.transition_bank import CandidateEdge, TransitionBank, TransitionNode


def test_replay_tiebreak_prefers_lower_duration_then_distance_then_lexical_destination() -> None:
    """Handoff Phase 3.2: deterministic branch selection for duplicate action_class."""
    bank = TransitionBank(
        root_address="Root",
        nodes={
            "Root": TransitionNode(
                address="Root",
                coords=(0.0, 0.0),
                depth=0,
                candidates=[
                    CandidateEdge(
                        destination_address="Zebra",
                        destination_coords=(2.0, 0.0),
                        first_instruction="A",
                        action_class="turn_right",
                        duration_sec=20.0,
                        distance_m=50.0,
                    ),
                    CandidateEdge(
                        destination_address="Apple",
                        destination_coords=(1.0, 0.0),
                        first_instruction="B",
                        action_class="turn_right",
                        duration_sec=10.0,
                        distance_m=200.0,
                    ),
                    CandidateEdge(
                        destination_address="Mango",
                        destination_coords=(1.5, 0.0),
                        first_instruction="C",
                        action_class="turn_right",
                        duration_sec=10.0,
                        distance_m=100.0,
                    ),
                ],
            ),
            "Apple": TransitionNode(address="Apple", coords=(1.0, 0.0), depth=1, candidates=[]),
            "Mango": TransitionNode(address="Mango", coords=(1.5, 0.0), depth=1, candidates=[]),
            "Zebra": TransitionNode(address="Zebra", coords=(2.0, 0.0), depth=1, candidates=[]),
        },
    )
    env = ReplayGraphEnvironment(bank=bank, rule_choice="right", max_intersections=2)
    _s, _r, _d, info = env.step("turn_right")
    assert info["matched_action"] is True
    assert info["selected_destination_address"] == "Mango"


def test_replay_fallback_when_action_not_in_candidates() -> None:
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
                        duration_sec=1.0,
                        distance_m=1.0,
                    )
                ],
            ),
            "A": TransitionNode(address="A", coords=(1.0, 0.0), depth=1, candidates=[]),
        },
    )
    env = ReplayGraphEnvironment(bank=bank, rule_choice="right", max_intersections=2)
    _s, _r, _d, info = env.step("turn_left")
    assert info["fallback_used"] is True
    assert info["matched_action"] is False
    assert info["selected_destination_address"] == "A"


def test_replay_no_candidates_matched_action_false() -> None:
    bank = TransitionBank(
        root_address="Root",
        nodes={
            "Root": TransitionNode(address="Root", coords=(0.0, 0.0), depth=0, candidates=[]),
        },
    )
    env = ReplayGraphEnvironment(bank=bank, rule_choice="right", max_intersections=2)
    _s, _r, done, info = env.step("turn_right")
    assert done is True
    assert info["matched_action"] is False
    assert info["fallback_used"] is True
    assert info.get("candidate_count") == 0


def test_replay_graph_env_step_matches_candidate() -> None:
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
    _state, reward, done, info = env.step("turn_right")
    assert reward == 0.0
    assert done is True
    assert info["matched_action"] is True
