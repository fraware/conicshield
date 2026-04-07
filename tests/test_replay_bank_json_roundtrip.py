"""§7.1 replay: TransitionBank JSON round-trip preserves deterministic step traces."""

from __future__ import annotations

from pathlib import Path

from conicshield.bench.replay_graph_env import ReplayGraphEnvironment
from conicshield.bench.transition_bank import CandidateEdge, TransitionBank, TransitionNode


def _fixture_like_bank() -> TransitionBank:
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
                        duration_sec=10.0,
                        distance_m=100.0,
                    )
                ],
            ),
            "A": TransitionNode(address="A", coords=(1.0, 0.0), depth=1, candidates=[]),
        },
    )


def _trace(env: ReplayGraphEnvironment, action: str, max_steps: int) -> list[tuple[str, str | None, bool]]:
    out: list[tuple[str, str | None, bool]] = []
    for _ in range(max_steps):
        _st, _r, done, info = env.step(action)
        out.append((action, info.get("selected_destination_address"), bool(done)))
        if done:
            break
    return out


def test_transition_bank_json_roundtrip_replay_identical(tmp_path: Path) -> None:
    bank0 = _fixture_like_bank()
    path = tmp_path / "bank.json"
    bank0.to_json(path)
    bank1 = TransitionBank.from_json(path)

    cap = 5
    action = "turn_right"
    t0 = _trace(ReplayGraphEnvironment(bank=bank0, rule_choice="right", max_intersections=cap), action, cap + 2)
    t1 = _trace(ReplayGraphEnvironment(bank=bank1, rule_choice="right", max_intersections=cap), action, cap + 2)
    assert t0 == t1
