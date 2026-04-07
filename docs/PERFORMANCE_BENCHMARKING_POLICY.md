# Performance benchmarking policy

## Purpose

Define when ConicShield may claim **performance advantages** (compiled native vs CVXPY reference, warm start, CUDA vs CPU). This document complements the master plan in [VERIFICATION_AND_STRESS_TEST_PLAN.md](VERIFICATION_AND_STRESS_TEST_PLAN.md).

## Principles

1. **Measured artifacts only.** Speedup or crossover claims require written outputs under `output/` (for example `performance_summary.json`, `performance_matrix.csv`) from the maintained benchmark driver (`scripts/performance_benchmark.py`).
2. **CUDA claims are conditional.** GPU benefit must be demonstrated on hardware where `moreau.device_available("cuda")` is true; document GPU model and driver in the report or run metadata.
3. **CPU baseline is always valid.** Public CI and contributors without CUDA must not be blocked; performance verification is an **optional** layer for vendor environments.
4. **Problem shape matters.** The shield path is primarily **single-vector projection** QPs; batching may be limited by API surface. Document limitations in the performance report when a sweep is not applicable.

## Allowed claims

| Claim | Required evidence |
|-------|-------------------|
| Native faster than CVXPY on repeated fixed-structure solves | `performance_matrix.csv` rows with steady-state ratio and workload description |
| Warm start reduces latency or iterations | Before/after columns in the matrix or `performance_summary.json` fields |
| CUDA faster than CPU in regime R | Device sweep rows for R; no claim if only CPU was measured |

## Forbidden claims

- Marketing-style speedups without reproducible commands and artifacts.
- CUDA speedup measured on CPU-only machines or without recording device availability failures.

## Artifacts (machine output)

- `output/performance_summary.json` — must validate against [schemas/performance_summary.schema.json](../schemas/performance_summary.schema.json); contract tested in `tests/test_performance_summary_schema.py`.
- `output/performance_matrix.csv`, `output/performance_report.md`
- `output/performance_latency.png` — optional bar chart (mean and p95 per row) when `matplotlib` is installed and `--no-plots` is not passed.

## Related

- [MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md)
- Makefile: `make dashboard` (governance); performance artifacts are separate from governance dashboard JSON.
