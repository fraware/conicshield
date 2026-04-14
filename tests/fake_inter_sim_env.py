from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CANONICAL_ACTIONS = ("turn_left", "turn_right", "go_straight", "turn_back")


@dataclass
class FakeObservation:
    """Observation with a fixed-length vector matching bench policy expectations."""

    def get_state_vector(self) -> list[float]:
        return [0.0] * 24


class FakeInterSimEnv:
    """Minimal protocol-compatible env for default CI (no external inter-sim-rl)."""

    max_intersections = 5
    action_space = list(CANONICAL_ACTIONS)
    rule_choice = "right"

    def __init__(self) -> None:
        self._step_idx = 0
        self.current_address = "fake_root"

    def get_observation(self) -> FakeObservation:
        return FakeObservation()

    def get_shield_context(self) -> dict[str, Any]:
        prev = None if self._step_idx == 0 else "turn right"
        return {
            "allowed_actions": list(CANONICAL_ACTIONS),
            "blocked_actions": [],
            "action_upper_bounds": dict.fromkeys(CANONICAL_ACTIONS, 1.0),
            "rule_choice": self.rule_choice,
            "previous_instruction": prev,
            "hazard_score": min(1.0, 0.05 * self._step_idx),
            "current_heading_deg": 0.0,
            "branch_bearings_deg": [90.0, 0.0, -90.0, 180.0],
            "current_location": [0.0, 0.0],
            "current_direction": [1.0, 0.0],
            "current_address": self.current_address,
            "transition_candidates": [],
        }

    def step(self, chosen_action: str) -> tuple[FakeObservation, float, bool, dict[str, Any]]:
        _ = chosen_action
        self._step_idx += 1
        done = self._step_idx >= self.max_intersections
        info = {"matched_action": True, "fallback_used": False}
        return self.get_observation(), 0.0, done, info
