"""R6 training stubs and R15 comparison harness (fail-closed until flagship gate)."""

from __future__ import annotations

from typing import Any

__all__ = [
    "COMPARISON_ARMS",
    "CRITICAL_PROMOTION_RULE",
    "HELD_OUT_EVAL_FIELDS",
    "InterventionAwareTrainingPlan",
    "build_controlled_comparison_harness",
    "build_r6_decision_report_scaffold",
    "probe_flagship_gate_for_training",
    "r6_execution_authorized",
    "run_controlled_comparison",
    "train_intervention_aware_policy",
    "write_r6_decision_scaffold",
]

# All surfaces lazy: keeps assurance/proof_carrying off the package import path
# and avoids runpy double-import of r6_decision_scaffold as __main__.
_LAZY = {
    "COMPARISON_ARMS": ("conicshield.experimental.training.comparison_harness", "COMPARISON_ARMS"),
    "CRITICAL_PROMOTION_RULE": (
        "conicshield.experimental.training.comparison_harness",
        "CRITICAL_PROMOTION_RULE",
    ),
    "HELD_OUT_EVAL_FIELDS": (
        "conicshield.experimental.training.comparison_harness",
        "HELD_OUT_EVAL_FIELDS",
    ),
    "InterventionAwareTrainingPlan": (
        "conicshield.experimental.training.intervention_aware_stub",
        "InterventionAwareTrainingPlan",
    ),
    "build_controlled_comparison_harness": (
        "conicshield.experimental.training.comparison_harness",
        "build_controlled_comparison_harness",
    ),
    "build_r6_decision_report_scaffold": (
        "conicshield.experimental.training.r6_decision_scaffold",
        "build_r6_decision_report_scaffold",
    ),
    "probe_flagship_gate_for_training": (
        "conicshield.experimental.training.comparison_harness",
        "probe_flagship_gate_for_training",
    ),
    "r6_execution_authorized": (
        "conicshield.experimental.training.comparison_harness",
        "r6_execution_authorized",
    ),
    "run_controlled_comparison": (
        "conicshield.experimental.training.comparison_harness",
        "run_controlled_comparison",
    ),
    "train_intervention_aware_policy": (
        "conicshield.experimental.training.intervention_aware_stub",
        "train_intervention_aware_policy",
    ),
    "write_r6_decision_scaffold": (
        "conicshield.experimental.training.r6_decision_scaffold",
        "write_r6_decision_scaffold",
    ),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        import importlib

        mod_name, attr = _LAZY[name]
        return getattr(importlib.import_module(mod_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
