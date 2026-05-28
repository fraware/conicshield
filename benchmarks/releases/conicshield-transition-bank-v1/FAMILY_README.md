# Family `conicshield-transition-bank-v1`

Governance: [`docs/BENCHMARK_GOVERNANCE.md`](../../../docs/BENCHMARK_GOVERNANCE.md), [`docs/RELEASE_POLICY.md`](../../../docs/RELEASE_POLICY.md).

## Current release

| Field | Value |
|-------|--------|
| `current_run_id` | **`host-realistic-20260525`** |
| Tier | S3 `vendor_native` |
| Export | `live_upstream_dump` (fork graph via inter-sim API) |

Machine-readable: `CURRENT.json`, `HISTORY.json`, `FAMILY_MANIFEST.json`.

Refresh cadence: [`docs/REFERENCE_REFRESH_LOG.md`](../../../docs/REFERENCE_REFRESH_LOG.md).

## Bundles

Paths in `CURRENT.json` → `benchmark_bundle_paths`. Integrity: [`PUBLISHED_RUN_INDEX.json`](../../PUBLISHED_RUN_INDEX.json).

| `run_id` | Role |
|----------|------|
| `host-realistic-20260525` | Flagship current |
| `wsl-real-20260409-132450` | S2 reference; parity gold source |
| `wsl-native-20260409-091141` | S3 historical |

## Gate refresh without new run

`finalize_cli --sync-current-release` — same `current_run_id`, updated parity columns only.

## Other families

`conicshield-shield-qp-micro-v1` — uninitialized; do not use for external claims.
