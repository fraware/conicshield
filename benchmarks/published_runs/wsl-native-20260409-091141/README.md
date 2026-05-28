# Published run `wsl-native-20260409-091141`

Governed benchmark bundle `wsl-native-20260409-091141` at evidence tier `vendor_native`.

| Field | Value |
|-------|--------|
| `evidence_tier` | `vendor_native` |
| `projector_mode` | `real_projector` |
| Host-realistic | no |
| Native arm (`shielded-native-moreau`) | yes |
| Parity fixture gold source | no |
| Family `current_run_id` | no |
| Export `export_kind` | `live_upstream_dump` |
| Parity status | `n/a` |
| Scope contract | [`COMMUNITY_METADATA.json`](COMMUNITY_METADATA.json) |

## What this run proves

- Validator-required bundle surface passes `validate_run_bundle`
- `summary.json` arms with governance gates recorded in `governance_status.json`

## What this run does not prove

- Production differentiable shield / autograd product ([`docs/DIFFERENTIATION_PUBLIC_STANCE.md`](../../docs/DIFFERENTIATION_PUBLIC_STANCE.md))
- Universal batch speedup ([`docs/SOLVER_PATHS_AND_BATCHING.md`](../../docs/SOLVER_PATHS_AND_BATCHING.md))
- Full Maps/session navigation graph (fork topology unless provenance says otherwise)

## Validate and inspect

```bash
python -m conicshield.published_runs.cli verify wsl-native-20260409-091141
python -m conicshield.artifacts.validator_cli --run-dir benchmarks/published_runs/wsl-native-20260409-091141
python scripts/validate_published_bundle_profile.py --run-id wsl-native-20260409-091141
```

Python API:

```python
from conicshield.published_runs import load_run, load_summary, verify_run
verify_run('wsl-native-20260409-091141')
bundle = load_run('wsl-native-20260409-091141')
```

## Further reading

- Consumer guide: [`docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md`](../../docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md)
- Citation: [`docs/CITING_CONICSHIELD_ARTIFACTS.md`](../../docs/CITING_CONICSHIELD_ARTIFACTS.md)
- Maintainer refresh: [`docs/HOST_REALISTIC_REFRESH_PROCEDURE.md`](../../docs/HOST_REALISTIC_REFRESH_PROCEDURE.md)

