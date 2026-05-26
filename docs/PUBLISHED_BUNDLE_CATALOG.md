# Published bundle catalog (reference-grade artifacts)

Every governed run under `benchmarks/published_runs/<run_id>/` follows this surface. The machine-readable view is `catalog` on each entry in [`PUBLISHED_RUN_INDEX.json`](../benchmarks/PUBLISHED_RUN_INDEX.json).

## Required validated files

Hashes recorded in the index (schema v2):

| File | Role |
|------|------|
| `config.json` / `config.schema.json` | Task contract and arms |
| `summary.json` / `summary.schema.json` | Per-arm benchmark metrics |
| `episodes.jsonl` / `episodes.schema.json` | Episode stream |
| `transition_bank.json` | Bank used for the run |

## Required governance files (when published)

| File | Role |
|------|------|
| `governance_status.json` | Gate outcomes, `publishable_arms`, `state` |
| `governance_decision.md` | Human approve/reject record before `release_cli` |
| `RUN_PROVENANCE.json` | Export source, `evidence_tier`, `projector_mode` |

## Optional files (hashed when present)

| File | Role |
|------|------|
| `release_decision.json` | `release_cli` audit trail |
| `solver_versions.json` | Pinned vendor stack at publish time |
| `parity_out/parity_summary.json` | Native parity evidence (host-realistic flagship) |
| `README.md` | Human summary (sync: `scripts/sync_published_run_readmes.py`) |

## Index `catalog` fields

| Field | Meaning |
|-------|---------|
| `evidence_tier` | S0–S3 (`contract_fixture` … `vendor_native`) |
| `host_realistic` | From `RUN_PROVENANCE.host_realistic_evidence` |
| `includes_native_arm` | `shielded-native-moreau` row in `summary.json` |
| `parity_fixture_source` | This run promoted parity gold per `REGENERATION_NOTE.md` |
| `has_solver_versions` | `solver_versions.json` on disk |
| `projector_mode` | e.g. `real_projector`, `passthrough` |
| `governance_state` | e.g. `published`, `review-locked` |
| `is_family_current_run` | Matches `CURRENT.json` `current_run_id` |

## Human README

Each bundle should have `README.md` stating what the run proves, what environment produced it, and what it must not be used to claim. Regenerate:

```bash
python scripts/sync_published_run_readmes.py
```
