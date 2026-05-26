# Benchmark reports (committed examples)

Optional JSON reports that illustrate public benchmark evidence shapes. They are **not** live vendor timing claims unless regenerated on a licensed host and committed intentionally.

| File | Purpose |
|------|---------|
| [`batch_solve_report.example.json`](batch_solve_report.example.json) | Schema example for `scripts/batch_solve_report.py` output (`native_microbatch` vs `native_compiled_real_batch`) |

## Regenerate real batch evidence (licensed host)

```bash
python scripts/performance_benchmark.py --batch-size 4
python scripts/batch_solve_report.py output/performance_summary.json \
  --out benchmarks/reports/batch_solve_report.latest.json
```

Document the workflow in [`docs/SOLVER_PATHS_AND_BATCHING.md`](../../docs/SOLVER_PATHS_AND_BATCHING.md).
