# Roadmap

Operational commands: [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md). System map: [`REFERENCE_SYSTEM.md`](REFERENCE_SYSTEM.md).

## Current flagship

| Item | State |
|------|--------|
| Family | `conicshield-transition-bank-v1` |
| `current_run_id` | `host-realistic-20260525` |
| Tier | `vendor_native`, `real_projector`, green gates |
| Export | `live_upstream_dump` (fork graph via inter-sim API) |
| Refresh | Governed cadence + [`REFERENCE_AUTHORITY_LOG.md`](REFERENCE_AUTHORITY_LOG.md); monthly workflow |

## Operations (ongoing)

| Task | Trigger |
|------|---------|
| Update [`ENGINEERING_STATUS.md`](ENGINEERING_STATUS.md) | After green `vendor-ci-moreau` or flagship refresh (`solver_versions.json`) |
| Host-realistic refresh | [`HOST_REALISTIC_CADENCE_POLICY.md`](HOST_REALISTIC_CADENCE_POLICY.md) — monthly + immediate triggers |
| Re-capture export | `inter-sim-rl` REVISION, export parsers, bank/publish logic |
| Parity fixture | Promote from S2 bundle only; [`PARITY_AND_FIXTURES.md`](PARITY_AND_FIXTURES.md) |

## Deferred semantics

- **`progress` / `clearance`** — not implemented; [adr/001](adr/001-progress-clearance-constraints.md).

## Closed (v1 reference system)

Auditable in Git; do not re-open without a new milestone:

| Area | Delivered |
|------|-----------|
| Governed publish | `finalize_cli` / `release_cli` / `audit_cli`; `PUBLISHED_RUN_INDEX` v2 |
| Flagship | `host-realistic-20260525` published; live export path + refresh cycle |
| Native batch API | `NATIVE_MOREAU_BATCH`; viability + throughput-advisory policy |
| CI merge | `reference-authority`, Policy B attestation, bundle profile validator |
| inter-sim pin | `third_party/inter-sim-rl/REVISION`; capture via `make capture-inter-sim-graph` |
| Refresh cadence | `HOST_REALISTIC_CADENCE_POLICY.md`, monthly workflows, `REFERENCE_AUTHORITY_LOG.md` |
| Community bundles | `COMMUNITY_METADATA.json`, `PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md` |
| System status | `reference_system_status.json`, `generate_reference_system_status.py` |

## Open backlog

| # | Item | Next action |
|---|------|-------------|
| 1 | Richer upstream graph | Capture from patched host when available; not fork-only |
| 2 | Autograd product | Deferred; [`DIFFERENTIATION_PUBLIC_STANCE.md`](DIFFERENTIATION_PUBLIC_STANCE.md) |
| 3 | Conic suite CI artifacts | Optional committed `benchmarks/reports/conic_suite_*.json` |
| 4 | Test tree moves | Incremental per [`tests/STRUCTURE.md`](../tests/STRUCTURE.md) |
| 5 | Second family | `conicshield-shield-qp-micro-v1` uninitialized — Option B |
| 6 | Product extensions | New family manifest + governance per feature |

## v2 default

[`V2_STRATEGY.md`](V2_STRATEGY.md) — **Option A** (deepen same family). Option B/C deferred.
