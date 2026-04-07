# Benchmark run directories

Validated governed bundles live here as `benchmarks/runs/<run_id>/` after you run `python -m conicshield.bench.reference_run --out ...`.

## Layout

Each run directory should pass `validate_run_bundle` and typically contains at least:

- `config.json`, `summary.json`, `episodes.jsonl`, `transition_bank.json`
- Schema sidecars copied by `reference_run` (`*.schema.json`)

After validation, you can emit a Layer G report: `python scripts/artifact_validation_report.py --run-dir benchmarks/runs/<run_id>` (see [docs/VERIFICATION_AND_STRESS_TEST_PLAN.md](../../docs/VERIFICATION_AND_STRESS_TEST_PLAN.md)).

## Promotion to parity fixture

When a run is approved for native parity regression testing, promote it with:

```bash
python scripts/regenerate_parity_fixture.py --source benchmarks/runs/<run_id>
```

See [`docs/PARITY_AND_FIXTURES.md`](../docs/PARITY_AND_FIXTURES.md) for the fixture promotion checklist.

## Git policy

Large binary-ish JSONL trees may be gitignored or stored out-of-band per team policy. The parity **fixture** under `tests/fixtures/parity_reference/` is the minimal frozen contract kept in-repo for CI.
