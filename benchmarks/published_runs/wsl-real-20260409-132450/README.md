# Published run `wsl-real-20260409-132450`

Governed benchmark bundle for `conicshield-transition-bank-v1`.

| Field | Value |
|-------|--------|
| `evidence_tier` | `vendor_reference` |
| `projector_mode` | `real_projector` |
| Host-realistic export evidence | no |
| Includes `shielded-native-moreau` | no |
| Parity fixture gold source | yes |
| Family `current_run_id` | no |
| Governance `state` | `review-locked` |
| Committed export `export_kind` | `live_upstream_dump` |
| Parity status | `n/a` |
| Machine-readable scope | [`COMMUNITY_METADATA.json`](COMMUNITY_METADATA.json) |

## What this run proves

- Validated artifact surface (`validate_run_bundle`)
- Benchmark arms in `summary.json` with governance gates in `governance_status.json`
- Host-realistic export → bank → publish → parity loop is closed in-repo when `host_realistic` is yes

## Solver stack

- `cvxpy`: `1.8.2`
- `cvxpylayers`: `1.0.4`
- `moreau`: `0.3.0`

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

