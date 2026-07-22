# Production qualification report (S8)

Runtime qualification for Track 1 stabilization. This report is **separate** from
published v1 reference bundles (`host-realistic-20260525` and friends), which remain
the governed artifact authority.

## Scope

| Item | Value |
|------|--------|
| Integration branch | `engineering/stabilization-moreau` |
| S7 merge SHA | `d7f1da49b893557dd72e5d55fbc6018d79eb255e` |
| Work package | S8 decision-grade benchmarks + release gate evaluation |
| Machine report | `benchmarks/reports/s8_qualification/` |

## Environment provenance

Embedded in `decision_grade_summary.json` → `provenance` (solver-doctor subset:
OS, arch, distributions, Moreau identity/import error, capabilities evidence,
CUDA, commit).

This S8 capture was produced on **native Windows 11 / Python 3.12** where Moreau
import fails by platform policy.

## Workload matrix coverage

| Dimension | Result on this host |
|-----------|---------------------|
| Action dims (4, 8) | Measured (public) |
| Constraint kinds | simplex/turn/box/rate exercised; progress/clearance not productized |
| Well / ill conditioning | Measured; SCS may fail-closed under tight rate (recorded) |
| Cold starts | Measured |
| Warm sequences | Measured |
| Episode resets | Measured |
| Heterogeneous batch | NOT_RUN (licensed Moreau) |
| Batch sizes (microbatch) | Measured (public sequential loop) |
| Structural cache hit/miss | NOT_RUN (native) |
| Backend comparisons | Public ok; Moreau NOT_RUN |
| CPU algo / auto device | NOT_RUN (native) |
| CUDA | NOT_RUN |
| Windows sidecar overhead | NOT_RUN (no live Moreau worker attestation) |
| Worker restart | NOT_RUN |
| Concurrent callers | Measured (public, instance-confined) |
| Deadlines / max_iter stress | Measured (fail-closed ok) |
| Infeasible cases | Measured (construction/runtime fail-closed) |
| Numerical failure injection | Measured (NaN fail-closed) |
| p50/p95/p99/max | Reported for measured cells |
| Setup vs solve vs verification vs e2e | Reported when instrumentation present |
| Throughput / memory | Throughput on microbatch + concurrent; RSS when available |
| Failures / retries / fallbacks | Recorded on cells |

## Timing decomposition

For each successful sample:

- `e2e_wall_sec` — wall clock around `project`
- `solver_time_sec` — backend-reported solve time
- `setup_time_sec` / `construction_time_sec` — when provided
- `verification_time_sec` — estimated as residual wall after subtracting reported components
- `ipc_time_sec` — sidecar only (null in-process)

## Comparison arms

| Arm | Status |
|-----|--------|
| Public reference (Clarabel) | Measured |
| Public SCS | Measured |
| Moreau CVXPY | NOT_RUN — Moreau unsupported on native Windows / no license lane here |
| Moreau native | NOT_RUN |
| Heterogeneous batch | NOT_RUN |
| Windows sidecar | NOT_RUN — scaffolding only; not production-ready |

## Statistical uncertainty

Where `n >= 2` measured samples exist, `stderr_of_mean` is reported on latency
distributions. Do not treat single-sample stress cells as distributional claims.

## Release gate evaluation (honest)

See [`RELEASE_GATE_EVALUATION.md`](RELEASE_GATE_EVALUATION.md). **Integration must
not merge to `main` solely on this host’s public green.**

## Claims discipline

Performance claims in public docs must cite these committed reports and label
NOT_RUN limitations. Microbenchmark-only numbers without this matrix are not
decision-grade.
