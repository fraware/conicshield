# Research status (Track 2) — post live attestation refresh / Track 1 probe v0.2.1

Honest closure audit against directive deliverables §9 and success criteria §10
(CHARTER required research questions). **No production promotion claimed.**

Corpus context: R0 `r0-v0.3.0` (unchanged). CBF held-out `cbf-v0.1.0`.
Disagreement packaging `sdc-v0.1.0`. Active-set benchmark `asb-v0.2.0`.
Experimental RH filter `rh-v0.1.0`. R6 decision doc `r6-decision-v0.2.0`.
Track 1 probe attestation schema `t1-probe-v0.2.1` (env-aware sidecar WSL
Python; live-sample bar retained from `v0.2.0`).

## §9 — Ten research deliverables

| # | Deliverable | Status | Evidence paths |
| - | ----------- | ------ | -------------- |
| 1 | Versioned solver-disagreement corpus | **Implemented** (experimental; Clarabel/SCS) | `conicshield/experimental/solver_assurance/disagreement_corpus.py`; schema `research.solver_disagreement_corpus.v0`; version `sdc-v0.1.0` |
| 2 | Risk-based shadow-sampling study | **Implemented** (Wilson CI + cost-detection + negatives) | `sampling_study.py`; fixtures `fixtures/sampling_study_ci_small.json`; schema `research.sampling_study.v0` |
| 3 | Safety-Gradient Observatory (exact/smoothed/FD) | **Partial** — FD + research KKT/smoothed yes; **native exact** via `CompiledSolver.backward`; **smoothed** via softplus Moreau-QP softening (experimental; WSL/Linux) | `gradients/observatory.py`, `agreement_study.py`, `exact_backend.py`, `smoothed_backend.py` |
| 4 | Active-set transition benchmark | **Implemented** (`asb-v0.2.0` + integrity checks) | `corpus/active_set_benchmark.py` |
| 5 | Counterfactual safety-frontier tools | **Implemented** — WSL live S4 clears watermark **on that host**; Windows native keeps `sequential_adapter` | `frontiers/sweeps.py`, `local_global.py`, `safety_response_map.py` |
| 6 | Formally specified Assurance Bundle | **Implemented** (research schema) | `assurance/bundle.py`, `schemas/assurance_bundle.schema.json` |
| 7 | Replay and corruption-testing tools | **Implemented** | `assurance/replay.py`, `assurance/checks.py`; `tests/research/test_assurance_*` |
| 8 | One robust conic safety-filter demonstration | **Implemented (experimental)** — CBF stages 1–3 + held-out `cbf-v0.1.0`; stage-4 checklist green; **minimal short-horizon RH** `rh-v0.1.0` (not full MPC / multi-robot) | `domains/cbf_2d.py`, `cbf_rh.py`, `cbf_corpus.py`, `stage4_gate.py`, `infeasibility_taxonomy.py`; fixture `fixtures/cbf_rh_ci_small.json`; schemas `cbf_receding_horizon.schema.json`, `cbf_stage4_gate.schema.json` |
| 9 | Decision report on intervention-aware training | **Blocked scientific decision matrix** (no results) | `training/r6_decision_scaffold.py`; `reports/R6_DECISION_REPORT_SCAFFOLD.*`; version `r6-decision-v0.2.0` |
| 10 | Promotion matrix | **Maintained** | `DELIVERABLES_AND_PROMOTION_MATRIX.md`, this file, `PROMOTION_GATES.md` |

## §10 / CHARTER — Required research questions

