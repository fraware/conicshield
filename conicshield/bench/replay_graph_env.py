from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from conicshield.bench.transition_bank import CandidateEdge, TransitionBank

ACTION_SPACE = ["turn_left", "turn_right", "go_straight", "turn_back"]


@dataclass(slots=True)
class ReplayState:
    current_location: tuple[float, float]
    current_direction: tuple[float, float]
    nearby_streets: list[dict[str, Any]]
    current_address: str
    previous_instruction: str | None

    def get_state_vector(self) -> list[float]:
        base = [
            float(self.current_location[0]),
            float(self.current_location[1]),
            float(self.current_direction[0]),
            float(self.current_direction[1]),
        ]
        return base + [0.0] * 20


def _direction_vector(
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> tuple[float, float]:
    dx = float(destination[0] - origin[0])
    dy = float(destination[1] - origin[1])
    norm = math.hypot(dx, dy)
    if norm <= 1e-12:
        return (0.0, 0.0)
    return (dx / norm, dy / norm)


def _canonical_candidate_sort_key(c: CandidateEdge):
    dur = c.duration_sec if c.duration_sec is not None else float("inf")
    dist = c.distance_m if c.distance_m is not None else float("inf")
    return (dur, dist, c.destination_address)


class ReplayGraphEnvironment:
    def __init__(
        self,
        *,
        bank: TransitionBank,
        rule_choice: str,
        max_intersections: int = 20,
    ) -> None:
        self.bank = bank
        self.rule_choice = rule_choice
        self.max_intersections = max_intersections
        self.intersection_count = 0
        self.action_space = ACTION_SPACE.copy()

        self.current_address = bank.root_address
        self.current_node = bank.nodes[self.current_address]

        self.current_state = ReplayState(
            current_location=self.current_node.coords,
            current_direction=(0.0, 0.0),
            nearby_streets=[
                c.place for c in self.current_node.candidates if c.place is not None
            ],
            current_address=self.current_node.address,
            previous_instruction=None,
        )

    def get_observation(self) -> ReplayState:
        return self.current_state

    def get_shield_context(self) -> dict[str, Any]:
        return {
            "current_location": list(self.current_state.current_location),
            "current_direction": list(self.current_state.current_direction),
            "current_address": self.current_state.current_address,
            "previous_instruction": self.current_state.previous_instruction,
            "rule_choice": self.rule_choice,
            "transition_candidates": [
                {
                    "destination_address": c.destination_address,
                    "destination_coords": list(c.destination_coords),
                    "first_instruction": c.first_instruction,
                    "action_class": c.action_class,
                    "duration_sec": c.duration_sec,
                    "distance_m": c.distance_m,
                }
                for c in self.current_node.candidates
            ],
            "allowed_actions": self._allowed_actions_from_candidates(),
        }

    def _allowed_actions_from_candidates(self) -> list[str]:
        supported = sorted({c.action_class for c in self.current_node.candidates})
        return supported if supported else ACTION_SPACE.copy()

    def step(self, chosen_action: str):
        reward = self.calculate_reward(
            self.current_state.previous_instruction,
            chosen_action,
        )

        matching = [c for c in self.current_node.candidates if c.action_class == chosen_action]
        fallback_used = False

        if matching:
            selected = sorted(matching, key=_canonical_candidate_sort_key)[0]
        elif self.current_node.candidates:
            selected = sorted(self.current_node.candidates, key=_canonical_candidate_sort_key)[0]
            fallback_used = True
        else:
            selected = None
            fallback_used = True

        if selected is None:
            done = True
            info = {
                "fallback_used": True,
                "matched_action": False,
                "candidate_count": 0,
            }
            return self.current_state, reward, done, info

        next_address = selected.destination_address
        next_node = self.bank.nodes.get(next_address)

        if next_node is None:
            done = True
            info = {
                "fallback_used": fallback_used,
                "matched_action": bool(matching),
                "candidate_count": len(self.current_node.candidates),
                "out_of_bank": True,
            }
            return self.current_state, reward, done, info

        self.intersection_count += 1
        done = self.intersection_count >= self.max_intersections

        direction = _direction_vector(self.current_node.coords, next_node.coords)

        self.current_address = next_address
        self.current_node = next_node
        self.current_state = ReplayState(
            current_location=next_node.coords,
            current_direction=direction,
            nearby_streets=[c.place for c in next_node.candidates if c.place is not None],
            current_address=next_node.address,
            previous_instruction=chosen_action,
        )

        info = {
            "fallback_used": fallback_used,
            "matched_action": bool(matching),
            "candidate_count": len(self.current_node.candidates),
            "selected_action_class": selected.action_class,
            "selected_destination_address": selected.destination_address,
            "selected_duration_sec": selected.duration_sec,
            "selected_distance_m": selected.distance_m,
        }
        return self.current_state, reward, done, info

    def calculate_reward(self, previous_instruction, chosen_action: str) -> float:
        if previous_instruction is None:
            return 0.0

        prev = previous_instruction.lower()

        if self.rule_choice == "right":
            if "right" in prev and chosen_action == "turn_right":
                return 1.0
            if "right" in prev:
                return -0.5
            return 0.0

        if self.rule_choice == "left":
            if "left" in prev and chosen_action == "turn_left":
                return 1.0
            if "left" in prev:
                return -0.5
            return 0.0

        if self.rule_choice == "alternate":
            if "left" in prev and chosen_action == "turn_right":
                return 1.0
            if "right" in prev and chosen_action == "turn_left":
                return 1.0
            if "left" in prev or "right" in prev:
                return -0.5
            return 0.0

        return 0.0
