# ConicShield v1 reference release

Public name for the governed **host-realistic flagship** reference system shipped in this repository.

## What v1 is

| Item | Value |
|------|--------|
| Family | `conicshield-transition-bank-v1` |
| Flagship `run_id` | `host-realistic-20260525` |
| Evidence tier | `vendor_native`, `real_projector` |
| Export | `live_upstream_dump` (inter-sim fork topology) |
| Public API | `conicshield.published_runs` v1 (frozen) |
| Integrity catalog | `benchmarks/PUBLISHED_RUN_INDEX.json` schema v2 |

## What v1 is for

- Reproducible, hash-verified benchmark bundles for external researchers
- Library integration via reference CVXPY and (with license) native Moreau paths
- A closed maintainer loop: export → bank → publish → parity → index

## What v1 is not

See [PUBLIC_CLAIMS.md](PUBLIC_CLAIMS.md): no production autograd product, no universal batch speedup claim, no Maps/session navigation graph, no second-family authority.

## How to consume (start here)

1. [COMMUNITY_LAYER.md](COMMUNITY_LAYER.md)
2. `python examples/verify_published_run_index.py`
3. [CITING_CONICSHIELD_ARTIFACTS.md](CITING_CONICSHIELD_ARTIFACTS.md)

## How to verify coherence

```bash
make verify-v1-lock-quick
python scripts/print_v1_status.py
```

Machine snapshot: [`benchmarks/reports/reference_system_status.json`](../benchmarks/reports/reference_system_status.json).

## Maintainer operations

- Refresh: [HOST_REALISTIC_REFRESH_PROCEDURE.md](HOST_REALISTIC_REFRESH_PROCEDURE.md)
- Lock gate: [V1_LOCK_CHECKLIST.md](V1_LOCK_CHECKLIST.md)
- Strategy: [V2_STRATEGY.md](V2_STRATEGY.md) (Option A active; B/C deferred)
