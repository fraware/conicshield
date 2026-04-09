# Verification and stress-test plan

Operational **trust ladder** for ConicShield: commands, artifacts, and policies in this repository.

**Related:** [MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md), [PARITY_AND_FIXTURES.md](PARITY_AND_FIXTURES.md), [RELEASE_POLICY.md](RELEASE_POLICY.md), [DEVENV.md](DEVENV.md) (CI and pytest markers).

## Principles

The goal is not a single passing solve. The repository should show:

1. The environment can run reference or vendor mode as intended.
2. Solver output matches trusted references where claimed.
3. The native compiled path matches the governed reference stream on a frozen fixture.
4. Performance or CUDA claims are backed by measured artifacts.
5. Published benchmarks go through validation, parity where required, and governance gates.

**Do not:** benchmark before environment checks; trust native without parity; publish with a failed artifact gate; claim GPU benefit without measured evidence; claim differentiable behavior without gradient validation artifacts; bypass governance because a score looks good.

---

## Trust ladder (recommended order)

1. Environment — `python scripts/environment_check.py`
2. Smoke — `python scripts/smoke_check.py`
3. Reference correctness (minimal shield QP + optional conic suite) — `python scripts/reference_correctness_summary.py`
4. Native parity — `make parity-native-licensed`
5. Performance (vendor) — `python scripts/performance_benchmark.py`
6. Differentiation (optional) — `python scripts/differentiation_check.py`
7. Full tests / coverage — `make verify-extended`, `scripts/run_full_pytest.py`
8. Governance — `make audit`, `make dashboard`
9. Unified view — `python scripts/generate_trust_dashboard.py` (after `output/` artifacts exist)

---

## Four trust classes

| Class | Question |
|-------|----------|
| Environment | Right dependencies, solver, license, OS? |
| Solver | Correct math vs reference; native vs CVXPY parity? |
| Performance | Measured speedups; warm start; CUDA only when proven? |
| Governance | Bundles valid; gates green; publishable? |

---

## Layer map (repository status)

| Layer | Topic | Status | Primary command / artifact |
|-------|-----|--------|------------------------------|
| **A** | Environment | Partial | `scripts/environment_check.py` → `output/environment_check.json` |
| **B** | Smoke | Partial | `scripts/smoke_check.py` → `output/smoke_check.json`; `make smoke-solver` |
| **C** | Reference correctness | Implemented | `scripts/reference_correctness_summary.py` (conic suite vs CLARABEL/SCS + shield minimal); `tests/reference/test_reference_conic_correctness.py` (`pytest -m solver`) |
| **D** | Native parity | Implemented | `make parity-native-licensed`; `conicshield.parity.gates` |
| **E** | Performance | Implemented | `scripts/performance_benchmark.py` → `output/performance_*` |
| **F** | Differentiation | Optional | `scripts/differentiation_check.py` (shield FD + optional torch/jax micrograd probes) |
| **G** | Artifacts | Implemented | `validator_cli`, `scripts/artifact_validation_report.py` |
| **H** | Governance | Implemented | `make audit`, `make dashboard` |

---

## Layer A — Environment

**Goal:** Runtime can run public/reference or vendor mode.

**Artifacts:** `output/environment_check.json`, `output/environment_check.md`

**Pass:** Exit 0; JSON `status: ok` for the intended mode.

**Policy:** [MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md)

---

## Layer B — Smoke

**Goal:** Catch integration breakage before deep runs.

**Artifacts:** `output/smoke_check.json`, `output/smoke_check.md`

---

## Layer C — Reference correctness

**Goal:** Mathematical agreement with trusted references: **conic programs** (LP / QP / SOCP / mixed) with **Moreau vs CLARABEL** (or SCS fallback) on objectives and primals, plus a **minimal shield QP** check (CVXPY Moreau vs native) when both arms are available.

**Artifacts:** `output/reference_correctness_summary.json`, `output/reference_correctness_table.md`, `output/reference_correctness_report.md`

**Shared matrix:** `conicshield/reference_correctness/conic_suite.py` (used by the script and pytest so results do not drift).

---

## Layer D — Native parity

**Goal:** Native path matches frozen reference stream step-by-step.

**Artifacts:** `parity_summary.json`, `parity_steps.jsonl`, optional `parity_report.md` from `scripts/generate_parity_report.py`.

**Governance hook:** `python -m conicshield.governance.finalize_cli` accepts `--parity-summary-path` so `parity_gate` in `governance_status.json` (and, with `--sync-current-release`, `CURRENT.json`) reflects the same thresholds without requiring a `shielded-native-moreau` row in the benchmark `summary.json`. See [MAINTAINER_RUNBOOK.md](MAINTAINER_RUNBOOK.md).

**Vendor CI:** Manual workflow `vendor-ci-moreau` can upload a full verification bundle including parity outputs.

**Policy:** [PARITY_AND_FIXTURES.md](PARITY_AND_FIXTURES.md)

---

## Layer E — Performance

**Goal:** Measured cold vs warm, CVXPY vs native, optional CPU vs CUDA, and **decision-grade sweeps** when requested.

**Commands:** `python scripts/performance_benchmark.py` (single-scenario default). Use **`--sweep`** for `action_dim × conditioning × scenario` grids (default dims `4,8`; override with `--shield-action-dims`). Add **`--batch-sizes`** for both **sequential** native microbatch rows (`native_microbatch`) and **true** `CompiledSolver` batching (`native_compiled_real_batch`: one `solve(qs, bs)` per timed iteration), and **`--sweep-auto-tune`** to compare `NativeMoreauCompiledOptions.auto_tune`.

