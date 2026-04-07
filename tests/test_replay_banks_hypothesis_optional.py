from __future__ import annotations

import importlib.util

import pytest

if importlib.util.find_spec("hypothesis") is None:
    pytest.skip("hypothesis not installed", allow_module_level=True)

from hypothesis import given, settings
from hypothesis import strategies as st

from conicshield.bench.replay_graph_env import ReplayGraphEnvironment
from conicshield.bench.transition_bank import CandidateEdge, TransitionBank, TransitionNode

_ACTIONS = ("turn_left", "turn_right", "go_straight", "turn_back")


@st.composite
def tiny_linear_bank(draw: st.DrawFn) -> TransitionBank:
    n = draw(st.integers(min_value=1, max_value=8))
    action = draw(st.sampled_from(_ACTIONS))
    nodes: dict[str, TransitionNode] = {}
    for i in range(n + 1):
        addr = f"N{i}"
        if i == n:
            nodes[addr] = TransitionNode(address=addr, coords=(float(i), 0.0), depth=i, candidates=[])
        else:
            nxt = f"N{i + 1}"
            nodes[addr] = TransitionNode(
                address=addr,
                coords=(float(i), 0.0),
                depth=i,
                candidates=[
                    CandidateEdge(
                        destination_address=nxt,
                        destination_coords=(float(i + 1), 0.0),
                        first_instruction="go",
                        action_class=action,
                        duration_sec=float(i + 1),
                        distance_m=float(10 * (i + 1)),
                    )
                ],
            )
    return TransitionBank(root_address="N0", nodes=nodes)


@given(tiny_linear_bank(), st.sampled_from(("right", "left", "alternate")))
@settings(max_examples=25)
def test_replay_linear_bank_allowed_actions_subset_canonical(bank: TransitionBank, rule: str) -> None:
    env = ReplayGraphEnvironment(bank=bank, rule_choice=rule, max_intersections=20)
    ctx = env.get_shield_context()
    allowed = set(ctx["allowed_actions"])
    assert allowed.issubset(set(_ACTIONS))


def _root_action(bank: TransitionBank) -> str:
    cands = bank.nodes[bank.root_address].candidates
    assert cands
    return str(cands[0].action_class)


@given(tiny_linear_bank(), st.integers(min_value=1, max_value=8))
@settings(max_examples=25)
def test_replay_linear_bank_deterministic_trajectory(bank: TransitionBank, cap: int) -> None:
    action = _root_action(bank)
    env = ReplayGraphEnvironment(bank=bank, rule_choice="right", max_intersections=cap)
    traj: list[tuple[str, str | None]] = []
    for _ in range(cap + 2):
        _st, _r, done, info = env.step(action)
        traj.append((action, info.get("selected_destination_address")))
        if done:
            break
    env2 = ReplayGraphEnvironment(bank=bank, rule_choice="right", max_intersections=cap)
    traj2: list[tuple[str, str | None]] = []
    for _ in range(cap + 2):
        _st, _r, done, info = env2.step(action)
        traj2.append((action, info.get("selected_destination_address")))
        if done:
            break
    assert traj == traj2


def test_fan_out_same_action_class_picks_canonical_tie_break() -> None:
    """Multiple `turn_right` branches: replay uses duration, distance, then destination address (lexical)."""
    bank = TransitionBank(
        root_address="Root",
        nodes={
            "Root": TransitionNode(
                address="Root",
                coords=(0.0, 0.0),
                depth=0,
                candidates=[
                    CandidateEdge(
                        destination_address="Z_end",
                        destination_coords=(3.0, 0.0),
                        first_instruction="z",
                        action_class="turn_right",
                        duration_sec=1.0,
                        distance_m=10.0,
                    ),
                    CandidateEdge(
                        destination_address="A_end",
                        destination_coords=(1.0, 0.0),
                        first_instruction="a",
                        action_class="turn_right",
                        duration_sec=1.0,
                        distance_m=10.0,
                    ),
                    CandidateEdge(
                        destination_address="M_end",
                        destination_coords=(2.0, 0.0),
                        first_instruction="m",
                        action_class="turn_right",
                        duration_sec=1.0,
                        distance_m=10.0,
                    ),
                ],
            ),
            "A_end": TransitionNode(address="A_end", coords=(1.0, 0.0), depth=1, candidates=[]),
            "M_end": TransitionNode(address="M_end", coords=(2.0, 0.0), depth=1, candidates=[]),
            "Z_end": TransitionNode(address="Z_end", coords=(3.0, 0.0), depth=1, candidates=[]),
        },
    )
    env = ReplayGraphEnvironment(bank=bank, rule_choice="right", max_intersections=5)
    _st, _r, _d, info = env.step("turn_right")
    assert info["selected_destination_address"] == "A_end"


def test_replay_long_chain_two_instances_identical() -> None:
    nodes: dict[str, TransitionNode] = {}
    for i in range(9):
        addr = f"S{i}"
        if i == 8:
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
    bank = TransitionBank(root_address="S0", nodes=nodes)

    def walk() -> list[str | None]:
        env = ReplayGraphEnvironment(bank=bank, rule_choice="right", max_intersections=20)
        seq: list[str | None] = []
        for _ in range(25):
            _st, _r, done, info = env.step("go_straight")
            seq.append(info.get("selected_destination_address"))
            if done:
                break
        return seq

    assert walk() == walk()
