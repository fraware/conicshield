# External evidence (host-realistic export)

Committed artifacts that demonstrate the **export → transition bank → publish → parity** loop without relying on `tests/fixtures/offline_graph_export_minimal.json`.

| File | Role |
|------|------|
| [`offline_graph_export_upstream.json`](offline_graph_export_upstream.json) | `offline_transition_graph_export/v1` with multi-branch graph (Root → NodeA/NodeB/NodeC) |
| [`EXPORT_PROVENANCE.json`](EXPORT_PROVENANCE.json) | Pin and notes for upstream `inter-sim-rl` revision |

**Flagship published bundle:** [`../published_runs/host-realistic-20260525/`](../published_runs/host-realistic-20260525/) — `RUN_PROVENANCE.json` references this export at **`vendor_native`** tier.

## Committed structural graph vs live upstream dump

| Kind | What it is | When to use |
|------|------------|-------------|
| **Committed structural graph** | Multi-branch graph checked into this directory (rehearsal fork or prior export) | Proves the governed loop in public CI without a live simulator session |
| **Live upstream dump** | Raw graph captured via `make capture-inter-sim-graph` (pinned `RLEnvironment` + M2 patch) then `refresh_live_upstream_export.py` | Replaces `offline_graph_export_upstream.json`; updates `EXPORT_PROVENANCE.json` (`export_kind: live_upstream_dump`) |

After replacing the JSON, re-run:

```bash
make upgrade-host-realistic-vendor
```

## Regenerate structural export JSON

```bash
make export-upstream-rehearsal
```

## Produce or refresh published bundle

```bash
make upgrade-host-realistic-vendor
# or:
python scripts/run_host_realistic_publish.py \
  --export-json benchmarks/external_evidence/offline_graph_export_upstream.json \
  --run-id host-realistic-20260525 \
  --no-passthrough \
  --include-native-arm \
  --governance-scaffold \
  --copy-to-published \
  --refresh-index \
  --force
```

Keep schema validation and provenance fields aligned when the export file changes.
