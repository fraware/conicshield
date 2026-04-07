# Verification and stress-test plan (master)

**Canonical narrative (full specification, sections 1–22):** [VERIFICATION_MASTER_SPEC.md](VERIFICATION_MASTER_SPEC.md) — purpose, trust classes, checkpoints, layers A–H, metric inventory, stress matrix, test layout, thresholds, definition of done, and deliverables.

This document is the **operational verification ladder** for ConicShield. It maps abstract trust goals to **commands, artifacts, and policy files** in this repository.

**Related policy:** [MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md), [PERFORMANCE_BENCHMARKING_POLICY.md](PERFORMANCE_BENCHMARKING_POLICY.md), [NATIVE_PARITY_POLICY.md](NATIVE_PARITY_POLICY.md), [DIFFERENTIATION_VALIDATION_POLICY.md](DIFFERENTIATION_VALIDATION_POLICY.md), [RELEASE_POLICY.md](RELEASE_POLICY.md), [FIXTURE_POLICY.md](FIXTURE_POLICY.md). **Metric inventory (plan §13):** [METRICS_INVENTORY.md](METRICS_INVENTORY.md).

## Final outcome (trust ladder)

A new engineer should progress in order:

1. Environment validation — `python scripts/environment_check.py`
2. Smoke tests — `python scripts/smoke_check.py`
3. Reference correctness (minimal: shield QP) — `python scripts/reference_correctness_summary.py`
4. Native parity — `make parity-native-licensed`
5. Performance (vendor) — `python scripts/performance_benchmark.py`
6. Differentiation (optional) — `python scripts/differentiation_check.py`
7. Full pytest / coverage — `make verify-extended`, `scripts/run_full_pytest.py`
8. Governance — `make audit`, `make dashboard`
9. Unified view — `python scripts/generate_trust_dashboard.py` (after generating artifacts)

## Four trust classes

| Class | Question |
|-------|----------|
| Environment | Right deps, solver, license, OS policy? |
| Solver | Correct math vs reference; native vs CVXPY parity? |
| Performance | Measured speedups; warm start; CUDA only when proven? |
| Governance | Bundles valid; gates green; publishable? |

## Layer map (status)

| Layer | Topic | Status | Primary command / artifact |
|-------|-----|--------|------------------------------|
| **A** | Environment | **Partial** | `scripts/environment_check.py` → `output/environment_check.json` |
| **B** | Smoke | **Partial** | `scripts/smoke_check.py` → `output/smoke_check.json`; `make smoke-solver` |
| **C** | Reference correctness | **Partial** | Shield QP + `scripts/reference_correctness_summary.py`; vendor pytest `tests/reference/test_reference_conic_correctness.py` (LP/QP/SOCP/mixed-conic vs CLARABEL/SCS, `-m solver`) |
| **D** | Native parity | **Implemented** | `make parity-native-licensed`; `conicshield.parity.gates` |
| **E** | Performance | **Implemented** | `scripts/performance_benchmark.py` → `output/performance_*` |
| **F** | Differentiation | **Optional / stub** | `scripts/differentiation_check.py` — see [DIFFERENTIATION_VALIDATION_POLICY.md](DIFFERENTIATION_VALIDATION_POLICY.md) |
| **G** | Artifacts | **Implemented** | `conicshield.artifacts.validator_cli`; `scripts/artifact_validation_report.py` → `output/artifact_validation_report.{json,md}`; schema tests |
| **H** | Governance | **Implemented** | `make audit`, `make dashboard` |

---

## Layer A — Environment verification

**Goal:** Prove the runtime can run public/reference mode or vendor mode.

**Checks:** Python version, executable/prefix vs base prefix (venv hint), key imports, optional `torch` / `jax` probes, optional `moreau` probe, `cp.MOREAU`, license hints, `python -m moreau check` when available.

**Artifacts:** `output/environment_check.json`, `output/environment_check.md`

**Pass:** Script exits 0; JSON records `status: ok` for the intended mode.

**Policy:** [MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md)

---

## Layer B — Smoke verification

**Goal:** Catch integration breakage before deep runs.

**Public smoke:** Tiny CVXPY problem with CLARABEL (or SCS) inside `smoke_check`; artifact validator smoke; governance audit strict.

**Vendor smoke:** `solver_smoke_cli` (reference + native + warm-start second solve).

**Artifacts:** `output/smoke_check.json`, `output/smoke_check.md`

---

## Layer C — Reference correctness

**Goal:** Mathematical agreement with trusted references.

**Implemented:** Shield QP family — CVXPY+MOREAU vs native on the same `SafetySpec` where both run (`reference_correctness_summary.py`); **vendor pytest** `tests/reference/test_reference_conic_correctness.py` compares `cp.MOREAU` to CLARABEL (or SCS) on tiny LP, QP, SOCP, and mixed-conic instances (`pytest -m solver`).

**Artifacts:** `output/reference_correctness_summary.json`, `output/reference_correctness_table.md`, `output/reference_correctness_report.md` (same body as the table; plan §21 name)

