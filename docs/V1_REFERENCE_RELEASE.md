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
- A closed export → bank → publish → parity → index loop (operational detail in Makefile / `scripts/`)

## What v1 is not

Aligned with [PUBLIC_CLAIMS.md](PUBLIC_CLAIMS.md): no production autograd product, no Maps/session navigation graph, no second-family authority; public batch narrative is **viability_only** (does not claim throughput wins). `progress` / `clearance` constraint kinds are not implemented.

Track 1 **runtime qualification** (S8) is a separate artifact from this v1 bundle authority. See [`stabilization/PRODUCTION_QUALIFICATION_REPORT.md`](stabilization/PRODUCTION_QUALIFICATION_REPORT.md) and [`benchmarks/reports/s8_qualification/`](../benchmarks/reports/s8_qualification/). Do not conflate host runtime benches with published-run integrity.

## How to consume (start here)

```bash
pip install -e ".[dev]"
make onboard
```

1. [COMMUNITY_LAYER.md](COMMUNITY_LAYER.md) — product homepage
2. [examples/load_published_runs_api.py](../examples/load_published_runs_api.py) — canonical API walkthrough
3. [CITING_CONICSHIELD_ARTIFACTS.md](CITING_CONICSHIELD_ARTIFACTS.md)

## How to verify coherence

| Command | When |
|---------|------|
| `make verify-v1-lock-quick` | Day-to-day auditor check |
| `make verify-v1-lock` | Pre-announcement lock gate |
| `python scripts/print_v1_status.py` | Human-readable status snapshot |

```bash
make verify-v1-lock-quick
python scripts/verify_v1_lock.py --json
```

Example success output: [`V1_LOCK_AUDITOR_SUCCESS.example.json`](V1_LOCK_AUDITOR_SUCCESS.example.json).

Machine snapshot: [`benchmarks/reports/reference_system_status.json`](../benchmarks/reports/reference_system_status.json).

## Maintainers

See [CONTRIBUTING.md](../CONTRIBUTING.md). Typical targets: `make verify-v1-lock`, `make host-realistic-refresh-cycle-licensed`, `make finalize-community-dataset`. Refresh log: [`benchmarks/reports/reference_refresh_log.md`](../benchmarks/reports/reference_refresh_log.md).
