from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pytest

from conicshield.adapters.inter_sim_rl.policy import InterSimKerasDQNPolicy
from conicshield.adapters.inter_sim_rl.shield import InterSimConicShield
from conicshield.bench.episode_runner import InterSimEpisodeRunner
from conicshield.bench.passthrough_projector import PassthroughProjector
from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions
from conicshield.core.solver_factory import Backend
from conicshield.specs.compiler import SolverOptions
from conicshield.specs.schema import SafetySpec


@dataclass
class _Obs:
    current_address: str
    current_location: tuple[float, float]
    previous_instruction: str | None

    def get_state_vector(self) -> list[float]:
        return [0.0] * 24


class _FakeEnvThreeTuple:
    action_space = ["turn_left", "turn_right", "go_straight", "turn_back"]
    max_intersections = 1
    rule_choice = "right"

    def __init__(self) -> None:
        self._done = False

    def get_observation(self) -> _Obs:
        return _Obs("Root", (0.0, 0.0), None)

    def get_shield_context(self) -> dict[str, Any]:
        return {
            "allowed_actions": list(self.action_space),
            "blocked_actions": [],
            "action_upper_bounds": dict.fromkeys(self.action_space, 1.0),
            "rule_choice": self.rule_choice,
            "previous_instruction": None,
            "hazard_score": 0.0,
            "transition_candidates": [],
        }

    def step(self, chosen_action: str) -> tuple[_Obs, float, bool]:
        self._done = True
        return self.get_observation(), 0.0, True


class _FakeModel:
    q = np.array([0.0, 1.0, 0.0, 0.0], dtype=float)

    class _Inner:
        @staticmethod
        def predict(x: object, verbose: int = 0) -> np.ndarray:
            return np.array([_FakeModel.q], dtype=float)

    model = _Inner()


def test_episode_runner_accepts_three_tuple_step_and_default_info() -> None:
    runner = InterSimEpisodeRunner(
        env_factory=_FakeEnvThreeTuple,
        policy=InterSimKerasDQNPolicy(dqn_model=_FakeModel()),
        shield=None,
        epsilon=0.0,
        seed=0,
        arm_label="baseline-unshielded",
        backend="none",
        bank_id="t",
        policy_id="p",
        policy_checkpoint=None,
    )
    ep = runner.run_episode("e3")
    assert len(ep.steps) == 1
    assert ep.steps[0].matched_action is False
    assert ep.steps[0].fallback_used is False


def _passthrough_factory(
    _spec: SafetySpec,
    _backend: Backend,
    _solver_options: SolverOptions | None,
    _native_options: NativeMoreauCompiledOptions | None,
) -> PassthroughProjector:
    return PassthroughProjector()


def test_episode_runner_epsilon_one_records_raw_q_with_shield() -> None:
    class _FakeEnvFourTuple:
        action_space = ["turn_left", "turn_right", "go_straight", "turn_back"]
        max_intersections = 1
        rule_choice = "right"

        def get_observation(self) -> _Obs:
            return _Obs("Root", (0.0, 0.0), None)

        def get_shield_context(self) -> dict[str, Any]:
            return {
                "allowed_actions": list(self.action_space),
                "blocked_actions": [],
                "action_upper_bounds": dict.fromkeys(self.action_space, 1.0),
                "rule_choice": self.rule_choice,
                "previous_instruction": None,
                "hazard_score": 0.0,
                "transition_candidates": [],
            }

        def step(self, _chosen_action: str) -> tuple[_Obs, float, bool, dict[str, Any]]:
            return self.get_observation(), 0.0, True, {"matched_action": True, "fallback_used": False}

    shield = InterSimConicShield(
        backend=Backend.CVXPY_MOREAU,
        use_geometry_prior=False,
        projector_factory=_passthrough_factory,
    )
    runner = InterSimEpisodeRunner(
        env_factory=_FakeEnvFourTuple,
        policy=InterSimKerasDQNPolicy(dqn_model=_FakeModel()),
        shield=shield,
        epsilon=1.0,
        seed=42,
        arm_label="shielded-rules-plus-geometry",
        backend="cvxpy_moreau",
        bank_id="t",
        policy_id="p",
        policy_checkpoint=None,
    )
    ep = runner.run_episode("eps")
    assert len(ep.steps) == 1
    assert ep.steps[0].raw_q_values is not None
    assert len(ep.steps[0].raw_q_values) == 4
    assert ep.steps[0].chosen_action in _FakeEnvFourTuple.action_space
    assert ep.steps[0].proposed_distribution is None
    assert ep.steps[0].matched_action is True
    assert ep.steps[0].fallback_used is False


def test_episode_runner_propagates_fallback_used_from_info() -> None:
    class _FakeEnvFallbackInfo:
        action_space = ["turn_left", "turn_right", "go_straight", "turn_back"]
        max_intersections = 1
        rule_choice = "right"

        def get_observation(self) -> _Obs:
            return _Obs("Root", (0.0, 0.0), None)

        def get_shield_context(self) -> dict[str, Any]:
            return {
                "allowed_actions": list(self.action_space),
                "blocked_actions": [],
                "action_upper_bounds": dict.fromkeys(self.action_space, 1.0),
                "rule_choice": self.rule_choice,
                "previous_instruction": None,
                "hazard_score": 0.0,
                "transition_candidates": [],
            }

        def step(self, _chosen_action: str) -> tuple[_Obs, float, bool, dict[str, Any]]:
            return self.get_observation(), 0.0, True, {"matched_action": False, "fallback_used": True}

    runner = InterSimEpisodeRunner(
        env_factory=_FakeEnvFallbackInfo,
        policy=InterSimKerasDQNPolicy(dqn_model=_FakeModel()),
        shield=None,
        epsilon=0.0,
        seed=0,
        arm_label="baseline-unshielded",
        backend="none",
        bank_id="t",
        policy_id="p",
        policy_checkpoint=None,
    )
    ep = runner.run_episode("fb")
    assert len(ep.steps) == 1
    assert ep.steps[0].matched_action is False
    assert ep.steps[0].fallback_used is True


class _FakeEnvBadStep:
    action_space = ["turn_left", "turn_right", "go_straight", "turn_back"]
    max_intersections = 1
    rule_choice = "right"

    def get_observation(self) -> _Obs:
        return _Obs("Root", (0.0, 0.0), None)

    def get_shield_context(self) -> dict[str, Any]:
        return {
            "allowed_actions": list(self.action_space),
            "blocked_actions": [],
            "action_upper_bounds": dict.fromkeys(self.action_space, 1.0),
            "rule_choice": self.rule_choice,
            "previous_instruction": None,
            "hazard_score": 0.0,
            "transition_candidates": [],
        }

    def step(self, _chosen_action: str) -> tuple[_Obs, float]:
        return self.get_observation(), 0.0


def test_episode_runner_rejects_non_three_or_four_tuple_step() -> None:
    runner = InterSimEpisodeRunner(
        env_factory=_FakeEnvBadStep,
        policy=InterSimKerasDQNPolicy(dqn_model=_FakeModel()),
        shield=None,
        epsilon=0.0,
        seed=0,
        arm_label="baseline-unshielded",
        backend="none",
        bank_id="t",
        policy_id="p",
        policy_checkpoint=None,
    )
    with pytest.raises(ValueError, match="Unsupported env.step"):
        runner.run_episode("bad")
