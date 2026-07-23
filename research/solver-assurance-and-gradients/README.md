# Solver assurance and gradients (Track 2)

Research program root for ConicShield Track 2. See `CHARTER.md`.

## Quick start

```bash
# Generate / refresh versioned R0 corpus
python -m conicshield.experimental.corpus.generate

# Validate corpus integrity
python -m conicshield.experimental.corpus.validate

# Public-solver shadow harness
python -m conicshield.experimental.solver_assurance.shadow_harness

# Risk-based sampling study (CI-small)
python -m conicshield.experimental.solver_assurance.sampling_study --ci-small

# Candidate stack promotion (Clarabel vs SCS)
python -m conicshield.experimental.solver_assurance.promotion_protocol

# Formal hypothesis evaluation (CI-small fixture)
python -m conicshield.experimental.solver_assurance.hypotheses_eval

# Wave runners
python experiments/research_wave1/run_shadow_harness.py
python experiments/research_wave2/run_sampling_study.py
python experiments/research_wave2/run_observatory.py
python experiments/research_wave3/run_frontiers.py
python experiments/research_wave4/run_assurance_and_cbf.py
python experiments/research_wave5/run_hypothesis_eval.py
python experiments/research_wave5/run_gradients_and_cbf.py
python experiments/research_wave5/run_clean_env_soak.py
python experiments/research_wave6/run_agreement_study.py --ci-small
python experiments/research_wave6/run_platform_soak.py
python experiments/research_wave6/run_wave6_closure.py

# Wave 7–8 entrypoints
python -m conicshield.experimental.domains.cbf_corpus
python -m conicshield.experimental.domains.infeasibility_taxonomy
python -m conicshield.experimental.assurance.multi_host_soak_sim
python -m conicshield.experimental.solver_assurance.disagreement_corpus
python -m conicshield.experimental.domains.stage4_gate
python experiments/research_wave8/run_cbf_rh_ci_small.py
python -m conicshield.experimental.adapters.track1_probe
python -m conicshield.experimental.training.r6_decision_scaffold

# Research tests
python -m pytest tests/research -q
```

## Layout

- `corpus/` — versioned R0 scenarios + manifest (`r0-v0.3.0`)
- `corpus/cbf/` — held-out CBF corpus (`cbf-v0.1.0`)
- `schemas/` — experimental JSON schemas
- `fixtures/` — committed CI-small study summaries (incl. `cbf_rh_ci_small.json`)
- `notes/` — research model notes (e.g. CBF stage-3 uncertainty)
- `reports/` — report templates + R6 decision scaffold
- Docs in this directory — charter, principles, hypotheses, promotion gates, assurance semantics, `RESEARCH_STATUS.md`
- Implementation — `conicshield/experimental/`
- Entrypoints — `experiments/research_wave{1,2,3,4,5,6,8}/`

## Status (wave 8)

| Area | Status |
| ---- | ------ |
| R1 disagreement taxonomy + sampling + promotion + H1/H2 + CI curves + `sdc-v0.1.0` | implemented (public solvers) |
| R2 FD observatory + dual-pressure + research KKT/smoothed + corpus agreement study | implemented; native exact/smoothed backends (`AVAILABLE`/`UNAVAILABLE`) |
| R3 frontiers + local-global + safety response map | implemented with `sequential_adapter` + watermark |
| R4 AssuranceBundle + platform-matrix soak + synthetic multi-host sim + hash research adapter | implemented; real multi-host soak pending |
| R5 CBF stages 1–3 + `cbf-v0.1.0` + taxonomy + experimental RH `rh-v0.1.0` | stage-4 `experimental_rh_available`; not full MPC; not production-qualified |
| R6 training | blocked; scientific decision evidence matrix only (`r6-decision-v0.2.0`) |
| Research Windows-sidecar protocol stub + labeled mock | fail-closed / mock-labeled |
| Track 1 probe (`t1-probe-v0.1.0`) | S4/S5 unattested; S6 requires production differentiation_api; watermarks retained |

Closure audit: `RESEARCH_STATUS.md`.
