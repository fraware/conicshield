# Published runs (`benchmarks/published_runs/`)

Committed governed bundles. Ephemeral work: `benchmarks/runs/<run_id>/` (gitignored).

**Flagship:** [`host-realistic-20260525/`](host-realistic-20260525/README.md) — family `current_run_id`.

## Integrity

```bash
python scripts/refresh_published_run_index.py --check
python scripts/validate_published_bundle_profile.py
make verify-reference-system
```

Index: [`PUBLISHED_RUN_INDEX.json`](../PUBLISHED_RUN_INDEX.json) (schema v2, SHA-256).

## Publish sequence

1. Produce under `benchmarks/runs/<run_id>/` (non-passthrough for vendor claims).
2. `validator_cli --run-dir …`
3. Parity → `finalize_cli` (`--parity-summary-path` when native).
4. Copy to `published_runs/<run_id>/`; whitelist in [`.gitignore`](.gitignore).
5. `governance_decision.md` (approve) → `release_cli` → `audit_cli --strict`.
6. `refresh_published_run_index.py`; commit index.

**Host-realistic:** `make host-realistic-refresh-cycle` — [`docs/HOST_REALISTIC_REFRESH_PROCEDURE.md`](../../docs/HOST_REALISTIC_REFRESH_PROCEDURE.md).

## Layout (typical)

- Validator required: `config.json`, `summary.json`, `episodes.jsonl`, `transition_bank.json` (+ schemas)
- Governance: `governance_status.json`, `RUN_PROVENANCE.json`, `governance_decision.md`, `release_decision.json`
- Flagship adds: `solver_versions.json`, `parity_out/`, `README.md`

Catalog: [`docs/PUBLISHED_BUNDLE_CATALOG.md`](../../docs/PUBLISHED_BUNDLE_CATALOG.md).

## Rehearsal only

`--passthrough` / minimal fixture — not for parity promotion or `vendor_native` claims.

Full detail: [`docs/MAINTAINER_RUNBOOK.md`](../../docs/MAINTAINER_RUNBOOK.md).
