# `COMMUNITY_METADATA.json` schema

Public scope contract for each governed bundle under `benchmarks/published_runs/<run_id>/`.

**Schema id:** `conicshield_community_metadata/v1`  
**Required on every published bundle** (see `published_bundle_profile.json`).

## Required fields

| Field | Type | Meaning |
|-------|------|---------|
| `schema_version` | string | Always `conicshield_community_metadata/v1` |
| `run_id` | string | Bundle directory name |
| `family_id` | string | Benchmark family (e.g. `conicshield-transition-bank-v1`) |
| `evidence_tier` | string | `contract_fixture` \| `structural_export` \| `vendor_reference` \| `vendor_native` |
| `host_realistic` | bool | Host-realistic export evidence path |
| `includes_native_arm` | bool | `shielded-native-moreau` present in `summary.json` |
| `projector_mode` | string \| null | e.g. `real_projector`, `passthrough` |
| `is_family_current_run` | bool | Matches family `CURRENT.json` `current_run_id` |
| `parity_fixture_source` | bool | Repo parity gold promoted from this bundle |
| `export_kind` | string \| null | e.g. `live_upstream_dump` (from export provenance) |
| `source_export` | string \| null | Path to upstream export JSON when host-realistic |
| `parity_status` | string | Parity summary status when present |
| `recommended_uses` | string[] | What external researchers may use this bundle for |
| `known_limitations` | string[] | Explicit non-claims and scope bounds |

## Optional fields

| Field | Type | Meaning |
|-------|------|---------|
| `solver_stack` | object \| null | `moreau`, `cvxpy`, `cvxpylayers` versions when recorded |

## Generate / refresh

```bash
python scripts/sync_community_metadata.py
```

Builder: `conicshield.governance.community_metadata.build_community_metadata`.

## Read in Python

```python
from conicshield.published_runs import load_run
bundle = load_run("host-realistic-20260525")
meta = bundle.community
```

See [QUICKSTART_RESEARCHER.md](QUICKSTART_RESEARCHER.md).
