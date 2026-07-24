"""R15 controlled comparison harness for intervention-aware training (R6).

Structure is always available. Execution remains fail-closed until the R14
flagship promotion gate passes. Intervention-frequency reduction alone is
never treated as evidence of a safer policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

COMPARISON_HARNESS_SCHEMA_ID = "research.r6_controlled_comparison_harness.v1"
COMPARISON_HARNESS_VERSION = "r15-harness-v1.0.0"

# Controlled comparison arms (plan R15 / directive).
COMPARISON_ARMS: tuple[str, ...] = (
    "unshielded_policy",
    "shield_only_at_inference",
    "exact_gradient_training",
    "smoothed_gradient_training",
    "intervention_penalty_without_solver_gradient",
    "dual_pressure_regularization",
)

# Held-out evaluation matrix fields (required even when blocked / empty).
HELD_OUT_EVAL_FIELDS: tuple[str, ...] = (
    "unshielded_safety",
    "shielded_safety",
    "safety_margin",
    "task_performance",
    "intervention_frequency",
    "distribution_shift",
    "altered_constraints",
    "shield_removal",
    "smoothing_sensitivity",
    "active_set_transition_behavior",
    "solver_version_change",
)

CRITICAL_PROMOTION_RULE = (
    "A reduction in intervention frequency alone is NOT evidence of a safer policy. "
    "Promotion requires improved independently measured safety/robustness under "
    "held-out conditions."
)

PUBLIC_CLAIM_BINDING = (
    "Numerical assurance evidence (flagship L0–L4 / ProofCarryingProjection) is not "
    "system-level safety proof and does not by itself authorize a safer-policy claim."
)


def _lazy_evaluate_flagship_promotion_gate(projection: Any | None = None, **kwargs: Any) -> Any:
    """Lazy import to preserve R10/R11 cycle breaks (training must not import assurance at module load)."""

    from conicshield.experimental.assurance.proof_carrying import evaluate_flagship_promotion_gate

    return evaluate_flagship_promotion_gate(projection, **kwargs)


def probe_flagship_gate_for_training(
    *,
    projection: Any | None = None,
    stages: Any | None = None,
    corrupted_artifact_rejected: bool = False,
    incomplete_bundle_rejected: bool = False,
    multi_host_includes_native_moreau: bool | None = None,
    docs_path: Any | None = None,
) -> dict[str, Any]:
    """Evaluate the R14 flagship gate and return a serializable authorization snapshot.

    Fail-closed defaults: without demonstrated corruption/incomplete rejection and
    without a live proof-carrying projection, the gate does not pass.
    """

    gate = _lazy_evaluate_flagship_promotion_gate(
        projection,
        stages=stages,
        corrupted_artifact_rejected=corrupted_artifact_rejected,
        incomplete_bundle_rejected=incomplete_bundle_rejected,
        multi_host_includes_native_moreau=multi_host_includes_native_moreau,
        docs_path=docs_path,
    )
    d = gate.as_dict()
    return {
        "schema_id": d.get("schema_id"),
        "passed": bool(d.get("passed")),
        "predicates": dict(d.get("predicates") or {}),
        "blockers": list(d.get("blockers") or []),
        "production_claim": False,
        "r6_execution_authorized": bool(d.get("passed")),
        "public_claim": d.get("public_claim"),
        "public_claim_nonclaim": d.get("public_claim_nonclaim"),
        "notes": list(d.get("notes") or []),
    }


def r6_execution_authorized(**kwargs: Any) -> bool:
    """True only when the flagship promotion gate passes (research predicates)."""

    return bool(probe_flagship_gate_for_training(**kwargs).get("r6_execution_authorized"))


@dataclass(slots=True)
class ComparisonArmResult:
    arm_id: str
    status: str = "blocked"  # blocked | pending | complete | failed
    metrics: dict[str, Any] | None = None
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "arm_id": self.arm_id,
            "status": self.status,
            "metrics": None if self.metrics is None else dict(self.metrics),
            "notes": list(self.notes),
        }


@dataclass(slots=True)
class HeldOutEvalMatrix:
    """Pre-registered held-out fields; values remain None while execution is blocked."""

    fields: dict[str, Any | None] = field(default_factory=dict)
    status: str = "blocked"
    critical_rule: str = CRITICAL_PROMOTION_RULE

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "critical_rule": self.critical_rule,
            "fields": {k: self.fields.get(k) for k in HELD_OUT_EVAL_FIELDS},
            "required_field_ids": list(HELD_OUT_EVAL_FIELDS),
            "note": (
                "Intervention frequency alone must not be used as a safety promotion signal. "
                "Independently measured safety/robustness under held-out conditions is required."
            ),
        }


@dataclass(slots=True)
class ControlledComparisonHarness:
    schema_id: str = COMPARISON_HARNESS_SCHEMA_ID
    harness_version: str = COMPARISON_HARNESS_VERSION
    status: str = "BLOCKED"
    flagship_gate: dict[str, Any] = field(default_factory=dict)
    arms: list[ComparisonArmResult] = field(default_factory=list)
    held_out_eval: HeldOutEvalMatrix = field(default_factory=HeldOutEvalMatrix)
    critical_rule: str = CRITICAL_PROMOTION_RULE
    public_claim_binding: str = PUBLIC_CLAIM_BINDING
    results: None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "harness_version": self.harness_version,
            "status": self.status,
            "flagship_gate": dict(self.flagship_gate),
            "comparison_arms": [a.as_dict() for a in self.arms],
            "comparison_arm_ids": list(COMPARISON_ARMS),
            "held_out_eval": self.held_out_eval.as_dict(),
            "critical_rule": self.critical_rule,
            "public_claim_binding": self.public_claim_binding,
            "results": self.results,
            "execution_authorized": bool(self.flagship_gate.get("r6_execution_authorized")),
        }


def empty_held_out_eval(*, status: str = "blocked") -> HeldOutEvalMatrix:
    return HeldOutEvalMatrix(
        fields={fid: None for fid in HELD_OUT_EVAL_FIELDS},
        status=status,
        critical_rule=CRITICAL_PROMOTION_RULE,
    )


def build_controlled_comparison_harness(**gate_kwargs: Any) -> ControlledComparisonHarness:
    """Build the comparison + held-out matrix structure (blocked when flagship gate fails)."""

    gate = probe_flagship_gate_for_training(**gate_kwargs)
    authorized = bool(gate.get("r6_execution_authorized"))
    arm_status = "pending" if authorized else "blocked"
    arm_notes = (
        ()
        if authorized
        else (
            "Arm execution blocked until flagship promotion gate passes.",
            CRITICAL_PROMOTION_RULE,
        )
    )
    arms = [
        ComparisonArmResult(arm_id=arm_id, status=arm_status, metrics=None, notes=arm_notes)
        for arm_id in COMPARISON_ARMS
    ]
    return ControlledComparisonHarness(
        status="AUTHORIZED_STRUCTURE_ONLY" if authorized else "BLOCKED",
        flagship_gate=gate,
        arms=arms,
        held_out_eval=empty_held_out_eval(status="pending" if authorized else "blocked"),
        results=None,
    )


def run_controlled_comparison(**gate_kwargs: Any) -> ControlledComparisonHarness:
    """Execute the comparison battery. Raises while the flagship gate fails (fail-closed)."""

    harness = build_controlled_comparison_harness(**gate_kwargs)
    if not harness.flagship_gate.get("r6_execution_authorized"):
        blockers = harness.flagship_gate.get("blockers") or []
        raise RuntimeError(
            "R6 controlled comparison execution is BLOCKED until the R14 flagship "
            f"promotion gate passes. blockers={list(blockers)}. "
            "See research/solver-assurance-and-gradients/R6_TRAINING_BLOCKED.md. "
            f"{CRITICAL_PROMOTION_RULE}"
        )
    # Gate passed: structure is ready, but this work package still does not fabricate
    # training results. Callers must supply a real training loop in a later drop.
    raise RuntimeError(
        "Flagship gate passed, but R15 does not yet implement executable training loops. "
        "Harness structure is authorized; fill results only after real held-out runs. "
        f"{CRITICAL_PROMOTION_RULE}"
    )


__all__ = [
    "COMPARISON_ARMS",
    "COMPARISON_HARNESS_SCHEMA_ID",
    "COMPARISON_HARNESS_VERSION",
    "CRITICAL_PROMOTION_RULE",
    "ComparisonArmResult",
    "ControlledComparisonHarness",
    "HELD_OUT_EVAL_FIELDS",
    "HeldOutEvalMatrix",
    "PUBLIC_CLAIM_BINDING",
    "build_controlled_comparison_harness",
    "empty_held_out_eval",
    "probe_flagship_gate_for_training",
    "r6_execution_authorized",
    "run_controlled_comparison",
]
