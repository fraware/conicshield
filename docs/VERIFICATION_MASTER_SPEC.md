# ConicShield / Moreau Verification and Stress Test Plan (canonical)

This document is the **full narrative specification** for verification, validation, benchmarking, and stress testing. For **repository-specific commands and status**, see [VERIFICATION_AND_STRESS_TEST_PLAN.md](VERIFICATION_AND_STRESS_TEST_PLAN.md).

---

## Purpose

This document defines the full verification, validation, benchmarking, and stress-testing plan for the repository.

The goal is not merely to show that a solve works. The goal is to prove that the repository:

1. installs and initializes correctly in the intended environments,
2. computes correct solutions relative to trusted references,
3. exercises the full Moreau capability surface that the repository claims to support,
4. demonstrates performance advantages where those advantages are expected,
5. supports governed publication of benchmark results, and
6. remains trustworthy under regression, parity, and release controls.

This file is an operational plan for engineering execution. It should be used by maintainers, systems engineers, optimization engineers, ML engineers, infra engineers, and technical leads as the reference testing and benchmark policy.

---

## 1. Final outcome we are trying to reach

The repository is considered successful only when it behaves as a **trust ladder**, not just a codebase.

A new engineer should be able to move through:

1. environment validation  
2. smoke tests  
3. reference correctness validation  
4. native compiled parity validation  
5. warm-start and batching performance validation  
6. differentiation validation  
7. benchmark generation  
8. governance finalization  
9. dashboard and audit visibility  
10. release publication under controlled governance  

If any one of these layers is missing or weak, the repository is not yet at the intended final vision.

---

## 2. The four classes of trust

All verification work belongs to one of four trust classes.

### 2.1 Environment trust

- Is the right dependency installed?  
- Is the right solver backend available?  
- Is the license present?  
- Is the runtime environment supported?  

### 2.2 Solver trust

- Does Moreau produce the same math as the trusted reference path?  
- Do CVXPY/Moreau and native compiled Moreau agree?  
- Are gradients and batched semantics correct?  

### 2.3 Performance trust

- Does the compiled path outperform the reference path where expected?  
- Do warm starts help? Does batching help?  
- Does device selection behave sensibly? Does CUDA help where it should?  

### 2.4 Governance trust

- Is every benchmark bundle valid?  
- Is parity green where required? Is promotion green where required?  
- Is the current published result governed and auditable?  

---

## 3. Verification layers

The repository should enforce verification in layers:

- **Layer A** — Environment verification  
- **Layer B** — Smoke verification  
- **Layer C** — Reference correctness verification  
- **Layer D** — Native parity verification  
- **Layer E** — Performance and scaling verification  
- **Layer F** — Differentiation verification  
- **Layer G** — Benchmark and artifact verification  
- **Layer H** — Governance and release verification  

All layers must exist for serious runs. None may be skipped without explicit policy exception.

---

## 4. The practical question: “How do I know it works?”

Require **five green checkpoints** before claiming the repo works in a meaningful sense:

1. **Environment is real** — correct environment boots; diagnostics pass; intended devices visible; vendor mode can solve when requested.  
2. **Reference correctness is real** — CVXPY path with Moreau agrees with a trusted public solver on LP, QP, SOCP, and mixed-conic cases (within declared tolerances).  
3. **Native path is trustworthy** — native compiled Moreau matches the governed reference path on the same frozen input stream.  
4. **Performance claims are earned** — warm starts help; batching helps; compiled path improves repeated fixed-structure workloads; device selection validated empirically.  
5. **Governance is green** — run bundles validate; parity and promotion green where required; audit clean; dashboard reflects the truth.  

---

## 5. Layer A — Environment verification

**Goal:** Prove that the runtime environment can run public/reference mode, vendor CPU mode, and vendor CUDA mode where applicable.

**Required checks:** Python and venv; base imports (numpy, scipy, cvxpy, cvxpylayers, jsonschema, pytest, pydantic); Moreau availability in vendor mode (`import moreau`, `python -m moreau check`, devices); license behavior; optional PyTorch/JAX paths.

**Output artifacts:** `environment_check.json`, `environment_check.md` (in this repo: `scripts/environment_check.py`).

**Pass / fail:** Public mode passes with public deps and smoke; vendor mode requires Moreau check, simple solve, visible devices, and valid license when vendor runs are marked.

---

## 6. Layer B — Smoke verification

