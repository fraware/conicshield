# `conicshield.published_runs` API

Stable read-only interface for committed bundles under `benchmarks/published_runs/`.  
Does not run publish, parity, or refresh — use maintainer scripts for that.

## Install

```bash
pip install -e .
```

## Functions

| Function | Returns | Purpose |
|----------|---------|---------|
| `list_runs()` | `tuple[PublishedRunIndexEntry, ...]` | All runs in `PUBLISHED_RUN_INDEX.json` |
| `get_current_run(family_id)` | `PublishedRunBundle` | Family `CURRENT.json` → published bundle |
| `load_run(run_id)` | `PublishedRunBundle` | Paths + parsed sidecars |
| `verify_run(run_id)` | `None` | SHA-256 check vs index (raises on mismatch) |
| `load_summary(run_id)` | `tuple[SummaryRow, ...]` | `summary.json` arm rows |
| `load_provenance(run_id)` | `RunProvenance` | `RUN_PROVENANCE.json` (typed) |
| `load_episodes(run_id)` | `tuple[dict, ...]` | `episodes.jsonl` records |
| `index_path()` | `Path` | `benchmarks/PUBLISHED_RUN_INDEX.json` |

`current_family_run(family_id)` is an alias of `get_current_run`.

## Dataclasses

- **`PublishedRunBundle`** — `run_id`, `path`, `index_entry`, `community`, `governance_status`, `run_provenance`
- **`CommunityMetadata`** — `evidence_tier`, `host_realistic`, `includes_native_arm`, `recommended_uses`, `known_limitations`, …
- **`RunProvenance`** — `projector_mode`, `host_realistic_evidence`, `export_source`, …
- **`SummaryRow`** — `label`, `solve_time_p50_ms`, `extra`

Schema for `COMMUNITY_METADATA.json`: [COMMUNITY_METADATA_SCHEMA.md](COMMUNITY_METADATA_SCHEMA.md).

## CLI

```bash
python -m conicshield.published_runs.cli list
python -m conicshield.published_runs.cli verify host-realistic-20260525
python -m conicshield.published_runs.cli show host-realistic-20260525
python -m conicshield.published_runs.cli current
```

## Examples

- [examples/verify_published_run_index.py](../examples/verify_published_run_index.py)
- [examples/load_flagship_run.py](../examples/load_flagship_run.py)
- [QUICKSTART_RESEARCHER.md](QUICKSTART_RESEARCHER.md)