**Artifacts:** `output/performance_summary.json`, `output/performance_matrix.csv`, `output/performance_report.md`, optional `output/performance_latency.png`

**Schema:** `schemas/performance_summary.schema.json`

**Policy:** see [Performance](#performance-policy) below.

---

## Layer F — Differentiation

**Goal:** Gradients sane where differentiable paths are supported. Today: **finite-difference** slope on the reference shield projector (when MOREAU is installed) and optional **torch/jax micrograd vs FD** self-checks (`--probe-torch-jax`) that do not yet differentiate through the shield itself.

**Status:** Optional; not a governed gate in default CI. The report’s `status` field is **`deferred`** only when the reference stack is missing (`cvxpy`, `cp.MOREAU`, or a registered MOREAU solver). With a licensed solver install, the script runs the reference FD block and reports **`ok`** / **`partial`** (native FD requested but failed) rather than leaving Layer F as a stub.

**Artifacts:** `output/differentiation_summary.json`, `output/differentiation_report.md`

**Policy:** see [Differentiation](#differentiation-policy) below.

**Not yet in scope (defer explicit claims):** implicit differentiation / autograd **through** the shield stack (`NativeMoreauCompiledOptions.enable_grad`, `moreau` `backward()`, PyTorch/Jax binders on the real shield QP). The script’s torch/jax blocks remain toy quadrature checks. Adding vendor tests that compare `backward()` to finite differences on the same shield objective is the next step when differentiability is part of the public story.

---

## Layer G — Benchmark and artifact verification

**Goal:** Valid governed bundles.

**Commands:** `python -m conicshield.artifacts.validator_cli --run-dir ...`; `python scripts/artifact_validation_report.py --run-dir ...`

---

## Layer H — Governance and release

**Goal:** Publishable runs only under policy.

**Commands:** `make audit`, `make dashboard`, `python -m conicshield.governance.finalize_cli`, `python -m conicshield.governance.release_cli`, optional `finalize_cli --sync-current-release` to refresh release gate metadata for an already-published run; details in [MAINTAINER_RUNBOOK.md](MAINTAINER_RUNBOOK.md) and [RELEASE_POLICY.md](RELEASE_POLICY.md).

**Artifacts:** `output/governance_dashboard.json`, `output/governance_dashboard.md`

---

## Unified trust dashboard

**Command:** `python scripts/generate_trust_dashboard.py` (aggregates environment, smoke, reference, parity, performance, governance, differentiation when present).

**Outputs:** `output/trust_dashboard.html`, `output/trust_dashboard.md`

---

## Test layout

Pytest markers (`solver`, `requires_moreau`, `reference_correctness`, etc.) and `tests/reference/` for conic-vs-reference tests. See [tests/README.md](../tests/README.md).

---

## Performance policy

Speedup or crossover claims must come from maintained drivers and files under `output/` (for example `performance_summary.json`, `performance_matrix.csv` from `scripts/performance_benchmark.py`).

1. **Measured artifacts only.** No marketing-style speedups without reproducible commands and outputs.
2. **CUDA claims are conditional.** GPU benefit requires hardware where `moreau.device_available("cuda")` is true; document GPU model and driver in the report or metadata.
3. **CPU baseline always valid.** Public CI without CUDA must remain usable.
4. **Problem shape.** The shield path is primarily single-vector projection QPs; document limitations when a sweep does not apply.

**Forbidden:** CUDA speedup claimed from CPU-only runs or without recording device availability.

---

## Differentiation policy

Layer F is **optional** until a maintained differentiable path is validated with finite differences and integration tests. `NativeMoreauCompiledOptions.enable_grad` may exist for configuration; gradient correctness is not a default gate in public CI.

When implemented, validation should cover implicit differentiation and optional PyTorch/JAX paths as supported by the vendor stack. Artifacts: `output/differentiation_summary.json`, `output/differentiation_report.md` from `scripts/differentiation_check.py`.

---

## Metrics reference (for stress tests and reports)

Record what your scripts emit today; extend as coverage grows. Groupings:

- **Environment:** diagnostics, devices, license, optional deps, versions.
- **Solver:** status, objective, times, iterations, residuals, failure rates.
- **Reference correctness:** objective/primal deltas vs reference, status agreement, pass rate by family/size.
- **Parity:** action match, constraint match, distribution deltas, gate violations (see `parity.gates`).
- **Performance:** cold vs warm, throughput, device sweeps, speedup ratios.
- **Differentiation:** finite-diff vs analytic where applicable, NaN/inf rate, backward latency.
- **Governance:** artifact/parity/promotion gates, audit results, published vs candidate runs.

---

## Deliverables checklist

| Deliverable | Typical path |
|-------------|----------------|
| Environment | `output/environment_check.md` |
| Smoke | `output/smoke_check.md` |
| Reference correctness | `output/reference_correctness_table.md` |
| Native parity | `parity_summary.json` / `parity_report.md` |
| Artifact gate report | `output/artifact_validation_report.md` |
| Performance | `output/performance_report.md` |
| Differentiation | `output/differentiation_report.md` |
| Governance | `output/governance_dashboard.md` |
| Unified | `output/trust_dashboard.md` |

---

## See also

- [README.md](../README.md) — documentation map and quick commands
- [DEVENV.md](DEVENV.md) — CI matrix and markers