**Goal:** Catch obvious integration breakage before correctness or benchmarking.

**Required tests:** Minimal public smoke (tiny CVXPY + CLARABEL/SCS; artifact validation smoke; governance audit smoke); minimal vendor smoke (Moreau solve, `cp.MOREAU`, native compiled solve, warm-start sequence); optional framework smoke (PyTorch/JAX).

**Output artifacts:** `smoke_check.json`, `smoke_check.md`.

---

## 7. Layer C — Reference correctness verification

**Goal:** Prove that the high-level Moreau path is mathematically correct relative to trusted public solvers.

**Required problem families:** LP, QP, SOCP, mixed conic where relevant.

**Required comparisons:** For each family, solve with Moreau through CVXPY and with a trusted reference solver; compare objective, primal, status, feasibility residuals within declared tolerances.

**Variants:** Well-conditioned and moderately ill-conditioned; sparse and dense; tiny and medium; edge cases that activate constraints differently.

**Output artifacts:** `reference_correctness_summary.json`, `reference_correctness_table.md`, `reference_correctness_report.md` (alias for the table), per-family failure logs, optional plots.

**Repository mapping:** Shield-QP summary script plus `tests/reference/test_reference_conic_correctness.py` (vendor-marked) for LP/QP/SOCP/mixed-conic vs CLARABEL or SCS.

---

## 8. Layer D — Native compiled parity verification

**Goal:** Prove that the native compiled Moreau implementation faithfully reproduces the governed reference path on the same frozen input stream.

**Protocol:** Frozen reference stream (Q-values, action ordering, shield context, proposed/corrected distributions, chosen action, constraints, objective if stored); native replay; step-by-step comparison of actions, distributions, intervention norm, constraints, objective, status.

**Gates (baseline):** Action match rate 1.0; active-constraint match rate ≥ 0.999; max corrected L∞ ≤ 1e-5; p95 corrected L∞ ≤ 1e-6; max corrected L2 ≤ 1e-5 (see `conicshield.parity.gates`).

**Output artifacts:** `parity_summary.json`, `parity_steps.jsonl`, optional `parity_report.md` (`scripts/generate_parity_report.py`).

---

## 9. Layer E — Performance and scaling verification

**Goal:** Prove that performance claims are measured and that Moreau is used in regimes where it is valuable.

**Dimensions:** Cold vs warm; CVXPY vs native paths; CPU vs CUDA vs auto; batch size; problem scale (n, m, m/n, sparsity, cones); workload type (synthetic, shared-structure, sequential, replayed shield).

**Core metrics:** Solve/setup/construction time; iterations; p50/p95/p99 latency; throughput; batch efficiency; compiled-vs-reference speedup; cold-vs-warm speedup; device crossover metrics where CUDA is in scope.

**Output artifacts:** `performance_summary.json`, `performance_matrix.csv`, `performance_report.md`, optional plots (`scripts/performance_benchmark.py`).

**Policy:** [PERFORMANCE_BENCHMARKING_POLICY.md](PERFORMANCE_BENCHMARKING_POLICY.md).

---

## 10. Layer F — Differentiation verification

**Goal:** Prove that Moreau-backed solve layers are usable in learning loops.

**Paths:** Core implicit differentiation; PyTorch autograd; JAX (grad, vmap, jit) if in scope; smoothed differentiation as experimental if supported.

**Metrics:** Gradient finite-rate; NaN/inf rate; finite-difference vs analytic mismatch; backward latency; stability near active-set changes.

**Output artifacts:** `differentiation_summary.json`, `differentiation_report.md`.

**Policy:** [DIFFERENTIATION_VALIDATION_POLICY.md](DIFFERENTIATION_VALIDATION_POLICY.md).

---

## 11. Layer G — Benchmark and artifact verification

**Goal:** Prove that every serious run can be turned into a complete, valid, governed artifact bundle.

**Required bundle contents (conceptual):** config, schemas, summary, episodes, transition bank, benchmark card, governance status, provenance as required by policy.

**Validations:** Schema validation; cross-field invariants; bundle completeness; fixture policy when fixtures change.

**Output artifacts:** `artifact_validation_report.json`, optional `artifact_validation_report.md` (`scripts/artifact_validation_report.py`).

---

## 12. Layer H — Governance and release verification

**Goal:** Prove that a run is publishable under benchmark governance.

**Gates:** Artifact gate; fixture gate when relevant; parity gate when native endorsement is requested; promotion gate; review-lock and family compatibility for same-family replacement.

