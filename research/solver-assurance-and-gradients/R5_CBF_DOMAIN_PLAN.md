# R5 — One robust conic validation domain (staged plan)

## Selected domain

Uncertainty-aware control-barrier safety filter for two-dimensional motion.

## Stages

1. Nominal affine control-barrier QP. **Implemented** (`apply_cbf_filter`).
2. Batched agents with distinct states and obstacles. **Implemented** (`apply_cbf_filter_batched`, sequential research batch).
3. Uncertainty-aware robust margin expressed through a second-order cone when justified by the model. **Scaffold** with math notes (`SOCRobustMarginScaffold`); not claimed.
4. Optional short receding horizon only after the single-step system is validated. **Blocked** — machine-checkable gate evaluator (`evaluate_stage4_gate`) emits pass/fail/pending with evidence pointers; RH-MPC not implemented while required criteria remain pending.

## Scope limit

Do not add multiple robotics environments, full autonomous-driving stacks, or a general MPC framework. One deep, reproducible validation domain is sufficient.

## Baselines

- `no_filter`
- `public_solver_filter` (Clarabel/SCS)
- `moreau_filter` (fail-closed when unavailable)
- `primary_plus_shadow_assurance`
- `exact_versus_smoothed_differentiable_filter` (fail-closed when unavailable; CBF baseline not yet wired to live backends)

## Implementation

`conicshield.experimental.domains.cbf_2d` (wave-1 scaffold shim retained for import compatibility).
