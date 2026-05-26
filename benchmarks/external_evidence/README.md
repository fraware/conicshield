# External evidence (host-realistic export)

Committed artifacts that demonstrate the **export → transition bank → publish** loop without relying on `tests/fixtures/offline_graph_export_minimal.json`.

| File | Role |
|------|------|
| [`offline_graph_export_upstream.json`](offline_graph_export_upstream.json) | `offline_transition_graph_export/v1` with multi-branch graph (Root → NodeA/NodeB/NodeC) |
| [`EXPORT_PROVENANCE.json`](EXPORT_PROVENANCE.json) | Pin and notes for upstream `inter-sim-rl` revision |

**Published bundle:** [`../published_runs/host-realistic-20260525/`](../published_runs/host-realistic-20260525/) — `RUN_PROVENANCE.json` references this export.

**Regenerate export JSON (structural fork graph):**

```bash
make export-upstream-rehearsal
```

**Produce or refresh published bundle:**

```bash
python scripts/run_host_realistic_publish.py \
  --export-json benchmarks/external_evidence/offline_graph_export_upstream.json \
  --run-id host-realistic-20260525 \
  --no-passthrough \
  --copy-to-published \
  --refresh-index \
  --force
```

Replace the JSON with a live dump from a patched host when available; keep schema validation and provenance fields aligned.
