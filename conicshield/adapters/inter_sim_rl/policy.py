from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np


class ScorePolicyProtocol(Protocol):
    def score_actions(self, state: Any) -> np.ndarray:
        ...


@dataclass(slots=True)
class InterSimKerasDQNPolicy:
    """Adapter around an object exposing `.model.predict(...)`."""

    dqn_model: Any

    def score_actions(self, state: Any) -> np.ndarray:
        if hasattr(state, "get_state_vector"):
            state_vector = state.get_state_vector()
        else:
            state_vector = np.asarray(state, dtype=float)

        scores = self.dqn_model.model.predict(
            np.asarray([state_vector], dtype=float),
            verbose=0,
        )[0]
        return np.asarray(scores, dtype=float)
