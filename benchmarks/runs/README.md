# Ephemeral runs (`benchmarks/runs/`)

Gitignored working directories. Promote to [`../published_runs/`](../published_runs/) after governed validation.

```bash
python -m conicshield.artifacts.validator_cli --run-dir benchmarks/runs/<run_id>
python scripts/governed_local_promotion.py --help
```

Maintainers: [`CONTRIBUTING.md`](../../CONTRIBUTING.md). Parity fixtures: `tests/fixtures/parity_reference/`.
