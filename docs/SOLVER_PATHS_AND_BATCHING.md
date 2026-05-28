# Solver paths and batching

Three **separate** production solve modes for the same shield QP family. Batch is a first-class API (`Backend.NATIVE_MOREAU_BATCH`), not a benchmark-only shortcut.

## Mode 1 — Reference CVXPY Moreau

| | |
|--|--|
| API | `CVXPYMoreauProjector`, `cp.MOREAU` |
| Role | Parity gold, `shielded-rules-plus-geometry` arm |
| When to use | Establishing reference semantics, governance replay |

```python
from conicshield.core.solver_factory import Backend, create_projector

projector = create_projector(spec, backend=Backend.CVXPY_MOREAU)
```

## Mode 2 — Native compiled sequential reuse

| | |
|--|--|
| API | `Backend.NATIVE_MOREAU`, `NativeMoreauCompiledProjector` |
| Role | Per-step shield calls with warm-start reuse |
| When to use | RL stepping, parity against reference |

Benchmark label: `native_microbatch` (Python loop calling `project` with `batch_size` proposals — **not** the same as mode 3).

## Mode 3 — Native true batched compiled solve

| | |
|--|--|
| API | `Backend.NATIVE_MOREAU_BATCH`, `NativeMoreauCompiledBatchProjector` |
| Role | One `CompiledSolver.solve(qs, bs)` per batch |
| When to use | Throughput experiments, stacked proposals |

```python
from conicshield.core.solver_factory import Backend, create_batch_projector

batch = create_batch_projector(spec, backend=Backend.NATIVE_MOREAU_BATCH)
out = batch.project_batch(proposed_batch, previous_action)  # (K, n)
```

Benchmark label: `native_compiled_real_batch`.

**Governance test:** `test_batched_compiled_matches_sequential_native` (vendor) — mode 3 matches mode 2 on the same inputs. **CI (public):** `tests/governance/test_native_batch_report_contract.py` — report schema + `batch_story` honesty.

## Benchmark and reports

```bash
python scripts/performance_benchmark.py --out-dir output/perf --repeats 5 --sweep --batch-sizes 4,8,16
python scripts/batch_solve_report.py --input output/perf/performance_summary.json --out output/perf/batch_solve_report.json
```

`batch_solve_report.json` (v2) always includes:

| Field | Meaning |
|-------|---------|
| `comparisons[]` | `native_microbatch` vs `native_compiled_real_batch` per scenario |
| `speedup_ratio` | `mean_sec_sequential / mean_sec_batched` |
| `batch_story` | `viability_only` \| `throughput_win` \| `below_viability` |
| `batch_story_advisory` | Human-readable claim guardrail |

## Acceptance tiers

Policy: [`batch_acceptance_policy.json`](../benchmarks/reports/batch_acceptance_policy.json) (v2).

| Tier | Threshold | CI |
|------|-----------|-----|
| **viability** | `speedup_ratio >= 0.98`, `any_row_meets` | **Required** |
| **throughput_advisory** | `>= 1.05` | **Advisory only** |

### Public narrative (binding)

- **Say:** “True batched compiled solve path exists, is governed, and is viability-tested.”
- **Do not say:** “Batch is always faster” or “universal throughput win” unless `batch_story` is `throughput_win` **and** you have scenario coverage beyond micro-sweeps.

## Shield integration

`InterSimConicShield.project` — sequential (mode 2).  
`InterSimConicShield.project_softmax_batch` — batch path (mode 3).

Flagship refresh: [`HOST_REALISTIC_REFRESH_PROCEDURE.md`](HOST_REALISTIC_REFRESH_PROCEDURE.md).
