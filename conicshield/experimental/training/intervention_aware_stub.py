"""Intervention-aware policy training (R6) — BLOCKED until R14 flagship promotion gate passes.

R15 wires authorization through ``evaluate_flagship_promotion_gate`` (lazy) and
exposes the controlled comparison harness structure. Training remains fail-closed
while the flagship gate fails. Numerical evidence is not system safety proof.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from conicshield.experimental.training.comparison_harness import (
    COMPARISON_ARMS,
    CRITICAL_PROMOTION_RULE,
    HELD_OUT_EVAL_FIELDS,
    PUBLIC_CLAIM_BINDING,
    build_controlled_comparison_harness,
    probe_flagship_gate_for_training,
    r6_execution_authorized,
    run_controlled_comparison,
)


@dataclass(slots=True)
class InterventionAwareTrainingPlan:
    status: str = "BLOCKED"
    blocked_until: str = (
        "R14 flagship promotion gate passes (evaluate_flagship_promotion_gate); "
        "R2/R4 remain supporting prerequisites"
    )
    comparisons: tuple[str, ...] = COMPARISON_ARMS
    held_out_eval_fields: tuple[str, ...] = HELD_OUT_EVAL_FIELDS
    objective_components: tuple[str, ...] = (
        "task_loss",
        "intervention_distance_penalty",
        "safety_margin_penalty",
        "dual_pressure_penalty",
        "sensitivity_penalty",
        "active_set_instability_penalty",
    )
    critical_rule: str = CRITICAL_PROMOTION_RULE
    promotion_gate: str = (
        "No claim of learning safer policies unless: independently measured safety/"
        "robustness improves under held-out conditions; results hold under distribution "
        "shift, altered constraints, shield removal, smoothing sensitivity, active-set "
        "transitions, and solver-version change; failure cases are retained; training "
        "does not exploit known verifier or gradient weaknesses. Intervention-frequency "
        "reduction alone is insufficient. Flagship numerical evidence is not system "
        "safety proof."
    )
    public_claim_binding: str = PUBLIC_CLAIM_BINDING

    def as_dict(self) -> dict[str, Any]:
        gate = probe_flagship_gate_for_training()
        authorized = bool(gate.get("r6_execution_authorized"))
        return {
            "status": "AUTHORIZED_STRUCTURE_ONLY" if authorized else self.status,
            "blocked_until": self.blocked_until,
            "comparisons": list(self.comparisons),
            "held_out_eval_fields": list(self.held_out_eval_fields),
            "objective_components": list(self.objective_components),
            "critical_rule": self.critical_rule,
            "promotion_gate": self.promotion_gate,
            "public_claim_binding": self.public_claim_binding,
            "flagship_gate": gate,
            "execution_authorized": authorized,
            "implementation": "r15_harness_structure_fail_closed",
        }


def train_intervention_aware_policy(*_args: Any, **kwargs: Any) -> None:
    """Fail-closed entrypoint: raises unless the R14 flagship promotion gate passes."""

    gate = probe_flagship_gate_for_training(**{
        k: kwargs[k]
        for k in (
            "projection",
            "stages",
            "corrupted_artifact_rejected",
            "incomplete_bundle_rejected",
            "multi_host_includes_native_moreau",
            "docs_path",
        )
        if k in kwargs
    })
    if not gate.get("r6_execution_authorized"):
        blockers = gate.get("blockers") or []
        raise RuntimeError(
            "R6 intervention-aware training is BLOCKED until the R14 flagship promotion "
            f"gate passes. blockers={list(blockers)}. "
            "See research/solver-assurance-and-gradients/R6_TRAINING_BLOCKED.md. "
            f"{CRITICAL_PROMOTION_RULE}"
        )
    # Even if research gate predicates green, do not fabricate training results.
    raise RuntimeError(
        "Flagship gate passed, but executable intervention-aware training loops are not "
        "implemented in this drop. Use build_controlled_comparison_harness / "
        "run_controlled_comparison for the authorized structure. "
        f"{CRITICAL_PROMOTION_RULE}"
    )


__all__ = [
    "COMPARISON_ARMS",
    "CRITICAL_PROMOTION_RULE",
    "HELD_OUT_EVAL_FIELDS",
    "InterventionAwareTrainingPlan",
    "PUBLIC_CLAIM_BINDING",
    "build_controlled_comparison_harness",
    "probe_flagship_gate_for_training",
    "r6_execution_authorized",
    "run_controlled_comparison",
    "train_intervention_aware_policy",
]
