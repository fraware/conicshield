# R6 decision report scaffold

**Status: BLOCKED**

Document type: `scientific_decision_evidence_matrix`  
Version: `r6-decision-v0.3.0`  
CHARTER question: `Q8`

Is intervention-aware training scientifically justified for ConicShield?

## Flagship gate dependency (R14 → R15)

- `r6_execution_authorized`: `False`
- `flagship_gate.passed`: `False`
- blockers: `['missing_proof_carrying_projection', 'sidecar_protocol_v2_incomplete:got=1;need>=2', 'moreau_compatibility_unqualified:moreau_import_failed:ModuleNotFoundError', 'multi_host_missing_native_moreau', 'gradients_missing_or_unlinked', 'cbf_not_independently_verified', 'corrupted_artifact_rejection_not_demonstrated', 'incomplete_bundle_rejection_not_demonstrated']`

A reduction in intervention frequency alone is NOT evidence of a safer policy. Promotion requires improved independently measured safety/robustness under held-out conditions.

Numerical assurance evidence (flagship L0–L4 / ProofCarryingProjection) is not system-level safety proof and does not by itself authorize a safer-policy claim.

## Blocked until

- flagship_promotion_gate
- R2_promotion_gate
- R4_promotion_gate

## Decision logic (scientific)

- IF evaluate_flagship_promotion_gate does not pass THEN decision_status remains BLOCKED and no training execution is authorized (fail-closed).
- IF R2 and R4 promotion gates are not passed THEN treat as supporting blockers under the flagship gate; do not authorize R6 execution.
- IF independent held-out safety metrics do not improve under shift THEN do not claim scientifically justified intervention-aware training.
- IF only intervention frequency decreases without safety-metric gains THEN treat as negative / inconclusive result — never as promotion evidence.
- IF native exact/smoothed gradients are unavailable on the training host THEN do not claim native differentiable training success (research adapters are distinct evidence).
- Flagship / L0–L4 numerical assurance is not system-level safety proof and does not alone justify a safer-policy claim.
- Stage-4 CBF experimental RH availability does not satisfy flagship / R2 / R4 and does not unblock R6.

## Controlled comparison arms

- `unshielded_policy`
- `shield_only_at_inference`
- `exact_gradient_training`
- `smoothed_gradient_training`
- `intervention_penalty_without_solver_gradient`
- `dual_pressure_regularization`

## Held-out evaluation matrix fields

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

## Required evidence matrix

| ID | Status | Role | Blocking | Acceptance criterion |
| -- | ------ | ---- | -------- | -------------------- |
| `flagship_promotion_gate` | blocked_dependency | required | True | evaluate_flagship_promotion_gate(...).passed is True with retained blockers empty; production_claim remains False. Numerical evidence is not a system safety proof. |
| `r2_native_or_validated_gradients` | partial | required | True | Claimed differentiation path has documented exact-vs-FD agreement on active-set coverage corpus; research adapters must not be silently aliased as native Moreau backends. |
| `r4_assurance_reproduction` | partial | required | True | >=2 distinct real hosts reproduce assurance artifacts; synthetic second-host fixtures do not count; production governed-hash wiring present. |
| `track1_s4_hetero_batch_attestation` | missing | required | True | probe_track1_research_readiness().reduce_watermarks is True with S4 research_attested=True on the reporting host. |
| `independent_safety_metrics_under_shift` | missing | required | True | Pre-registered held-out safety metrics improve under shift vs baselines; intervention-frequency reduction alone is insufficient for promotion. |
| `robustness_to_solver_and_smoothing` | missing | required | True | Sign of safety conclusions unchanged across declared solver/smoothing sensitivity grid; negatives retained. |
| `no_verifier_or_gradient_exploitation` | missing | required | True | Adversarial / known-failure probes do not show metric gaming of verifier or gradient weaknesses. |
| `comparison_battery` | partial | required | True | All listed baselines present with identical metrics and seed control; exact/smoothed baseline entries require live native backend availability and must not be silently substituted by research adapters. |
| `decision_report_with_negative_results` | partial | required | True | Final report includes negatives and an explicit go/no-go under the acceptance criteria above; this scaffold alone is insufficient. |
| `negative_retention_protocol` | partial | negative_retention | True | Artifact store includes failed runs with hashes; omission of negatives is a gate failure. |

### Evidence details

