# Published run `host-realistic-20260525`

Flagship **host-realistic** governed bundle: closed export→bank→publish loop at `vendor_native` with native Moreau arm and family `current_run_id`.

Publication-grade governed benchmark bundle. Read [`COMMUNITY_METADATA.json`](COMMUNITY_METADATA.json) first.

| Field | Value |
|-------|--------|
| `evidence_tier` | `vendor_native` |
| `projector_mode` | `real_projector` |
| Host-realistic | yes |
| Native arm (`shielded-native-moreau`) | yes |
| Parity fixture gold source | no |
| Family `current_run_id` | yes |
| Export `export_kind` | `live_upstream_dump` |
| Export source | `benchmarks/external_evidence/offline_graph_export_upstream.json` |
| Parity status | `present` |
| Governance state | `published` |
| Index integrity | Run `python -m conicshield.published_runs.cli verify` after clone |

## What this run proves

- Validator-required bundle surface passes `validate_run_bundle`
- `summary.json` arms with governance gates recorded in `governance_status.json`
- Host-realistic export → transition bank → publish path is **closed in-repo**

## What this run does not prove

- Production differentiable shield / autograd product ([`docs/DIFFERENTIATION_PUBLIC_STANCE.md`](../../docs/DIFFERENTIATION_PUBLIC_STANCE.md))
- Claim of universal batch throughput win ([`docs/SOLVER_PATHS_AND_BATCHING.md`](../../docs/SOLVER_PATHS_AND_BATCHING.md))
- Full upstream Maps/session navigation graph (fork topology only unless provenance documents more)

## Validate and inspect

```bash
python -m conicshield.published_runs.cli verify host-realistic-20260525
python -m conicshield.published_runs.cli show host-realistic-20260525
python -m conicshield.artifacts.validator_cli --run-dir benchmarks/published_runs/host-realistic-20260525
python scripts/validate_published_bundle_profile.py --run-id host-realistic-20260525
```

Python API (v1 stable — see [`docs/PUBLISHED_RUNS_API.md`](../../docs/PUBLISHED_RUNS_API.md)):

```python
from conicshield.published_runs import load_run, load_summary, load_provenance, verify_run
verify_run('host-realistic-20260525')
bundle = load_run('host-realistic-20260525')
```

## Cite this artifact

Cite the **`run_id`**, repository **commit SHA**, and [`COMMUNITY_METADATA.json`](COMMUNITY_METADATA.json) scope. Distinguish **artifact identity** from scientific conclusions — see [`docs/CITING_CONICSHIELD_ARTIFACTS.md`](../../docs/CITING_CONICSHIELD_ARTIFACTS.md) and [`docs/PUBLIC_CLAIMS.md`](../../docs/PUBLIC_CLAIMS.md).

## Solver stack

- `cvxpy`: `1.8.2`
- `cvxpylayers`: `1.0.4`
- `moreau`: `0.3.0`

## Source export

- `benchmarks/external_evidence/offline_graph_export_upstream.json` (`live_upstream_dump`)
- Authority log: [`docs/REFERENCE_AUTHORITY_LOG.md`](../../docs/REFERENCE_AUTHORITY_LOG.md)
- Export provenance: [`benchmarks/external_evidence/EXPORT_PROVENANCE.json`](../../benchmarks/external_evidence/EXPORT_PROVENANCE.json)

## Further reading

- Consumer guide: [`docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md`](../../docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md)
- Citation: [`docs/CITING_CONICSHIELD_ARTIFACTS.md`](../../docs/CITING_CONICSHIELD_ARTIFACTS.md)
- Maintainer refresh: [`docs/HOST_REALISTIC_REFRESH_PROCEDURE.md`](../../docs/HOST_REALISTIC_REFRESH_PROCEDURE.md)

