from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np


class ScorePolicyProtocol(Protocol):
    def score_actions(self, state: Any) -> np.ndarray: ...


@dataclass(slots=True)
class InterSimKerasDQNPolicy:
    """Adapter around an object exposing `.model.predict(...)`."""

    dqn_model: Any

    def score_actions(self, state: Any) -> np.ndarray:
        state_vector = state.get_state_vector() if hasattr(state, "get_state_vector") else state
        vec = np.asarray(state_vector, dtype=float)
        if vec.ndim != 1:
            raise ValueError(f"State vector must be 1D; got shape {vec.shape}")

        inner = getattr(self.dqn_model, "model", None)
        if inner is None:
            raise TypeError("dqn_model must expose a .model attribute")
        predict = getattr(inner, "predict", None)
        if predict is None:
            raise TypeError("dqn_model.model must expose predict(...)")

        batch = np.asarray([vec], dtype=float)
        raw = predict(batch, verbose=0)
        scores = np.asarray(raw, dtype=float)
        if scores.ndim == 2:
            scores = scores[0]
        if scores.shape != (4,):
            raise ValueError(f"Expected four Q-scores; got shape {scores.shape}")
        return scores
