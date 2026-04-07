from __future__ import annotations

import numpy as np
import pytest

from conicshield.adapters.inter_sim_rl.policy import InterSimKerasDQNPolicy


def test_policy_scores_four_actions() -> None:
    class _Inner:
        @staticmethod
        def predict(x: object, verbose: int = 0) -> np.ndarray:
            return np.array([[0.0, 1.0, 2.0, 3.0]], dtype=float)

    class _Wrap:
        model = _Inner()

    pol = InterSimKerasDQNPolicy(dqn_model=_Wrap())
    out = pol.score_actions(np.zeros(24, dtype=float))
    assert out.shape == (4,)
    assert out[3] == pytest.approx(3.0)


def test_policy_rejects_non_vector_state() -> None:
    class _Inner:
        @staticmethod
        def predict(x: object, verbose: int = 0) -> np.ndarray:
            return np.array([[0.0, 0.0, 0.0, 0.0]], dtype=float)

    class _Wrap:
        model = _Inner()

    pol = InterSimKerasDQNPolicy(dqn_model=_Wrap())
    with pytest.raises(ValueError, match="1D"):
        pol.score_actions(np.zeros((2, 3), dtype=float))


def test_policy_requires_model_predict() -> None:
    class _Bad:
        model = object()

    pol = InterSimKerasDQNPolicy(dqn_model=_Bad())
    with pytest.raises(TypeError, match="predict"):
        pol.score_actions(np.zeros(4, dtype=float))
