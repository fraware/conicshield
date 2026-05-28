# Published run `wsl-native-20260409-091141`

Governed benchmark bundle for `conicshield-transition-bank-v1`.

| Field | Value |
|-------|--------|
| `evidence_tier` | `vendor_native` |
| `projector_mode` | `real_projector` |
| Host-realistic export evidence | no |
| Includes `shielded-native-moreau` | yes |
| Parity fixture gold source | no |
| Family `current_run_id` | no |
| Governance `state` | `published` |
| Committed export `export_kind` | `live_upstream_dump` |
| Parity status | `n/a` |
| Machine-readable scope | [`COMMUNITY_METADATA.json`](COMMUNITY_METADATA.json) |

## What this run proves

- Validated artifact surface (`validate_run_bundle`)
- Benchmark arms in `summary.json` with governance gates in `governance_status.json`
- Host-realistic export → bank → publish → parity loop is closed in-repo when `host_realistic` is yes

## Evidence qualification

## What this run does not claim

- Differentiable runtime shield product guarantees (see `docs/DIFFERENTIATION_PUBLIC_STANCE.md`)
- Universal batch speedup on all micro-scenarios (viability only; see `docs/SOLVER_PATHS_AND_BATCHING.md`)
- Full upstream navigation-session graph unless capture provenance documents a richer dump

## Ops

- Refresh procedure: [`docs/HOST_REALISTIC_REFRESH_PROCEDURE.md`](../../docs/HOST_REALISTIC_REFRESH_PROCEDURE.md)
- Catalog spec: [`docs/PUBLISHED_BUNDLE_CATALOG.md`](../../docs/PUBLISHED_BUNDLE_CATALOG.md)
- Consume index: [`docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md`](../../docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md)
- Bundle file profile: `python scripts/validate_published_bundle_profile.py`