| # | Question | Answered? | Evidence / note |
| - | -------- | --------- | --------------- |
| 1 | When do Moreau and independent public solvers disagree? | **Partial** | Public Clarabel vs SCS disagreement corpus (`sdc-v0.1.0`). Live Moreau sidecar hello+project attested on Windows↔WSL path; broader disagreement study still incomplete. |
| 2 | Which observables predict disagreement or fallback? | **Partial** | Sampling study + R1.H1/H2 protocols; residual / active-set features. Warm-start (R1.H3) incomplete. |
| 3 | How stable is corrected action under perturbations? | **Partial** | FD observatory + frontier sweeps; publication-grade on WSL when S4 live-attested. |
| 4 | Where do exact, smoothed, and FD disagree? | **Partial** | Research KKT/smoothed ↔ FD agreement study. Native **exact** path uses `CompiledSolver.backward` + `enable_grad` (experimental; FD-gated). Native **smoothed** uses softplus inequality softening on the Moreau QP (ε recorded; FD-gated). Production `differentiation_api` still **False** (identity probes `differentiate`/`DiffSettings`/`cvxpylayers`). |
| 5 | Can local sensitivity identify upcoming active-set transitions? | **Partial** | Local-global consistency metrics + R2.H3 / R3.H1 protocols; sequential batching watermark on Windows native. |
| 6 | Can counterfactual frontiers improve parameter selection? | **Partial** | Pareto + safety response map; R3.H2 not evaluated; S4 live sample **succeeded on WSL**. |
| 7 | What evidence suffices for "proof-carrying" without overclaim? | **Partial** | Assurance semantics + L0–L4 + replay/corruption. **Two real hosts** (Windows + WSL) aggregated with matching sealed digests → `r4_multi_host_gate_ready=true` (evidence only). Production governed-hash wiring + CI matrix dispatch still open. |
| 8 | Does differentiable training improve safety under shift? | **Unanswered** | R6 **BLOCKED**; decision matrix lists required evidence only. |

## Promotion gates (honest)

| Gate | Status |
| ---- | ------ |
| R1 advanced sampling → production | **Not passed** (research study exists; production not claimed) |
| R2 observatory / native grads | **Not passed** (experimental `exact_backend_gradient` + `smoothed_backend_gradient` on WSL; production `differentiation_api=False`; R2 promotion gate not claimed) |
| R3 frontiers publication-grade | **Partial host-local** — WSL live S4 → `batch_emulation=none` / publication_grade on that process; Windows native still `sequential_adapter` |
| R4 proof-carrying flagship | **Not passed** (multi-host **evidence ready** Windows+WSL sealed digests agree / `r4_multi_host_gate_ready=true`; production governed-hash + remote CI dispatch still open) |
| R5 CBF stage-4 RH | Checklist **green**; experimental short-horizon RH **available** (`experimental_rh_available`, `rh-v0.1.0`); full RH-MPC **not** implemented; domain **not** production-qualified |
| R6 training | **BLOCKED** |

## Track 1 probe results (`t1-probe-v0.2.1`)

Probe module: `conicshield.experimental.adapters.track1_probe`.

Attestation bar: **capability discovery alone is insufficient**. S4 requires a
live `NATIVE_MOREAU_BATCH` sample with sample hashes. S5 requires a live sidecar
hello with Moreau worker (honors `CONICSHIELD_WSL_PYTHON`). S6 requires productized
native differentiation callables (not research KKT/smoothed adapters).

| Capability | Landed in Track 1 surface? | Research attested? | Effect |
| ---------- | -------------------------- | ------------------ | ------ |
| S4 hetero-batch (`NATIVE_MOREAU_BATCH`) | Yes | **Yes on WSL** (`.venv-wsl-moreau`, Moreau 0.3.3, live `project_batch` hashes); **No on native Windows** | Frontiers watermark clears **only** when probe runs on an S4-attested host (WSL); Windows native keeps `sequential_adapter` |
| S5 sidecar | Yes | **Yes on Windows** with `CONICSHIELD_RESEARCH_SIDECAR_ENABLE=1` + `CONICSHIELD_WSL_PYTHON=.../.venv-wsl-moreau/bin/python` (hello + live project) | Research sidecar live path available under those env flags; still research-only / no production claim |
| S6-adjacent native exact/smoothed grads | Production `differentiation_api` still **False** | **Exact:** `CompiledSolver.backward`+`enable_grad` (WSL). **Smoothed:** softplus Moreau-QP experimental path (WSL). Research surface attested in probe extras; S6 Track-1 bar not cleared (prod flag). | Observatory calls live exact/smoothed on Linux/WSL with problem data; Windows UNAVAILABLE; S6 not cleared |

### Precise evidence (this machine)

