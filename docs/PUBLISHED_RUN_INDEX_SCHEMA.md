# `PUBLISHED_RUN_INDEX.json` schema note

Machine-readable integrity catalog for committed bundles under `benchmarks/published_runs/`.

## Stable (safe for external tools)

| Field | Stability |
|-------|-----------|
| `schema_version` | Integer `2` for current format |
| `runs[].run_id` | Stable identifier for a bundle |
| `runs[].repository_relative_path` | Stable path from repo root |
| `runs[].integrity` | Map of **relative file path** → `{ "sha256": "<hex>" }` |
| `governed_run_ids` | Sorted list of indexed ids |

Required hashed files match `validate_run_bundle` required surface (see `conicshield.published_run_index.PUBLISHED_RUN_REQUIRED_INTEGRITY_FILENAMES`).

Optional hashed files when present: governance, provenance, `README.md`, `COMMUNITY_METADATA.json`, etc.

## May evolve (do not hard-code beyond docs)

| Field | Notes |
|-------|--------|
| `generated_at_utc` | Regenerated on each index refresh |
| `runs[].catalog` | Denormalized metadata for dashboards; not a substitute for on-disk `COMMUNITY_METADATA.json` |
| Additional optional integrity keys | New sidecars may appear as bundles gain files |

## How external tools should read it

1. Parse JSON at `benchmarks/PUBLISHED_RUN_INDEX.json`.
2. For each `run_id`, resolve `repository_relative_path` relative to the **git commit** you trust.
3. Verify every `integrity` entry with SHA-256 before reading metrics.
4. Read scope from `COMMUNITY_METADATA.json` and human `README.md` — not from the index alone.

## CLI

```bash
python -m conicshield.published_runs.cli list
python -m conicshield.published_runs.cli verify host-realistic-20260525
python -m conicshield.published_runs.cli show host-realistic-20260525
```

## Python API

```python
from conicshield.published_runs import list_runs, load_run, verify_run
```

See [PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md](PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md).
