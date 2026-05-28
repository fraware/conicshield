# Benchmark reports (committed examples)

Optional JSON reports that illustrate public benchmark evidence shapes. They are **not** live vendor timing claims unless regenerated on a licensed host and committed intentionally.

| File | Purpose |
|------|---------|
| [`reference_authority_snapshot.json`](reference_authority_snapshot.json) | Committed flagship release alignment (`current_run_id`, gates, provenance); CI `--check` via `reference_authority_check` |
| [`batch_solve_report.example.json`](batch_solve_report.example.json) | v2 schema: comparisons + `batch_story` (`viability_only` / `throughput_win`) |

Regenerate snapshot after release or flagship bundle changes:

```bash
make reference-authority-snapshot
```

## Regenerate real batch evidence (licensed host)

```bash
python scripts/performance_benchmark.py --batch-size 4
python scripts/batch_solve_report.py output/performance_summary.json \
  --out benchmarks/reports/batch_solve_report.latest.json
```

Document the workflow in [`docs/SOLVER_PATHS_AND_BATCHING.md`](../../docs/SOLVER_PATHS_AND_BATCHING.md).
