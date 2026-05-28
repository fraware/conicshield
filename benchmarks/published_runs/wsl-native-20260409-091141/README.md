# Published run `wsl-native-20260409-091141`

Governed benchmark artifact `wsl-native-20260409-091141` at tier `vendor_native` (family current run; native arm=True).

Read [`COMMUNITY_METADATA.json`](COMMUNITY_METADATA.json) before `summary.json`.

| Field | Value |
|-------|--------|
| `evidence_tier` | `vendor_native` |
| `projector_mode` | `real_projector` |
| Export `export_kind` | `live_upstream_dump` |
| Graph shape (qualification) | `n/a` — See `RUN_PROVENANCE.json` for export scope. |
| Native arm (`shielded-native-moreau`) | yes |
| Parity status | `n/a` |
| Host-realistic path | no |
| Family `current_run_id` | no |
| Governance state | `published` |

## What this run proves

- Validator-required bundle surface passes `validate_run_bundle`
- `summary.json` arms with governance gates recorded in `governance_status.json`

## What this run does not prove

- Production differentiable shield / autograd product ([`docs/DIFFERENTIATION_PUBLIC_STANCE.md`](../../docs/DIFFERENTIATION_PUBLIC_STANCE.md))
- Claim of universal batch throughput win ([`docs/SOLVER_PATHS_AND_BATCHING.md`](../../docs/SOLVER_PATHS_AND_BATCHING.md))
- Full upstream navigation export (fork topology only unless provenance documents more)

## Verify this artifact

```bash
python -m conicshield.published_runs.cli verify wsl-native-20260409-091141
python -m conicshield.published_runs.cli show wsl-native-20260409-091141
python -m conicshield.published_runs.cli summary wsl-native-20260409-091141
python -m conicshield.published_runs.cli provenance wsl-native-20260409-091141
python -m conicshield.artifacts.validator_cli --run-dir benchmarks/published_runs/wsl-native-20260409-091141
python scripts/validate_published_bundle_profile.py --run-id wsl-native-20260409-091141
```

Canonical API example: [`examples/load_published_runs_api.py`](../../examples/load_published_runs_api.py).

## Cite this artifact

Cite **`run_id`**, repository **commit SHA**, and [`COMMUNITY_METADATA.json`](COMMUNITY_METADATA.json). Artifact identity is not a scientific conclusion — follow [`docs/CITING_CONICSHIELD_ARTIFACTS.md`](../../docs/CITING_CONICSHIELD_ARTIFACTS.md) and [`docs/PUBLIC_CLAIMS.md`](../../docs/PUBLIC_CLAIMS.md).

## Further reading

- Public entry: [`docs/COMMUNITY_LAYER.md`](../../docs/COMMUNITY_LAYER.md)
- Index consumers: [`docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md`](../../docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md)
- Maintainers: [`CONTRIBUTING.md`](../../CONTRIBUTING.md)

