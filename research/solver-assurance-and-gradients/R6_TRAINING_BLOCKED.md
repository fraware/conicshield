# R6 — Intervention-aware policy training (BLOCKED)

This work package is **blocked** until R2 and R4 pass their promotion gates.

## Required comparisons (documented, not implemented)

1. Unshielded policy
2. Policy trained without shield and shielded at inference
3. Policy trained through exact differentiation
4. Policy trained through smoothed differentiation
5. Policy trained with intervention penalties but no shield gradient
6. Policy trained with dual-pressure regularization if justified

## Critical rule

A decrease in intervention rate is not sufficient evidence of improved safety. The policy must improve independently measured safety margin or robustness under held-out conditions.

## Implementation

`conicshield.experimental.training.intervention_aware_stub` documents the plan and raises if training is invoked.

`conicshield.experimental.training.r6_decision_scaffold` emits a BLOCKED decision-report scaffold listing required evidence (no training results).
