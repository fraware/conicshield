# Solver paths and batching

Three production solve modes for the same QP family. Batch is a first-class API (`Backend.NATIVE_MOREAU_BATCH`), not a benchmark-only shortcut.

## Modes

| Mode | API | Use |
|------|-----|-----|
| Reference | `CVXPYMoreauProjector`, `cp.MOREAU` | Parity gold, `shielded-rules-plus-geometry` |
| Sequential native | `Backend.NATIVE_MOREAU`, `create_projector()` | Shield steps, warm-start |
| Compiled batch | `Backend.NATIVE_MOREAU_BATCH`, `create_batch_projector()` | Stacked proposals, throughput experiments |

Benchmark compares `native_microbatch` (Python loop, batch 1) vs `native_compiled_real_batch` only to judge mode 3.

```python
from conicshield.core.solver_factory import Backend, create_batch_projector, create_projector
```

Shield: `InterSimConicShield.project` (sequential) or `project_softmax_batch` (batch).

## Verification (licensed host)

```bash
python scripts/performance_benchmark.py --out-dir output/perf --repeats 5 --sweep --batch-sizes 4,8,16
python scripts/batch_solve_report.py --input output/perf/performance_summary.json --out output/perf/batch_solve_report.json
python scripts/check_batch_acceptance.py --tier viability --report output/perf/batch_solve_report.json
python scripts/check_batch_acceptance.py --tier throughput_advisory --report output/perf/batch_solve_report.json
```

## Acceptance tiers

Policy: [`batch_acceptance_policy.json`](../benchmarks/reports/batch_acceptance_policy.json) (v2).

| Tier | Threshold | CI |
|------|-----------|-----|
| **viability** | `speedup_ratio >= 0.98`, `any_row_meets`, CPU sweep 4/8/16 | **Required** (`reference-authority`, `vendor-ci-moreau`) |
| **throughput_advisory** | `>= 1.05`, `any_row_meets` | **Advisory** (log only) |

**Public narrative:** “Batch API is governed and viability-tested.” **Do not** claim universal batch speedup.

## Vendor regression tests

| Test | Proves |
|------|--------|
| `test_batched_compiled_matches_sequential_native` | Mode 3 ≈ mode 2 |
| `test_shield_native_softmax_batch` | Shield batch path |
| `test_solver_factory` | `NATIVE_MOREAU_BATCH` factory |

Full numeric parity: `vendor-ci-moreau` / `make test-vendor-moreau`.

## Governed bundles

`summary.json` records per-arm sequential metrics. Batch report is orthogonal throughput evidence, not a substitute for parity or promotion gates.

Flagship: [`HOST_REALISTIC_REFRESH_PROCEDURE.md`](HOST_REALISTIC_REFRESH_PROCEDURE.md). Tiers: [`REFERENCE_EVIDENCE_TIERS.md`](REFERENCE_EVIDENCE_TIERS.md).
