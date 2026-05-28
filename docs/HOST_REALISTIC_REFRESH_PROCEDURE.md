# Host-realistic refresh procedure

**Flagship:** `host-realistic-20260525` (`current_run_id`). **Log every cycle:** [`REFERENCE_REFRESH_LOG.md`](REFERENCE_REFRESH_LOG.md).

Licensed **Linux/WSL** host required for native arm, parity, and batch sweep.

## Standard cycle (current export)

```bash
make capture-inter-sim-graph
make refresh-live-upstream-export-live
make host-realistic-refresh-cycle
```

What this does:

1. Capture `offline_transition_graph` via pinned inter-sim `RLEnvironment` → `benchmarks/external_evidence/live_dumps/`.
2. Replace `offline_graph_export_upstream.json`; set `EXPORT_PROVENANCE.export_kind` to `live_upstream_dump`.
3. Re-publish bundle, release sync (same `run_id`), batch viability check, index + snapshot + `reference_authority_check`.

Default `run_id`: family `current_run_id` from `CURRENT.json`.

## Variants

| Goal | Command |
|------|---------|
| Same flagship, full refresh | `make host-realistic-refresh-cycle` |
| New dated run + promote | `make host-realistic-refresh-milestone` |
| Explicit run id | `python scripts/host_realistic_refresh_cycle.py --run-id host-realistic-YYYYMMDD --force` |
| Governance only | `python scripts/upgrade_host_realistic_vendor.py --run-id <id> --refresh-governance` |
| Skip batch sweep | `... --skip-vendor-verify` |

## Cadence

| Trigger | Action |
|---------|--------|
| Monthly / calendar | Run standard cycle; append row to [`REFERENCE_REFRESH_LOG.md`](REFERENCE_REFRESH_LOG.md) |
| `inter-sim-rl` REVISION change | Re-capture graph + full cycle |
| Solver / native / batch code change | Full cycle + vendor attestation on PR |

## After each cycle (commit)

1. `benchmarks/published_runs/<run_id>/` (if changed)
2. `benchmarks/PUBLISHED_RUN_INDEX.json`
3. `benchmarks/external_evidence/EXPORT_PROVENANCE.json`
4. `benchmarks/reports/reference_authority_snapshot.json`
5. `benchmarks/reports/batch_solve_report.latest.json` (if batch ran)
6. Row in [`REFERENCE_REFRESH_LOG.md`](REFERENCE_REFRESH_LOG.md)
7. [`ENGINEERING_STATUS.md`](ENGINEERING_STATUS.md) solver rows from flagship `solver_versions.json`

## Evidence qualification (do not overstate)

- `live_upstream_dump` = inter-sim API capture at pinned sha, **fork** topology.
- Not a Maps/session navigation graph unless a future capture documents one.

## Related

- [`HOST_REALISTIC_RUNBOOK.md`](HOST_REALISTIC_RUNBOOK.md) — manual step list
- [`REFERENCE_AUTHORITY.md`](REFERENCE_AUTHORITY.md) — flagship map