1. **S4 WSL live sample:** `output/research/track1_probe_wsl_live/attestation.json` + `s4_live_sample.json` — `succeeded=true`, solver 0.3.3, sample hashes present; frontier attestation `batch_emulation=none`
2. **S4 Windows native:** `output/research/track1_probe_windows_live/attestation.json` — fail-closed (`windows_native_unsupported`); `reduce_watermarks=false`
3. **S5 Windows↔WSL sidecar:** same Windows attestation + `output/research/sidecar_smoke/live_project.json` / `direct_start.json`
4. **S6:** production `differentiation_api=false` (identity symbols absent). Research differentiation surface = `CompiledSolver.backward` + `enable_grad`. Experimental `exact_backend_gradient` and `smoothed_backend_gradient` (softplus ε-softening) implemented. Live verify script: `experiments/research_wave_verify/run_backend_gradients_live.py` → `output/research/backend_gradients_live/`. (WSL HCS timeout blocked re-run this session; prior Moreau 0.3.3 host remains the attestation target.) S6 Track-1 clear still requires productized production flag. `moreau.torch` is exact-autograd only (no vendor envelope).
5. **R4:** two real hosts aggregated — `output/research/multi_host/this_host/` (Windows) + `wsl_host/` (WSL); aggregate `output/research/multi_host/aggregate_win_wsl/platform_soak_aggregate.json` with `r4_multi_host_gate_ready=true`, `promotion_claim=false`, matching sealed digest `b794e6f3e4bcf595`. CI workflow `research-multi-host-soak.yml` exists locally but is **not on remote default branch** — `gh workflow run` → HTTP 404 (**user must commit + push**; no push this session).
6. **R6:** remains **BLOCKED**.

Operator runbook: `MULTI_HOST_SOAK_RUNBOOK.md` (Windows+WSL same-machine policy documented). CI matrix:
`.github/workflows/research-multi-host-soak.yml` (ubuntu+windows; dispatch blocked until workflow is on remote).

### Env flags that unlocked live S5

```text
CONICSHIELD_RESEARCH_SIDECAR_ENABLE=1
CONICSHIELD_RESEARCH_PROBE_WSL_MOREAU=1
CONICSHIELD_WSL_PYTHON=/mnt/c/Users/mateo/conicshield/.venv-wsl-moreau/bin/python
CONICSHIELD_SIDECAR_REQUIRE_MOREAU=1
```

System WSL `python3` lacks Moreau (PEP 668 / no package); vendor install lives in `.venv-wsl-moreau`.
Credentials were present in local `.env` (`GEMFURY_TOKEN`, `MOREAU_PIP_EXTRA_INDEX_URL`, `MOREAU_LICENSE_KEY`) and `~/.moreau/key` (WSL + Windows).

## Remaining Track 1 / vendor blockers

1. S4 hetero-batch on **native Windows** remains unsupported (use WSL for batch live path)
2. R4 production still needs governed-hash release wiring; push/dispatch `research-multi-host-soak` for independent CI runners (optional strengthening)
3. S6: productize production `differentiation_api` (identity symbols); experimental exact/smoothed backends ≠ full S6 clear
4. Optional: broader robotics generality beyond single CBF domain (out of scope by design)
5. Full RH-MPC / multi-robot / recursive feasibility certificates (explicitly out of experimental RH scope)
6. R6 remains **BLOCKED** (no training execution)
7. CI multi-host soak: workflow exists locally; **user must commit + push** before `gh workflow run` works (no push this session)

## Explicit non-claims

- Experimental modules are **not** in stable `conicshield.__all__`.
- No production API / claims / backends / release policy / governed benchmark changes.
- No R6 training execution.
- Native Windows is still not a Moreau execution host for S4 batch.
- `r4_multi_host_gate_ready=true` is **evidence-readiness only**, not a production R4 / flagship pass.
- CI ubuntu+windows soak matrix is **real-host evidence toward** R4 when run, not a production pass.
- Mock sidecar is **not** production attestation (live S5 here is research-attested only).
- Experimental RH is **not** full MPC and is **not** production-qualified.
- Research KKT/smoothed adapters are **not** native Moreau gradients.
- Experimental `exact_backend_gradient` / `smoothed_backend_gradient` ≠ production `differentiation_api` clearance.
- Watermark reduction is **host-local** (WSL S4-attested process only); not a global production claim.
