"""Intervention-aware policy training (R6) — BLOCKED until R2 and R4 promotion gates pass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class InterventionAwareTrainingPlan:
    status: str = "BLOCKED"
    blocked_until: str = "R2 and R4 promotion gates pass"
    comparisons: tuple[str, ...] = (
        "unshielded_policy",
        "trained_without_shield_shielded_at_inference",
        "trained_through_exact_differentiation",
        "trained_through_smoothed_differentiation",
        "trained_with_intervention_penalties_no_shield_gradient",
        "trained_with_dual_pressure_regularization_if_justified",
    )
    objective_components: tuple[str, ...] = (
        "task_loss",
        "intervention_distance_penalty",
        "safety_margin_penalty",
        "dual_pressure_penalty",
        "sensitivity_penalty",
        "active_set_instability_penalty",
    )
    critical_rule: str = (
        "A decrease in intervention rate is not sufficient evidence of improved safety. "
        "The policy must improve independently measured safety margin or robustness under held-out conditions."
    )
    promotion_gate: str = (
        "No claim of learning safer policies unless: the unshielded policy improves on independent "
        "safety metrics; results hold under distribution shift; results are robust to solver and "
        "smoothing choices; failure cases are included; training does not exploit known verifier "
        "or gradient weaknesses."
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "blocked_until": self.blocked_until,
            "comparisons": list(self.comparisons),
            "objective_components": list(self.objective_components),
            "critical_rule": self.critical_rule,
            "promotion_gate": self.promotion_gate,
            "implementation": "stub_only_wave1",
        }


def train_intervention_aware_policy(*_args: Any, **_kwargs: Any) -> None:
    raise RuntimeError(
        "R6 intervention-aware training is BLOCKED until R2 and R4 promotion gates pass. "
        "See research/solver-assurance-and-gradients/R6_TRAINING_BLOCKED.md"
    )
