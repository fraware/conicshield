from conicshield.bench.replay_graph_env import ReplayGraphEnvironment
from conicshield.bench.transition_bank import CandidateEdge, TransitionBank, TransitionNode


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
