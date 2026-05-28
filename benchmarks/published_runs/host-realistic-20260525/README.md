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
| Governance `state` | `review-locked` |
| Committed export `export_kind` | `live_upstream_dump` |
| Parity status | `present` |
| Machine-readable scope | [`COMMUNITY_METADATA.json`](COMMUNITY_METADATA.json) |

## What this run proves

- Validated artifact surface (`validate_run_bundle`)
- Benchmark arms in `summary.json` with governance gates in `governance_status.json`
- Host-realistic export → bank → publish → parity loop is closed in-repo when `host_realistic` is yes

## Solver stack

- `cvxpy`: `1.8.2`
- `cvxpylayers`: `1.0.4`
- `moreau`: `0.3.0`

## Source export

- `benchmarks/external_evidence/offline_graph_export_upstream.json` (`export_kind: live_upstream_dump`)

## Evidence qualification

- **Export loop:** closed in-repo; source export is `benchmarks/external_evidence/offline_graph_export_upstream.json` (`export_kind: live_upstream_dump`).
- **Live capture:** when `export_kind` is `live_upstream_dump`, the graph was validated through pinned **inter-sim-rl `RLEnvironment`** (see `benchmarks/external_evidence/live_dumps/*.provenance.json`).
- **Graph content:** host-realistic **fork topology** (Root → NodeA/NodeB/NodeC), not a full Maps/session-built navigation graph unless provenance explicitly says otherwise.
- **Cadence:** [`docs/REFERENCE_AUTHORITY_LOG.md`](../../docs/REFERENCE_AUTHORITY_LOG.md).

## What this run does not claim

- Differentiable runtime shield product guarantees (see `docs/DIFFERENTIATION_PUBLIC_STANCE.md`)
- Universal batch speedup on all micro-scenarios (viability only; see `docs/SOLVER_PATHS_AND_BATCHING.md`)
- Full upstream navigation-session graph unless capture provenance documents a richer dump

## Ops

- Refresh procedure: [`docs/HOST_REALISTIC_REFRESH_PROCEDURE.md`](../../docs/HOST_REALISTIC_REFRESH_PROCEDURE.md)
- Catalog spec: [`docs/PUBLISHED_BUNDLE_CATALOG.md`](../../docs/PUBLISHED_BUNDLE_CATALOG.md)
- Consume index: [`docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md`](../../docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md)
- Bundle file profile: `python scripts/validate_published_bundle_profile.py`

