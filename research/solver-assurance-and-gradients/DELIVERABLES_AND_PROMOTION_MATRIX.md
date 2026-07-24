# Deliverables and promotion matrix

See also `RESEARCH_STATUS.md` for the §9–§10 closure audit with evidence paths.

## Ten research deliverables

1. A versioned solver-disagreement corpus. — **yes** (`sdc-v0.1.0`, Clarabel/SCS; experimental)
2. A risk-based shadow-sampling study. — **yes** (Wilson 95% CI, cost-detection curve, negatives)
3. A Safety-Gradient Observatory with exact, smoothed, and finite-difference modes. — **partial** (FD + research adapters; native exact/smoothed **experimental** on Moreau hosts)
4. An active-set transition benchmark. — **yes** (`asb-v0.2.0` + integrity checks)
5. Counterfactual safety-frontier tools. — **yes** (`sequential_adapter` + `NOT_PUBLICATION_GRADE`)
6. A formally specified Assurance Bundle. — **yes** (research schema)
7. Replay and corruption-testing tools. — **yes**
8. One robust conic safety-filter demonstration. — **yes (experimental)** (CBF 1–3 + `cbf-v0.1.0` + short-horizon RH `rh-v0.1.0`; not full MPC / multi-robot / production)
9. A decision report on whether intervention-aware training is scientifically justified. — **blocked scientific evidence matrix** (`r6-decision-v0.3.0`; flagship-gate wired; harness structure; no results)
10. A promotion matrix distinguishing experimental / internally validated / governed research artifact / production-qualified capability. — **this document**

## Evidence path index (§9)

| # | Primary evidence paths |
| - | ---------------------- |
| 1 | `conicshield/experimental/solver_assurance/disagreement_corpus.py`; `research/.../corpus` packaging `sdc-v0.1.0` |
| 2 | `sampling_study.py`; `fixtures/sampling_study_ci_small.json` |
| 3 | `gradients/observatory.py`, `agreement_study.py`, `exact_backend.py`, `smoothed_backend.py` |
| 4 | `corpus/active_set_benchmark.py`; `fixtures/active_set_transition_benchmark.json` |
| 5 | `frontiers/sweeps.py`, `local_global.py`, `safety_response_map.py` |
| 6 | `assurance/bundle.py`; `schemas/assurance_bundle.schema.json` |
| 7 | `assurance/replay.py`, `assurance/checks.py`; `tests/research/test_assurance_*` |
| 8 | `domains/cbf_2d.py`, `cbf_rh.py`, `stage4_gate.py`, `cbf_corpus.py`; `fixtures/cbf_rh_ci_small.json`; `schemas/cbf_receding_horizon.schema.json`, `schemas/cbf_stage4_gate.schema.json` |
| 9 | `training/r6_decision_scaffold.py`; `reports/R6_DECISION_REPORT_SCAFFOLD.*` |
| 10 | This file; `RESEARCH_STATUS.md`; `PROMOTION_GATES.md` |

## Promotion matrix (wave 8 status)

| Capability | Experimental | Internally validated | Governed research artifact | Production-qualified |
| ---------- | ------------ | -------------------- | -------------------------- | -------------------- |
| R0 corpus + generators (`r0-v0.3.0`) | yes | pending CI soak | experimental family id only | no |
| CBF held-out corpus (`cbf-v0.1.0`) | yes | pending | no | no |
| Public shadow harness | yes | pending | no | no |
| Solver-disagreement corpus export (`sdc-v0.1.0`) | yes | pending | no | no |
| Risk-based sampling study (+ Wilson CI / cost-detection curve) | yes | pending nightly | no | no |
| Candidate-stack promotion protocol (`csp-v0.2.0`) | yes (public Clarabel/SCS) | pending | no | no |
| Formal hypothesis protocols (R1.H1/H2, R2.H2/H3, …) | yes | pending nightly | no | no |
| FD gradient infrastructure | yes | pending | no | no |
| Exact / smoothed **native** gradients | yes (experimental Moreau backends; fail closed when unavailable) | pending live vendor CI | no | no |
| Research KKT / smoothed projection adapters | yes (distinct labels) | pending | no | no |
| Corpus-wide KKT↔FD agreement study | yes (CI-small + nightly full) | pending multi-host | no | no |
| Active-set transition benchmark (`asb-v0.2.0`) | yes | pending | no | no |
| Frontier sweeps + local-global + safety response map | yes (`sequential_adapter` + watermark) | no | no | no |
| AssuranceBundle + checks + replay + platform-matrix soak | yes | pending **real** multi-host soak | no | no |
| Multi-host soak **simulation** + governed hash research adapter | yes (synthetic; not real multi-host) | no | no | no |
| Multi-host soak **runbook** + optional CI OS matrix | yes (operator + `research-multi-host-soak.yml`) | pending green CI aggregate + production hash | no | no |
| CBF 2D domain stages 1–3 + held-out / taxonomy | yes | pending | no | no |
| CBF stage 4 experimental short-horizon RH (`rh-v0.1.0`) | yes (gate-gated; not full MPC) | pending | no | no |
| Research Windows-sidecar protocol stub + labeled mock | yes (fail closed / mock-labeled) | no | no | no |
| Track 1 readiness probe (`t1-probe-v0.2.1`) | yes (live-sample bar; env-aware WSL Python for S5) | n/a | no | no |
| Intervention-aware training / R6 decision | blocked evidence matrix + harness (`r6-decision-v0.3.0`; flagship-gated) | no | no | no |

Honest reading: **most capabilities remain experimental**. Nothing here is production-qualified.
Internally validated / governed columns stay empty until real multi-host soak, Track 1 S4
vendor attestation, native gradients (if claimed), and corresponding promotion gates pass.

Production-qualified requires Track 1 foundations and the corresponding promotion gate in `PROMOTION_GATES.md`.
