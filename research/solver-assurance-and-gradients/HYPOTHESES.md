# Research hypotheses

Evaluation format: each hypothesis is scored `pass` / `fail` / `inconclusive` / `blocked` / `not_evaluated` with evidence pointers.
Machine-readable catalog + pre-registered protocols: `conicshield.experimental.solver_assurance.hypotheses_eval`.

CI-small deterministic fixture: `python -m conicshield.experimental.solver_assurance.hypotheses_eval`
Nightly / wave5: `python experiments/research_wave5/run_hypothesis_eval.py`

## R1 — Solver assurance

- **R1.H1** Active-set changes predict solver disagreement better than raw proposal distance. — scored by `evaluate_r1_h1_from_features` (protocol thresholds + Bonferroni note).
- **R1.H2** Residual-based sampling detects most consequential disagreements at substantially lower shadow cost than uniform sampling. — scored from `research.sampling_study.v0`.
- **R1.H3** Warm-start anomalies are early signals of solver instability. — `not_evaluated` (instrumentation incomplete).
- **R1.H4** Cross-platform disagreement is dominated by a small number of conditioning regimes. — pending multi-platform soak; Clarabel/SCS-only is insufficient for pass.

## R2 — Safety gradients

- **R2.H1** Exact, smoothed, and finite-difference modes disagree most near active-set transitions. — `inconclusive` (native exact/smoothed backends exist; live multi-host Moreau coverage still required; research KKT/smoothed adapters are distinct evidence kinds).
- **R2.H2** Dual magnitude alone is a weak predictor of causal sensitivity without normalization and validation. — scored by `evaluate_r2_h2_from_dual_study`.
- **R2.H3** Local Jacobian norms rise before discrete active-set changes in bound-neighborhood corpora. — scored by `evaluate_r2_h3_from_jac_trajectory` on `active_set_transition_neighborhoods`.

## R3 — Frontiers

- **R3.H1** Local gradient predictions of nearby frontier movement fail precisely where active sets change. — scored by `evaluate_r3_h1_from_local_global`.
- **R3.H2** Pareto-efficient safety-parameter choices are concentrated in a small number of conditioning regimes. — `not_evaluated`.

## R4 — Assurance bundles

- **R4.H1** Evidence levels L0–L4 communicate assurance strength without implying universal safety guarantees. — semantics + naming checks; formal user study not claimed.
- **R4.H2** Corruption and missing-evidence tests catch overstated "proof-carrying" claims. — covered by research assurance tests + sealed-digest checks.

## R6 — Training (blocked)

- **R6.H1** Reducing intervention rate on the training distribution does not imply improved held-out safety margin. — `blocked` until R2 and R4 promotion gates pass.
