# R6 — Intervention-aware policy training (BLOCKED)

This work package remains **blocked** until the R14 flagship promotion gate passes
(`evaluate_flagship_promotion_gate` in `conicshield.experimental.assurance.proof_carrying`).

R2 and R4 remain supporting prerequisites folded into flagship predicates. Today's
environment fails closed (for example native Moreau / multi-host participation is
still missing even though sidecar wire ``PROTOCOL_VERSION`` is v2).

**Numerical evidence is not system-level safety proof.** Passing L0–L4 / flagship
predicates does not by itself authorize a safer-policy claim.

## Controlled comparisons (R15 harness structure)

Documented arms (structure available; execution raises while the flagship gate fails):

1. `unshielded_policy`
2. `shield_only_at_inference`
3. `exact_gradient_training`
4. `smoothed_gradient_training`
5. `intervention_penalty_without_solver_gradient`
6. `dual_pressure_regularization`

## Held-out evaluation matrix (required fields)

Even while blocked / empty, the harness records:

- `unshielded_safety`
- `shielded_safety`
- `safety_margin`
- `task_performance`
- `intervention_frequency`
- `distribution_shift`
- `altered_constraints`
- `shield_removal`
- `smoothing_sensitivity`
- `active_set_transition_behavior`
- `solver_version_change`

## Critical rule

A reduction in intervention frequency alone is **not** evidence of a safer policy.
Promotion requires improved independently measured safety/robustness under held-out
conditions.

## Implementation

- `conicshield.experimental.training.comparison_harness` — controlled comparison +
  held-out matrix; probes the flagship gate (lazy import).
- `conicshield.experimental.training.intervention_aware_stub` — plan + fail-closed
  `train_intervention_aware_policy`.
- `conicshield.experimental.training.r6_decision_scaffold` — BLOCKED decision-report
  scaffold (`r6-decision-v0.3.0`) with flagship-gate dependency (no training results).
