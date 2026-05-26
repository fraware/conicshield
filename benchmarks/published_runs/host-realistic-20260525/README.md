# Published run `host-realistic-20260525`

Governed benchmark bundle for `conicshield-transition-bank-v1`.

| Field | Value |
|-------|--------|
| `evidence_tier` | `vendor_native` |
| `projector_mode` | `real_projector` |
| Host-realistic export evidence | yes |
| Includes `shielded-native-moreau` | yes |
| Parity fixture gold source | no |
| Family `current_run_id` | yes |
| Governance `state` | `published` |
| Committed export `export_kind` | `live_upstream_dump` |

## What this run proves

- Validated artifact surface (`validate_run_bundle`)
- Benchmark arms in `summary.json` with governance gates in `governance_status.json`
- Host-realistic export → bank → publish → parity loop is closed in-repo when `host_realistic` is yes

## Evidence qualification

- **Export loop:** closed in-repo; source export is `benchmarks/external_evidence/offline_graph_export_upstream.json` (`export_kind: live_upstream_dump`).
- **Live capture:** when `export_kind` is `live_upstream_dump`, the graph was validated through pinned **inter-sim-rl `RLEnvironment`** (see `benchmarks/external_evidence/live_dumps/*.provenance.json`).
- **Graph content:** host-realistic **fork topology** (Root → NodeA/NodeB/NodeC), not a full Maps/session-built navigation graph unless provenance explicitly says otherwise.
- **Cadence:** recorded in [`docs/REFERENCE_REFRESH_LOG.md`](../../docs/REFERENCE_REFRESH_LOG.md).

## What this run does not claim

- Differentiable runtime shield product guarantees (see `docs/DIFFERENTIATION_PUBLIC_STANCE.md`)
- Universal batch speedup on all micro-scenarios (viability only; see `docs/SOLVER_PATHS_AND_BATCHING.md`)
- Full upstream navigation-session graph unless capture provenance documents a richer dump

## Ops

- Refresh procedure: [`docs/HOST_REALISTIC_REFRESH_PROCEDURE.md`](../../docs/HOST_REALISTIC_REFRESH_PROCEDURE.md)
- Catalog spec: [`docs/PUBLISHED_BUNDLE_CATALOG.md`](../../docs/PUBLISHED_BUNDLE_CATALOG.md)
- Bundle file profile: `python scripts/validate_published_bundle_profile.py`

