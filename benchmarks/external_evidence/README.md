# External evidence

Committed export for the host-realistic loop. **Flagship bundle:** [`../published_runs/host-realistic-20260525/`](../published_runs/host-realistic-20260525/).

| File | Role |
|------|------|
| [`offline_graph_export_upstream.json`](offline_graph_export_upstream.json) | `offline_transition_graph_export/v1` (multi-branch graph) |
| [`EXPORT_PROVENANCE.json`](EXPORT_PROVENANCE.json) | `export_kind`, pin, [`refresh_history`](EXPORT_PROVENANCE.json) |
| [`live_dumps/`](live_dumps/) | Raw graph + capture provenance from `make capture-inter-sim-graph` |

## Current export kind

`EXPORT_PROVENANCE.export_kind` is **`live_upstream_dump`**.

| Claim | Status |
|-------|--------|
| Graph validated via inter-sim `RLEnvironment` at pinned sha | Yes |
| Topology | Host-realistic **fork** (Root → NodeA/NodeB/NodeC) |
| Maps/session navigation graph | **No** — unless a future capture says otherwise |

## Refresh

```bash
make capture-inter-sim-graph
make refresh-live-upstream-export-live
make host-realistic-refresh-cycle
```

Cadence: [`../../docs/REFERENCE_REFRESH_LOG.md`](../../docs/REFERENCE_REFRESH_LOG.md).

## Structural rehearsal only (CI)

```bash
make export-upstream-rehearsal
```

Does not replace flagship provenance for vendor-native claims.
