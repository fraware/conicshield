# Track 1 completion report

Production stabilization track (S0–S8) for ConicShield solver correctness,
verification, packaging, Windows qualification, CI governance, and decision-grade
benchmarks.

## 1. Starting and ending commits

| | SHA | Notes |
|--|-----|-------|
| **Start (S0 baseline)** | `180bed7411f3146205b65b4258e6711c786c9f6f` (`180bed7`) | `origin/main` tip at track start; see [`starting_commit.json`](starting_commit.json) |
| **Integration tip after S7** | `d7f1da49b893557dd72e5d55fbc6018d79eb255e` (`d7f1da4`) | Merge of PR #8 (S7) into `engineering/stabilization-moreau` |
| **S8 branch tip** | `34f9904` (PR #9 tip; implement commit `296f49c`) | `engineering/s8-benchmark-qualification-release` |

Long-lived integration branch: `engineering/stabilization-moreau`.

## 2. Closed deficiency ledger

All tracked P0 and P1 ledger items are **fixed** in [`issue_ledger.json`](issue_ledger.json):

| ID | Severity | WP | Fix PR |
|----|----------|----|--------|
| CS-SOLVER-001 | P0 | S1 | #2 |
| CS-SOLVER-002 | P0 | S2 | #3 |
| CS-SOLVER-003 | P0 | S7 | #8 |
| CS-SOLVER-004 | P0 | S3 | #4 |
| CS-SOLVER-005 | P0 | S1 | #2 |
| CS-SOLVER-006 | P0 | S5 | #6 |
| CS-SOLVER-007 | P0 | S7 | #8 |
| CS-SOLVER-101–111 | P1 | S2–S6 | #3–#7 |

## 3. Architecture description

Stabilized architecture (Track 1):

1. **SafetySpec schema** → canonical `ShieldQPData` with singleton constraint kinds and fail-safe policy.
2. **Structural compiler** (`ConstraintTopology`, `ParameterLayout`, `CompiledShieldTemplate`) with structural fingerprints and numeric buffers.
3. **Backends** via `Backend` enum: `AUTO` / `PUBLIC_CLARABEL` / `PUBLIC_SCS` / `CVXPY_MOREAU` / `NATIVE_MOREAU` / `NATIVE_MOREAU_BATCH`.
4. **Verified release pipeline** (S2): status normalization → residual checks → release classification → optional fallback ladder → evidence on `ProjectionResult`.
5. **Episode / concurrency contracts**: `StatefulProjectorProtocol.reset_state`, `ConcurrencyModel`.
6. **Windows modes**: public native Windows; WSL-native repo; Moreau sidecar (stdio NDJSON) as qualification scaffolding.
7. **Governance**: vendor evidence gates, read-only verify paths, solver-stack policy, published-run integrity.

## 4. Mathematical semantics of every supported constraint

Productized constraint kinds (must pass residual verification before release):

| Kind | Semantics |
|------|-----------|
| `simplex` | \(\sum_i x_i = total\) with \(total > 0\) (default \(1\)) |
| `box` | \(lower_i \le x_i \le upper_i\) for each coordinate (finite bounds) |
| `rate` | \(|x_i - x^{\mathrm{prev}}_i| \le max\_delta_i\) (nonnegative; \(+\infty\) allowed) |
| `turn_feasibility` | \(x_i = 0\) for \(i \notin allowed\_actions\); empty allowed set requires explicit `fail_safe_policy` |

Not productized (schema may exist; **not** claimable): `progress`, `clearance`.

Native and CVXPY Moreau paths must encode the same declared lower/upper bounds (CS-SOLVER-001).

## 5. Status and release policy

- Raw solver statuses map to `CanonicalSolverStatus`.
- `ReleaseDecision` gates acceptance (`accepted_primary`, fallback acceptance, or reject).
- Inaccurate / iteration-limit / timeout outcomes follow the declared policy; unverified actions are not released.
- Evidence fields on `ProjectionResult`: `canonical_status`, `release_decision`, `verification`, `solver_provenance`, `fallback_history`.

## 6. Fallback and fail-safe policy

- Spec-level `FailSafePolicy`: `reject`, `uniform_admissible`, `clamped_proposed` (synthesized actions still require residual verification).
- Runtime fallback ladder records `FallbackAttempt` history; empty admissible sets fail closed when policy is `reject`.
- Windows sidecar worker death uses declared `FallbackPolicy` (default public Clarabel); never releases without verification.

## 7. Concurrency model

Declared `ConcurrencyModel` values:

- `instance_confined` (default expectation for stateful projectors)
- `lock_protected`
- `pooled_exclusive_checkout`
- `stateless`

S8 concurrent benchmark uses one projector instance per worker task.

## 8. Cache and warm-start lifecycle

- Structural fingerprint keys cache compiled structure; numeric parameters may change without full rebuild when layout matches.
- Episode reset (`reset_episode` / `reset_state`) clears warm starts so first-solve matches a fresh projector (CS-SOLVER-004).
- Batch path reports `cache_status` and `structural_fingerprint` on `BatchProjectionResult`.

## 9. Backend qualification matrix

| Backend | This host (Windows S8 run) | Qualification stance |
|---------|----------------------------|----------------------|
| `PUBLIC_CLARABEL` | **Measured** | Windows public mode qualified |
| `PUBLIC_SCS` | **Measured** (tight rate may fail-closed more often) | Public alternative |
| `AUTO` | **Measured** → public | Never selects vendor from importability |
| `CVXPY_MOREAU` | **NOT_RUN** | Requires licensed Moreau on supported OS |
| `NATIVE_MOREAU` | **NOT_RUN** | Same; not supported on native Windows |
| `NATIVE_MOREAU_BATCH` | **NOT_RUN** | Heterogeneous batch needs vendor |

## 10. Windows qualification matrix

| Mode | Declared qualification | Production claim? |
|------|------------------------|-------------------|
| `windows_public` | Required CI (`.github/workflows/windows-ci.yml`) + local doctor/public solves | Yes (public backends only) |
| `windows_wsl_native_repo` | Path helpers + optional local vendor | Vendor optional |
| `windows_moreau_sidecar` | Protocol/client/worker scaffolding + tests; **not** live Moreau attestation on this host | **No** — scaffolding / public CI only |

Native Moreau-on-Windows is **not** a qualified mode.

## 11. Solver and package provenance

Capture via `conicshield solver-doctor --json`. S8 reports embed a doctor subset under
`benchmarks/reports/s8_qualification/decision_grade_summary.json` → `provenance.solver_doctor_subset`
(commit, distributions, capabilities evidence, CUDA, platform notes). Secrets are redacted.

## 12. Test execution and skip counts

Stabilization regression package: `tests/stabilization/` (P0/P1 + S7 governance).

Vendor-required lane (`CONICSHIELD_VENDOR_REQUIRED=1`) is designed so capability skips become failures in vendor CI. On this Windows host, licensed Moreau attestation is **not** runnable; do not treat local public green as vendor proof.

Exact skip counts vary by environment markers (`solver`, `requires_moreau`, Windows sidecar availability). Record CI JUnit / evidence gate artifacts for authoritative vendor counts.

## 13. Benchmark results

Committed decision-grade artifacts:

- [`benchmarks/reports/s8_qualification/decision_grade_summary.json`](../../benchmarks/reports/s8_qualification/decision_grade_summary.json)
- [`benchmarks/reports/s8_qualification/decision_grade_report.md`](../../benchmarks/reports/s8_qualification/decision_grade_report.md)

Summary from the committed Windows host run (commit `d7f1da4` provenance):

- Public Clarabel / SCS / AUTO: measured with p50/p95/p99/max, setup/solve/verification decomposition, concurrent callers, warm sequences, episode resets, batch micro-sizes, fail-closed stress cells.
- Moreau CVXPY / native / heterogeneous batch / CUDA / live sidecar IPC: **NOT_RUN** with explicit reasons.
- Throughput / tail claims for vendor paths are **not** published from this host.

Reproduce:

```powershell
py -3 scripts/decision_grade_benchmark.py --out-dir benchmarks/reports/s8_qualification
# or
py -3 scripts/performance_benchmark.py --decision-grade --out-dir benchmarks/reports/s8_qualification
```

## 14. Remaining limitations

1. Licensed vendor Moreau CI attestation requires Gemfury / license secrets; local Windows cannot import Moreau.
2. Flagship full-refresh cadence (~35–55d policy) may keep `make verify-v1-lock` cadence checks red until a licensed refresh.
3. WSL sidecar is **not** production-ready; no live Moreau worker attestation on this host.
4. Public latency numbers are host-specific; do not generalize to vendor or CUDA.
5. `progress` / `clearance` remain unimplemented as product constraints.
6. Batch public narrative remains **viability_only** unless governed reports show throughput tier.

## 15. Exact public claims now justified

See [`docs/PUBLIC_CLAIMS.md`](../PUBLIC_CLAIMS.md). Track 1 justifies:

- Convex shield with `simplex`, `turn_feasibility`, `box`, `rate`.
- Independent residual/status verification before release.
- Public Clarabel/SCS/AUTO on Windows without vendor credentials.
- Native sequential + true batched compiled APIs exist (vendor OS + license required to execute).
- Published v1 bundles remain verifiable; runtime qualification is a **separate** artifact from bundle authority.
- Episode reset / concurrency contracts exist and are tested.
- Vendor CI **wiring** rejects skip-based false confidence when secrets are present.

Track 1 does **not** justify: native Windows Moreau; universal batch speedups; live sidecar production readiness; CUDA performance; Moreau latency from this host.
