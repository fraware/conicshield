from __future__ import annotations

import numpy as np

from conicshield.adapters.inter_sim_rl.policy import InterSimKerasDQNPolicy
from conicshield.adapters.inter_sim_rl.shield import InterSimConicShield
from conicshield.bench.episode_runner import InterSimEpisodeRunner
from conicshield.bench.passthrough_projector import PassthroughProjector
from conicshield.core.solver_factory import Backend
from tests.fake_inter_sim_env import FakeInterSimEnv


def _policy() -> InterSimKerasDQNPolicy:
    class _M:
        q = np.array([0.1, 2.0, 0.2, -0.5], dtype=float)

        class _Inner:
            @staticmethod
            def predict(x: object, verbose: int = 0) -> np.ndarray:
                return np.array([_M.q], dtype=float)

        model = _Inner()

    return InterSimKerasDQNPolicy(dqn_model=_M())


def test_fake_env_episode_with_shield_no_nan() -> None:
    shield = InterSimConicShield(
        backend=Backend.CVXPY_MOREAU,
        use_geometry_prior=True,
        projector_factory=lambda *a, **k: PassthroughProjector(),
    )
    runner = InterSimEpisodeRunner(
        env_factory=FakeInterSimEnv,
        policy=_policy(),
        shield=shield,
        epsilon=0.0,
        seed=3,
        arm_label="shielded-rules-plus-geometry",
        backend="cvxpy_moreau",
        bank_id="fake_bank",
        policy_id="fake_policy",
        policy_checkpoint=None,
    )
    ep = runner.run_episode("fake-001")
    assert ep.num_steps >= 1
    for s in ep.steps:
        q = np.asarray(s.raw_q_values, dtype=float)
        assert np.all(np.isfinite(q))
        assert s.chosen_action in FakeInterSimEnv.action_space
