from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

import numpy as np

CANONICAL_ACTION_SPACE: tuple[str, ...] = (
    "turn_left",
    "turn_right",
    "go_straight",
    "turn_back",
)


def wrap_angle_deg(theta: float) -> float:
    return theta % 360.0


def angular_distance_deg(a: float, b: float) -> float:
    delta = abs(wrap_angle_deg(a) - wrap_angle_deg(b))
    return min(delta, 360.0 - delta)


def target_heading_by_action(current_heading_deg: float) -> dict[str, float]:
    return {
        "go_straight": wrap_angle_deg(current_heading_deg),
        "turn_left": wrap_angle_deg(current_heading_deg - 90.0),
        "turn_right": wrap_angle_deg(current_heading_deg + 90.0),
        "turn_back": wrap_angle_deg(current_heading_deg + 180.0),
    }


@dataclass(slots=True)
class GeometryPriorConfig:
    sigma_deg: float = 35.0
    min_mass: float = 1e-6
    base_weight: float = 0.10
    hazard_weight_scale: float = 0.55
    fallback_uniform: bool = True


def gaussian_heading_score(*, target_deg: float, candidate_deg: float, sigma_deg: float) -> float:
    d = angular_distance_deg(target_deg, candidate_deg)
    return math.exp(-(d * d) / (2.0 * sigma_deg * sigma_deg))


def infer_geometry_prior(
    *,
    context: Mapping[str, object],
    config: GeometryPriorConfig | None = None,
) -> tuple[np.ndarray | None, float]:
    cfg = config or GeometryPriorConfig()

    heading = context.get("current_heading_deg")
    branch_bearings = context.get("branch_bearings_deg")
    hazard_score = context.get("hazard_score", 0.0)

    if heading is None or not branch_bearings:
        if not cfg.fallback_uniform:
            return None, 0.0
        prior = np.ones(len(CANONICAL_ACTION_SPACE), dtype=float)
        prior /= np.sum(prior)
        return prior, 0.0

    heading = float(heading)
    bearings = [float(b) for b in branch_bearings]
    targets = target_heading_by_action(heading)

    scores = np.zeros(len(CANONICAL_ACTION_SPACE), dtype=float)
    for i, action_name in enumerate(CANONICAL_ACTION_SPACE):
        target = targets[action_name]
        best = max(
            gaussian_heading_score(
                target_deg=target,
                candidate_deg=bearing,
                sigma_deg=cfg.sigma_deg,
            )
            for bearing in bearings
        )
        scores[i] = max(cfg.min_mass, best)

    prior = scores / np.sum(scores)

    hz = max(0.0, min(1.0, float(hazard_score)))
    weight = cfg.base_weight + cfg.hazard_weight_scale * hz
    return prior, weight
