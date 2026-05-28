# `conicshield.published_runs` API (v1)

Stable read-only interface for committed bundles under `benchmarks/published_runs/`.  
Does not publish, refresh parity, or mutate the index — use maintainer scripts for that.

**Version:** `PUBLISHED_RUNS_API_VERSION = "v1"` (see `conicshield.published_runs.api`).

## v1 stability guarantees

### Stable in v1 (do not rename or remove without a major bump)

| Symbol | Role |
|--------|------|
| `list_runs()` | Index entries |
| `get_current_run(family_id)` | Family `CURRENT.json` → bundle |
| `current_family_run` | Alias of `get_current_run` |
| `load_run(run_id)` | Bundle + sidecars |
| `verify_run(run_id)` | SHA-256 vs index |
| `load_summary(run_id)` | `summary.json` rows |
| `load_provenance(run_id)` | `RUN_PROVENANCE.json` typed |
| `load_episodes(run_id)` | `episodes.jsonl` |
| `index_path()` | Path to `PUBLISHED_RUN_INDEX.json` |
| CLI: `list`, `current`, `verify`, `show`, `summary`, `provenance` | Mirrors Python API |

Dataclasses: `PublishedRunBundle`, `CommunityMetadata`, `RunProvenance`, `SummaryRow`, `PublishedRunIndexEntry`, `IntegrityEntry`.

### Stable output fields (v1)

| Type | Stable fields consumers may rely on |
|------|-------------------------------------|
| `PublishedRunIndexEntry` | `run_id`, `repository_relative_path`, `integrity` (`IntegrityEntry.path`, `.sha256`), `catalog` |
| `PublishedRunBundle` | `run_id`, `path`, `index_entry`, `community`, `governance_status`, `run_provenance` |
| `CommunityMetadata` | `run_id`, `family_id`, `evidence_tier`, `projector_mode`, `known_limitations`, `recommended_uses` |
| `RunProvenance` | `run_id`, `evidence_tier`, `projector_mode`, `host_realistic_evidence`, `export_source`, `extra` |
| `SummaryRow` | `label`, `solve_time_p50_ms`, `extra` (arm-specific metrics) |
| `IntegrityEntry` | `path`, `sha256` |
| CLI subcommands | `list`, `current`, `verify`, `show`, `summary`, `provenance` — stdout is human-readable text |

New optional attributes on dataclasses may appear in v1.x; required fields above will not be renamed or removed without a major API version bump.

### May expand in v1.x (backward compatible)

- Optional fields on dataclasses (with defaults)
- New read-only helpers that do not change existing signatures
- Additional CLI subcommands that do not alter existing ones

### Explicitly internal (not public API)

- `conicshield.governance.*`, `conicshield.published_run_index` (use `published_runs` instead)
- `ensure_community_metadata` (build helper; prefer on-disk `COMMUNITY_METADATA.json`)
- Publish/finalize/release CLIs and `scripts/*` refresh tooling

## Install

```bash
pip install -e .
```

## Python examples

```python
from conicshield.published_runs import (
    list_runs,
    get_current_run,
    load_run,
    verify_run,
    load_summary,
    load_provenance,
)

# Iterate indexed run ids
for entry in list_runs():
    print(entry.run_id, entry.repository_relative_path)

# Flagship / family current
verify_run("host-realistic-20260525")
bundle = get_current_run("conicshield-transition-bank-v1")
print(bundle.community.known_limitations)

# Compare two summary arms (metrics only — not a speedup claim)
rows = {r.label: r for r in load_summary(bundle.run_id)}
ref = rows["shielded-rules-plus-geometry"]
nat = rows["shielded-native-moreau"]
print(ref.solve_time_p50_ms, nat.solve_time_p50_ms)

prov = load_provenance(bundle.run_id)
print(prov.evidence_tier, prov.projector_mode)
```

**Canonical walkthrough** (list → current → verify → summary → provenance): [examples/load_published_runs_api.py](../examples/load_published_runs_api.py).

## CLI (mirrors Python API)

```bash
python -m conicshield.published_runs.cli list
python -m conicshield.published_runs.cli current conicshield-transition-bank-v1
python -m conicshield.published_runs.cli verify host-realistic-20260525
python -m conicshield.published_runs.cli show host-realistic-20260525
python -m conicshield.published_runs.cli summary host-realistic-20260525
python -m conicshield.published_runs.cli provenance host-realistic-20260525
```

After install: `conicshield-published-runs verify host-realistic-20260525`.

## Index catalog stability

Machine catalog: [`benchmarks/PUBLISHED_RUN_INDEX.json`](../benchmarks/PUBLISHED_RUN_INDEX.json) (schema `conicshield_published_run_index/v2`).

| Stable | Meaning |
|--------|---------|
| `schema_version` | Top-level schema id |
| `runs[].run_id` | Bundle directory name |
| `runs[].repository_relative_path` | Path from repo root |
| `runs[].integrity` | Map of relative file → `{sha256}` |

| Optional / catalog | May grow per run |
|--------------------|------------------|
| `runs[].catalog` | Denormalized flags (`evidence_tier`, `host_realistic`, …) |

Forward-compatible pattern: add new **optional** keys under `catalog` or new integrity files; never rename `run_id` in place. Refresh: `python scripts/refresh_published_run_index.py`.

Consumer guide: [PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md](PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md).

## Related docs

- [COMMUNITY_LAYER.md](COMMUNITY_LAYER.md) — public front door
- [COMMUNITY_METADATA_SCHEMA.md](COMMUNITY_METADATA_SCHEMA.md)
- [CITING_CONICSHIELD_ARTIFACTS.md](CITING_CONICSHIELD_ARTIFACTS.md)
