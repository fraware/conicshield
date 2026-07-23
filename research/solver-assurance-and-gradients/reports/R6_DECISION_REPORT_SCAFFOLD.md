# R6 decision report scaffold

**Status: BLOCKED**

Document type: `scientific_decision_evidence_matrix`  
Version: `r6-decision-v0.2.0`  
CHARTER question: `Q8`

Is intervention-aware training scientifically justified for ConicShield?

## Blocked until

- R2_promotion_gate
- R4_promotion_gate

## Decision logic (scientific)

- IF R2 and R4 promotion gates are not passed THEN decision_status remains BLOCKED and no training execution is authorized.
- IF independent held-out safety metrics do not improve under shift THEN do not claim scientifically justified intervention-aware training.
- IF only intervention rate decreases without safety-metric gains THEN treat as negative / inconclusive result.
- IF native exact/smoothed backends are UNAVAILABLE (or lack documented exact-vs-FD agreement) THEN do not claim native differentiable training success (research adapters are distinct evidence).
- Stage-4 CBF experimental RH availability does not satisfy R2 or R4 and does not unblock R6.

## Required evidence matrix

| ID | Status | Role | Blocking | Acceptance criterion |
| -- | ------ | ---- | -------- | -------------------- |
| `r2_native_or_validated_gradients` | partial | required | True | Claimed differentiation path has documented exact-vs-FD agreement on active-set coverage corpus; research adapters must not be silently aliased as native Moreau backends. |
| `r4_assurance_reproduction` | partial | required | True | >=2 distinct real hosts reproduce assurance artifacts; synthetic second-host fixtures do not count; production governed-hash wiring present. |
| `track1_s4_hetero_batch_attestation` | missing | required | True | probe_track1_research_readiness().reduce_watermarks is True with S4 research_attested=True on the reporting host. |
| `independent_safety_metrics_under_shift` | missing | required | True | Pre-registered held-out safety metrics improve under shift vs baselines; intervention-rate reduction alone is insufficient. |
| `robustness_to_solver_and_smoothing` | missing | required | True | Sign of safety conclusions unchanged across declared solver/smoothing sensitivity grid; negatives retained. |
| `no_verifier_or_gradient_exploitation` | missing | required | True | Adversarial / known-failure probes do not show metric gaming of verifier or gradient weaknesses. |
| `comparison_battery` | missing | required | True | All listed baselines present with identical metrics and seed control; exact/smoothed baseline entries require live native backend availability and must not be silently substituted by research adapters. |
| `decision_report_with_negative_results` | partial | required | True | Final report includes negatives and an explicit go/no-go under the acceptance criteria above; this scaffold alone is insufficient. |
| `negative_retention_protocol` | partial | negative_retention | True | Artifact store includes failed runs with hashes; omission of negatives is a gate failure. |

### Evidence details

- `r2_native_or_validated_gradients` [partial]: R2 gate: corpus-validated gradients with active-set coverage and exact-vs-FD agreement for the claimed differentiation path (native backends implemented; live Moreau required for AVAILABLE). Research KKT/smoothed adapters are distinct evidence kinds and do not satisfy the native exact-vs-FD promotion gate. pointers=['research/solver-assurance-and-gradients/PROMOTION_GATES.md#r2', 'conicshield.experimental.gradients.agreement_study', 'conicshield.experimental.gradients.exact_backend', 'conicshield.experimental.gradients.smoothed_backend']
- `r4_assurance_reproduction` [partial]: R4 gate: multi-host clean-env soak on >=2 real hosts, schema/replay/corruption tests, and governed hash policy integrated with production release tooling (research adapter exists; production wiring absent). pointers=['research/solver-assurance-and-gradients/PROMOTION_GATES.md#r4', 'conicshield.experimental.assurance.platform_soak', 'conicshield.experimental.assurance.multi_host_soak_sim', 'conicshield.experimental.assurance.governed_hash_policy']
- `track1_s4_hetero_batch_attestation` [missing]: Track 1 S4 heterogeneous batch interface attested; frontiers no longer watermarked sequential_adapter for publication-grade claims. pointers=['conicshield.experimental.adapters.track1_probe.probe_track1_research_readiness', 'conicshield.experimental.frontiers.sweeps.probe_track1_hetero_batch_attestation']
- `independent_safety_metrics_under_shift` [missing]: Held-out safety margin / robustness improvements under distribution shift (not intervention-rate alone). Must include failure cases. pointers=['research/solver-assurance-and-gradients/CHARTER.md', 'conicshield.experimental.domains.cbf_corpus']
- `robustness_to_solver_and_smoothing` [missing]: Results stable across solver backends and smoothing choices; failure cases included.
- `no_verifier_or_gradient_exploitation` [missing]: Training does not exploit known verifier or gradient weaknesses; adversarial checks against documented failure modes from R1/R2 corpora. pointers=['conicshield.experimental.solver_assurance.disagreement_corpus', 'conicshield.experimental.gradients.agreement_study']
- `comparison_battery` [missing]: Documented comparisons vs unshielded / inference-only shield / exact / smoothed / penalty-only / dual-pressure baselines with pre-registered metrics. pointers=['conicshield.experimental.training.intervention_aware_stub']
- `decision_report_with_negative_results` [partial]: Written decision report answering CHARTER Q8 with negative results retained; no claim of learning safer policies without independent safety-metric gains. pointers=['research/solver-assurance-and-gradients/CHARTER.md', 'conicshield.experimental.training.r6_decision_scaffold', 'research/solver-assurance-and-gradients/reports/R6_DECISION_REPORT_SCAFFOLD.md']
- `negative_retention_protocol` [partial]: Protocol for retaining failed seeds, infeasible episodes, and non-improving shift splits — required before any positive R6 claim. pointers=['conicshield.experimental.training.r6_decision_scaffold']

## Non-claims

- No claim of learning safer policies.
- No training results are present in this scaffold.
- Research KKT / smoothed adapters are not native Moreau gradients.
- Intervention-rate reduction alone is insufficient evidence of safety.
- Checklist completeness here does not unblock R6 training execution.
- Stage-4 CBF checklist green / experimental RH does not imply R2/R4 promotion gates passed.
- Track 1 S4/S5 scaffolding without vendor attestation does not clear publication-grade frontiers.

## Results

_None. This scaffold intentionally contains no training results._

## Explicit non-authorization

Completing rows in this matrix as documentation does **not** authorize R6 training execution. Execution remains blocked until R2 and R4 promotion gates pass and the acceptance criteria above are met with retained negatives.
