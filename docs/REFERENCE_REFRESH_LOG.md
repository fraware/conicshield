# Reference refresh log (host-realistic flagship)

Cadence record for `conicshield-transition-bank-v1` / `host-realistic-20260525`. Each entry is an independent governed refresh with provenance.

| # | Date (UTC) | Trigger | Git / notes | `EXPORT_PROVENANCE.export_kind` | Authority aligned |
|---|------------|---------|-------------|--------------------------------|-------------------|
| 1 | 2026-05-26 | Event-driven (refresh execution) | `2ff5fea` — release sync, batch viability, reference gates | `structural_committed` → then live path | yes |
| 2 | 2026-05-26 | Event-driven (live export + full cycle) | `381004e` — `capture-inter-sim-graph`, `live_upstream_dump`, full `host-realistic-refresh-cycle` | `live_upstream_dump` | yes |
| 3 | 2026-05-28 | **Calendar / cadence** — maintainer scheduled refresh (`make capture-inter-sim-graph` → `refresh-live-upstream-export-live` → `host-realistic-refresh-cycle`) | `714e213` | `live_upstream_dump` | yes |

## Standard refresh commands (licensed WSL host)

```bash
make capture-inter-sim-graph
make refresh-live-upstream-export-live
make host-realistic-refresh-cycle
```

Commit: `benchmarks/published_runs/host-realistic-20260525/`, `PUBLISHED_RUN_INDEX.json`, `EXPORT_PROVENANCE.json`, `benchmarks/reports/reference_authority_snapshot.json`, and append a row to this table.

## Evidence qualification (unchanged across refreshes until graph changes)

- Export loop is **closed in-repo** at `vendor_native`.
- `export_kind: live_upstream_dump` means the graph was captured via pinned **inter-sim-rl `RLEnvironment`** (see `live_dumps/*.provenance.json`).
- Graph topology is still the **host-realistic fork** (Root → NodeA/NodeB/NodeC), **not** a Maps/session-built navigation graph.
