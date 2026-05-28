# Published runs (`benchmarks/published_runs/`)

Committed governed bundles. Ephemeral work: `benchmarks/runs/<run_id>/` (gitignored).

**Flagship:** [`host-realistic-20260525/`](host-realistic-20260525/README.md) — family `current_run_id`.

## Integrity

```bash
python -m conicshield.published_runs.cli verify host-realistic-20260525
make community-verify
make verify-v1-lock-quick
```

Index: [`PUBLISHED_RUN_INDEX.json`](../PUBLISHED_RUN_INDEX.json) (schema v2, SHA-256). Consumers: [`docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md`](../../docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md).

## Publish (maintainers)

See [`CONTRIBUTING.md`](../../CONTRIBUTING.md). Typical: validate run → finalize → copy here → `make finalize-community-dataset` → refresh index.

**Host-realistic refresh:** `make host-realistic-refresh-cycle-licensed`.

## Layout (typical)

- `config.json`, `summary.json`, `episodes.jsonl`, `transition_bank.json`
- `governance_status.json`, `RUN_PROVENANCE.json`, `COMMUNITY_METADATA.json`, `README.md`
- Flagship: `solver_versions.json`, `parity_out/`

Public entry: [`docs/COMMUNITY_LAYER.md`](../../docs/COMMUNITY_LAYER.md).
