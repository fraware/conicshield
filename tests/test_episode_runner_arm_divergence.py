from __future__ import annotations

from typing import Any

import numpy as np

from conicshield.adapters.inter_sim_rl.policy import InterSimKerasDQNPolicy
from conicshield.adapters.inter_sim_rl.shield import InterSimConicShield
from conicshield.bench.episode_runner import InterSimEpisodeRunner
from conicshield.bench.replay_graph_env import ReplayGraphEnvironment
from conicshield.bench.transition_bank import CandidateEdge, TransitionBank, TransitionNode
from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions
from conicshield.core.result import ProjectionResult
from conicshield.core.solver_factory import Backend
from conicshield.specs.compiler import SolverOptions
from conicshield.specs.schema import SafetySpec


def _divergence_bank() -> TransitionBank:
    return TransitionBank(
        root_address="Root",
        nodes={
            "Root": TransitionNode(
                address="Root",
                coords=(0.0, 0.0),
                depth=0,
                candidates=[
                    CandidateEdge(
                        destination_address="R",
                        destination_coords=(1.0, 0.0),
                        first_instruction="Turn right",
                        action_class="turn_right",
                        duration_sec=1.0,
                        distance_m=10.0,
                    ),
                    CandidateEdge(
                        destination_address="L",
                        destination_coords=(0.0, 1.0),
                        first_instruction="Turn left",
                        action_class="turn_left",
                        duration_sec=2.0,
                        distance_m=20.0,
                    ),
                ],
            ),
            "R": TransitionNode(address="R", coords=(1.0, 0.0), depth=1, candidates=[]),
            "L": TransitionNode(address="L", coords=(0.0, 1.0), depth=1, candidates=[]),
        },
    )


class _FixedLeftProjector:
    def project(
        self,
        proposed_action: np.ndarray,
        previous_action: np.ndarray | None = None,
        *,
        reference_action: np.ndarray | None = None,
        policy_weight: float = 1.0,
        reference_weight: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> ProjectionResult:
        corr = np.zeros(4, dtype=float)
        corr[0] = 1.0
        prop = np.asarray(proposed_action, dtype=float)
        return ProjectionResult(
            proposed_action=prop,
            corrected_action=corr,
            intervened=True,
            intervention_norm=float(np.linalg.norm(corr - prop)),
            solver_status="optimal",
            objective_value=0.0,
            active_constraints=["test_fixed_left"],
            warm_started=True,
            solve_time_sec=0.001,
            setup_time_sec=0.0001,
            iterations=1,
            construction_time_sec=0.0,
            device="cpu",
            metadata=dict(metadata or {}),
        )


def _fixed_left_factory(
    _spec: SafetySpec,
    _backend: Backend,
    _solver_options: SolverOptions | None,
    _native_options: NativeMoreauCompiledOptions | None,
) -> _FixedLeftProjector:
    return _FixedLeftProjector()


class _QModel:
    q = np.array([0.1, 5.0, 0.1, 0.0], dtype=float)

    class _Inner:
        @staticmethod
        def predict(x: object, verbose: int = 0) -> np.ndarray:
            return np.array([_QModel.q], dtype=float)

    model = _Inner()


def test_arm_divergence_baseline_argmax_differs_from_fixed_left_shield() -> None:
    bank = _divergence_bank()

    def env_factory() -> ReplayGraphEnvironment:
        return ReplayGraphEnvironment(bank=bank, rule_choice="right", max_intersections=5)

    policy = InterSimKerasDQNPolicy(dqn_model=_QModel())

    base = InterSimEpisodeRunner(
        env_factory=env_factory,
        policy=policy,
        shield=None,
        epsilon=0.0,
        seed=0,
        arm_label="baseline-unshielded",
        backend="none",
        bank_id="div",
        policy_id="stub",
        policy_checkpoint=None,
    )
    shielded = InterSimEpisodeRunner(
        env_factory=env_factory,
        policy=policy,
        shield=InterSimConicShield(
            backend=Backend.CVXPY_MOREAU,
            use_geometry_prior=False,
            projector_factory=_fixed_left_factory,
        ),
        epsilon=0.0,
        seed=0,
        arm_label="shielded-rules-plus-geometry",
        backend="cvxpy_moreau",
        bank_id="div",
        policy_id="stub",
        policy_checkpoint=None,
    )

    eb = base.run_episode("b")
    es = shielded.run_episode("s")
    assert eb.steps[0].chosen_action == "turn_right"
    assert es.steps[0].chosen_action == "turn_left"
    assert eb.steps[0].selected_destination_address != es.steps[0].selected_destination_address