---

## Layer D — Native parity

**Goal:** Native path matches frozen reference stream step-by-step.

**Protocol:** Frozen fixture `tests/fixtures/parity_reference/`; `conicshield.parity.cli`; gates in `parity.gates`.

**Artifacts:** `parity_summary.json`, `parity_steps.jsonl`, optional **`parity_report.md`** from `python scripts/generate_parity_report.py` (under `output/native_parity_local` when using Makefile, or any `--out-dir`).

**Vendor CI:** The **Vendor CI track** (`vendor-ci-moreau`) writes parity outputs into `/tmp/vendor_verification` together with env/smoke/reference/perf/trust; download artifact **`vendor_verification_bundle`**.

**Policy:** [NATIVE_PARITY_POLICY.md](NATIVE_PARITY_POLICY.md), [PARITY_FIXTURE_PROMOTION.md](PARITY_FIXTURE_PROMOTION.md)

---

## Layer E — Performance and scaling

**Goal:** Measured cold vs warm, CVXPY vs native, optional CPU vs CUDA when available.

**Artifacts:** `output/performance_summary.json`, `output/performance_matrix.csv`, `output/performance_report.md`

**Command:** `make perf-benchmark` or `python scripts/performance_benchmark.py`. Exits non-zero if no benchmark row completed (expected without vendor Moreau). Optional PNG: `output/performance_latency.png` (use `--no-plots` to skip).

**Schema:** `schemas/performance_summary.schema.json` (validated in `tests/test_performance_summary_schema.py`).

**Policy:** [PERFORMANCE_BENCHMARKING_POLICY.md](PERFORMANCE_BENCHMARKING_POLICY.md)

---

## Layer F — Differentiation

**Goal:** Gradients sane where differentiable paths are supported.

**Status:** Optional; see [DIFFERENTIATION_VALIDATION_POLICY.md](DIFFERENTIATION_VALIDATION_POLICY.md).

**Artifacts:** `output/differentiation_summary.json`, `output/differentiation_report.md`

---

## Layer G — Benchmark and artifact verification

**Goal:** Valid governed bundles.

**Commands:** `python -m conicshield.artifacts.validator_cli --run-dir ...`; `python scripts/artifact_validation_report.py --run-dir ...` (writes `artifact_validation_report.json` / `.md`); pytest for schemas and invariants.

---

## Layer H — Governance and release

**Goal:** Publishable runs only under gates.

**Commands:** `make audit`, `make dashboard`, release CLIs per [RELEASE_POLICY.md](RELEASE_POLICY.md).

**Artifacts:** `output/governance_dashboard.json`, `output/governance_dashboard.md`

---

## Metrics dashboard (single view)

**Command:** `python scripts/generate_trust_dashboard.py` (aggregates `environment_check`, `smoke_check`, `reference_correctness_summary`, `parity_summary` if present, `performance_summary`, `governance_dashboard`, `differentiation_summary`).

**Outputs:** `output/trust_dashboard.html`, `output/trust_dashboard.md`

---

## Test suite layout

The repository uses pytest markers (`reference_correctness`, `performance`, `solver`, …). **`tests/reference/`** holds Layer C conic-vs-reference tests; see [tests/README.md](../tests/README.md). Other subtrees from the master plan (§15) remain optional.

---

## Recommended thresholds

Parity thresholds are defined in `conicshield.parity.gates` (single source). Promotion and correctness tolerances for reference scripts are documented in the generated `reference_correctness_table.md`.

---

## Execution order (mandatory)

1. Environment checks green  
2. Smoke checks green  
3. Reference correctness (minimal)  
4. Native parity (vendor)  
5. Performance (vendor)  
6. Differentiation (optional)  
7. Governance artifacts  
8. Trust dashboard  

---

## Non-negotiables

- Never benchmark before environment validation.
- Never trust a native arm without parity green.
- Never publish a run with a red artifact gate.
- Never claim CUDA benefit without measured crossover evidence.
- Never claim differentiability without gradient validation artifacts.
- Never bypass governance because a number looks good.

---

## Deliverables checklist

| Deliverable | Path |
|-------------|------|
| Environment | `output/environment_check.md` |
| Smoke | `output/smoke_check.md` |
| Reference correctness | `output/reference_correctness_table.md`, `output/reference_correctness_report.md` |
| Native parity | `output/native_parity_local/parity_summary.json` (or custom `--out-dir`); `parity_report.md` via `generate_parity_report.py` |
| Artifact gate report | `output/artifact_validation_report.md` |
| Performance | `output/performance_report.md` |
| Differentiation | `output/differentiation_report.md` |
| Governance | `output/governance_dashboard.md` |
| Unified | `output/trust_dashboard.md` |

---

## See also

- [README.md](../README.md) — full documentation map and quick verification commands
- [METRICS_INVENTORY.md](METRICS_INVENTORY.md) — §13 metric inventory
- [DEVENV.md](DEVENV.md) — CI and pytest markers
