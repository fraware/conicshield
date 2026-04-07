from __future__ import annotations

from conicshield.bench.replay_graph_env import ReplayGraphEnvironment
from conicshield.bench.transition_bank import CandidateEdge, TransitionBank, TransitionNode


def _make_bank() -> TransitionBank:
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
                        duration_sec=5.0,
                        distance_m=50.0,
                    ),
                    CandidateEdge(
                        destination_address="B",
                        destination_coords=(0.0, 1.0),
                        first_instruction="Turn left",
                        action_class="turn_left",
                        duration_sec=5.0,
                        distance_m=50.0,
                    ),
                ],
            ),
            "A": TransitionNode(address="A", coords=(1.0, 0.0), depth=1, candidates=[]),
            "B": TransitionNode(address="B", coords=(0.0, 1.0), depth=1, candidates=[]),
        },
    )


def test_replay_same_seed_actions_deterministic() -> None:
    bank = _make_bank()
    actions = ["turn_right", "turn_right"]

    def trace() -> list[tuple[str, bool, bool]]:
        env = ReplayGraphEnvironment(bank=bank, rule_choice="right", max_intersections=5)
        out: list[tuple[str, bool, bool]] = []
        for a in actions:
            _st, _r, done, info = env.step(a)
            out.append((env.current_state.current_address, bool(info["matched_action"]), bool(info["fallback_used"])))
            if done:
                break
        return out

    assert trace() == trace()


def test_replay_edges_reference_bank_nodes() -> None:
    bank = _make_bank()
    env = ReplayGraphEnvironment(bank=bank, rule_choice="right", max_intersections=5)
    _st, _r, done, info = env.step("turn_right")
    assert not done or env.current_state.current_address in bank.nodes
    dest = info.get("selected_destination_address")
    if dest is not None:
        assert dest in bank.nodes
