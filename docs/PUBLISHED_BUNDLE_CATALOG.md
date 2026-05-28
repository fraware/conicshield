# Published bundle catalog

Path: `benchmarks/published_runs/<run_id>/`. Index: [`PUBLISHED_RUN_INDEX.json`](../benchmarks/PUBLISHED_RUN_INDEX.json) (`catalog` per run).

Validate all indexed runs:

```bash
python scripts/validate_published_bundle_profile.py
```

Human READMEs: `python scripts/sync_published_run_readmes.py`

## Files (all published runs)

| File | Role |
|------|------|
| `config.json`, `config.schema.json` | Task contract, arms |
| `summary.json`, `summary.schema.json` | Per-arm metrics |
| `episodes.jsonl`, `episodes.schema.json` | Episode stream |
| `transition_bank.json` | Bank |
| `governance_status.json` | Gates, `publishable_arms`, `state` |
| `RUN_PROVENANCE.json` | `evidence_tier`, export source |
| `governance_decision.md` | Approve before `release_cli` |
| `release_decision.json` | `release_cli` record |
| `README.md` | Proves / does-not-prove / tier |

## Additional (flagship / current run)

| File | When |
|------|------|
| `solver_versions.json` | `current_run_id` |
| `parity_out/parity_summary.json` | Host-realistic + native arm |

Profile rules: [`published_bundle_profile.json`](../benchmarks/reports/published_bundle_profile.json).

## Index `catalog` fields

| Field | Meaning |
|-------|---------|
| `evidence_tier` | S0–S3 |
| `host_realistic` | `RUN_PROVENANCE.host_realistic_evidence` |
| `includes_native_arm` | `shielded-native-moreau` in `summary.json` |
| `parity_fixture_source` | Promoted parity gold |
| `governance_state` | e.g. `published` |
| `is_family_current_run` | Matches `CURRENT.json` |

Flagship README template includes **Evidence qualification** — see `host-realistic-20260525/README.md`.