**Output artifacts:** `governance_status.json`, release dry-run results, audit pass, dashboard visibility.

**Commands in repo:** `make audit`, `make dashboard`, release policy CLIs.

---

## 13. Full metric inventory (summary)

The complete enumerated list (§13.1–§13.15) lives in **[METRICS_INVENTORY.md](METRICS_INVENTORY.md)**. See the operational plan and policy docs for what this repository records today versus roadmap items.

---

## 14. Minimum dashboards

Expose at minimum: environment; correctness; native parity; performance; differentiation; governance. **Unified view in this repo:** `scripts/generate_trust_dashboard.py` → `output/trust_dashboard.html` and `.md`.

---

## 15. The exact test suite layout

The specification recommends physical subtrees under `tests/` (environment, smoke, reference, native, performance, diff, artifacts, governance). **This repository** uses **pytest markers** (`solver`, `requires_moreau`, `reference_correctness`, etc.) and has started **`tests/reference/`** for Layer C conic correctness; other tests remain under `tests/` until further split. See **[tests/README.md](../tests/README.md)**.

---

## 16. Recommended thresholds

- **Correctness:** Objective and primal deltas within declared tolerance; residuals below threshold; status agreement except tolerated edge cases.  
- **Native parity:** As in §8 / `conicshield.parity.gates`.  
- **Promotion:** Rules-only and geometry arms per benchmark policy; native solve-failure rate and latency gates when native promotion is the goal.  
- **Differentiation:** FD mismatch tolerance; no systematic NaNs/infs; acceptable backward latency for target workloads.  

---

## 17. Stress-test matrix

Stress Moreau by sweeping: problem family (LP, QP, SOCP, mixed); API path (CVXPY, native single, native compiled); solve mode (cold, warm); batch size; device (CPU, CUDA, auto); framework (core, PyTorch, JAX); workload type (synthetic, shield replay, shared-structure, sequential). Use this matrix for capability coverage, not a single happy-path solve.

---

## 18. Order of execution

1. Environment checks green.  
2. Smoke tests green.  
3. CVXPY-vs-reference correctness green.  
4. Native parity green.  
5. Warm-start and batching performance measured.  
6. CPU vs CUDA crossover measured where applicable.  
7. Differentiation paths validated.  
8. Full governed benchmark bundles generated.  
9. Governance status finalized.  
10. Publish only through the governed release path.  

---

## 19. Definition of done

The repository reaches the intended vision when: public and vendor modes work; CVXPY/Moreau matches trusted references; native compiled matches governed reference; capability coverage includes single/batched/warm-start/device/CVXPY families/differentiation/diagnostics; performance claims are measured; governance bundles validate; audit passes; dashboard is accurate; native endorsement is parity-gated; publication is governed.

---

## 20. Non-negotiable engineering rules

- Never benchmark before environment validation.  
- Never trust a native arm without parity.  
- Never publish a run with a red artifact gate.  
- Never confuse task changes with same-family score updates.  
- Never count “it runs once” as capability coverage.  
- Never claim CUDA benefit without measured crossover evidence.  
- Never claim differentiability without gradient validation.  
- Never bypass governance because a number looks good.  

---

## 21. Deliverables the team should produce

At the end of the verification campaign:

- `environment_check.md`  
- `smoke_check.md`  
- `reference_correctness_report` / table (and extended pytest logs for conic suites when run)  
- `native_parity_report` / parity summary and steps  
- `performance_report.md`  
- `differentiation_report.md`  
- governed benchmark run bundles  
- green governance audit  
- updated dashboard  
- at least one officially published, governed benchmark family state (per release policy)  

---

## 22. Recommended supporting docs

Under `docs/`:

- `VERIFICATION_AND_STRESS_TEST_PLAN.md` — operational ladder and repo mapping (this repo’s master index).  
- `VERIFICATION_MASTER_SPEC.md` — this canonical narrative (sections 1–22).  
- `METRICS_INVENTORY.md` — full §13 metric list (roadmap vs implemented).  
- `PERFORMANCE_BENCHMARKING_POLICY.md`  
- `NATIVE_PARITY_POLICY.md`  
- `DIFFERENTIATION_VALIDATION_POLICY.md`  

Add or extend narrower policies as the program matures.

**Repository index:** [README.md](../README.md) (*Documentation map*) lists all policies and runbooks in one place.
