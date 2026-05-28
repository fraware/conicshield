# Published run `wsl-real-20260409-132450`

Governed benchmark bundle `wsl-real-20260409-132450` at evidence tier `vendor_reference`.

| Field | Value |
|-------|--------|
| `evidence_tier` | `vendor_reference` |
| `projector_mode` | `real_projector` |
| Host-realistic | no |
| Native arm (`shielded-native-moreau`) | no |
| Parity fixture gold source | yes |
| Family `current_run_id` | no |
| Export `export_kind` | `live_upstream_dump` |
| Export source | n/a |
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
python -m conicshield.published_runs.cli verify wsl-real-20260409-132450
python -m conicshield.artifacts.validator_cli --run-dir benchmarks/published_runs/wsl-real-20260409-132450
python scripts/validate_published_bundle_profile.py --run-id wsl-real-20260409-132450
```

Python API:

```python
from conicshield.published_runs import load_run, load_summary, verify_run
verify_run('wsl-real-20260409-132450')
bundle = load_run('wsl-real-20260409-132450')
```

## Solver stack

- `cvxpy`: `1.8.2`
- `cvxpylayers`: `1.0.4`
- `moreau`: `0.3.0`

## Further reading

- Consumer guide: [`docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md`](../../docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md)
- Citation: [`docs/CITING_CONICSHIELD_ARTIFACTS.md`](../../docs/CITING_CONICSHIELD_ARTIFACTS.md)
- Maintainer refresh: [`docs/HOST_REALISTIC_REFRESH_PROCEDURE.md`](../../docs/HOST_REALISTIC_REFRESH_PROCEDURE.md)