- `flagship_promotion_gate` [blocked_dependency]: R14 flagship promotion gate (`evaluate_flagship_promotion_gate`) must pass before any R6 training execution. Includes level predicates, sidecar protocol ≥ v2, native Moreau multi-host participation, real linked gradients, verified CBF, corrupted/incomplete rejection, and docs limitations. Passing is numerical assurance readiness — not system-level safety proof. pointers=['conicshield.experimental.assurance.proof_carrying.evaluate_flagship_promotion_gate', 'research/solver-assurance-and-gradients/PROMOTION_GATES.md#r4', 'research/solver-assurance-and-gradients/ASSURANCE_SEMANTICS.md']
- `r2_native_or_validated_gradients` [partial]: R2 gate: corpus-validated gradients with active-set coverage and exact-vs-FD agreement for the claimed differentiation path (native backends implemented; live Moreau required for AVAILABLE). Research KKT/smoothed adapters are distinct evidence kinds and do not satisfy the native exact-vs-FD promotion gate. pointers=['research/solver-assurance-and-gradients/PROMOTION_GATES.md#r2', 'conicshield.experimental.gradients.agreement_study', 'conicshield.experimental.gradients.exact_backend', 'conicshield.experimental.gradients.smoothed_backend']
- `r4_assurance_reproduction` [partial]: R4 gate: multi-host clean-env soak on >=2 real hosts, schema/replay/corruption tests, and governed hash policy integrated with production release tooling (research adapter exists; production wiring absent). Supporting prerequisite for flagship multi-host predicates. pointers=['research/solver-assurance-and-gradients/PROMOTION_GATES.md#r4', 'conicshield.experimental.assurance.platform_soak', 'conicshield.experimental.assurance.multi_host_soak_sim', 'conicshield.experimental.assurance.governed_hash_policy']
- `track1_s4_hetero_batch_attestation` [missing]: Track 1 S4 heterogeneous batch interface attested; frontiers no longer watermarked sequential_adapter for publication-grade claims. pointers=['conicshield.experimental.adapters.track1_probe.probe_track1_research_readiness', 'conicshield.experimental.frontiers.sweeps.probe_track1_hetero_batch_attestation']
- `independent_safety_metrics_under_shift` [missing]: Held-out safety margin / robustness improvements under distribution shift (not intervention-rate alone). Must include failure cases. Required fields: unshielded_safety, shielded_safety, safety_margin, task_performance, intervention_frequency, distribution_shift, altered_constraints, shield_removal, smoothing_sensitivity, active_set_transition_behavior, solver_version_change. pointers=['research/solver-assurance-and-gradients/CHARTER.md', 'conicshield.experimental.training.comparison_harness', 'conicshield.experimental.domains.cbf_corpus']
- `robustness_to_solver_and_smoothing` [missing]: Results stable across solver backends and smoothing choices; failure cases included. pointers=['conicshield.experimental.training.comparison_harness']
- `no_verifier_or_gradient_exploitation` [missing]: Training does not exploit known verifier or gradient weaknesses; adversarial checks against documented failure modes from R1/R2 corpora. pointers=['conicshield.experimental.solver_assurance.disagreement_corpus', 'conicshield.experimental.gradients.agreement_study']
- `comparison_battery` [partial]: Documented controlled comparisons for arms: unshielded_policy, shield_only_at_inference, exact_gradient_training, smoothed_gradient_training, intervention_penalty_without_solver_gradient, dual_pressure_regularization with pre-registered held-out metrics. Harness structure exists; execution blocked until flagship gate passes. pointers=['conicshield.experimental.training.comparison_harness', 'conicshield.experimental.training.intervention_aware_stub']
- `decision_report_with_negative_results` [partial]: Written decision report answering CHARTER Q8 with negative results retained; no claim of learning safer policies without independent safety-metric gains. pointers=['research/solver-assurance-and-gradients/CHARTER.md', 'conicshield.experimental.training.r6_decision_scaffold', 'research/solver-assurance-and-gradients/reports/R6_DECISION_REPORT_SCAFFOLD.md']
- `negative_retention_protocol` [partial]: Protocol for retaining failed seeds, infeasible episodes, and non-improving shift splits — required before any positive R6 claim. pointers=['conicshield.experimental.training.r6_decision_scaffold']

## Non-claims

- No claim of learning safer policies.
- No training results are present in this scaffold.
- Research KKT / smoothed adapters are not native Moreau gradients.
- Intervention-frequency reduction alone is insufficient evidence of safety.
- Checklist completeness here does not unblock R6 training execution.
- Numerical evidence (ProofCarryingProjection / L0–L4) is not system-level safety proof.
- Stage-4 CBF checklist green / experimental RH does not imply flagship or R2/R4 gates passed.
- Track 1 S4/S5 scaffolding without vendor attestation does not clear publication-grade frontiers.

## Results

_None. This scaffold intentionally contains no training results._

## Explicit non-authorization

Completing rows in this matrix as documentation does **not** authorize R6 training execution. Execution remains blocked until `evaluate_flagship_promotion_gate` passes and the acceptance criteria above are met with retained negatives. Intervention-frequency reduction alone is not promotion evidence. Numerical assurance ≠ system safety proof.
