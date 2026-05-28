# Published run `host-realistic-20260525`

Public **host-realistic** benchmark artifact: a governed, hash-indexed run recording shielded RL episodes at evidence tier `vendor_native` with native Moreau arm and family `current_run_id`.

Read [`COMMUNITY_METADATA.json`](COMMUNITY_METADATA.json) before `summary.json`.

| Field | Value |
|-------|--------|
| `evidence_tier` | `vendor_native` |
| `projector_mode` | `real_projector` |
| Export `export_kind` | `live_upstream_dump` |
| Graph shape (qualification) | `host_realistic_fork` — Host-realistic **fork** via inter-sim `RLEnvironment` (fork topology only; does not prove full upstream navigation export). |
| Native arm (`shielded-native-moreau`) | yes |
| Parity status | `present` |
| Host-realistic path | yes |
| Family `current_run_id` | yes |
| Governance state | `published` |

## Solver stack

- `cvxpy`: `1.8.2`
- `cvxpylayers`: `1.0.4`
- `moreau`: `0.3.0`

## What this run proves

- Validator-required bundle surface passes `validate_run_bundle`
- `summary.json` arms with governance gates recorded in `governance_status.json`
- Host-realistic export → transition bank → publish path is **closed in-repo**

## What this run does not prove

- Production differentiable shield / autograd product ([`docs/DIFFERENTIATION_PUBLIC_STANCE.md`](../../docs/DIFFERENTIATION_PUBLIC_STANCE.md))
- Claim of universal batch throughput win ([`docs/SOLVER_PATHS_AND_BATCHING.md`](../../docs/SOLVER_PATHS_AND_BATCHING.md))
- Full upstream navigation export (fork topology only unless provenance documents more)

## Verify this artifact

```bash
python -m conicshield.published_runs.cli verify host-realistic-20260525
python -m conicshield.published_runs.cli show host-realistic-20260525
python -m conicshield.published_runs.cli summary host-realistic-20260525
python -m conicshield.published_runs.cli provenance host-realistic-20260525
python -m conicshield.artifacts.validator_cli --run-dir benchmarks/published_runs/host-realistic-20260525
python scripts/validate_published_bundle_profile.py --run-id host-realistic-20260525
```

Canonical API example: [`examples/load_published_runs_api.py`](../../examples/load_published_runs_api.py).

## Cite this artifact

Cite **`run_id`**, repository **commit SHA**, and [`COMMUNITY_METADATA.json`](COMMUNITY_METADATA.json). Artifact identity is not a scientific conclusion — follow [`docs/CITING_CONICSHIELD_ARTIFACTS.md`](../../docs/CITING_CONICSHIELD_ARTIFACTS.md) and [`docs/PUBLIC_CLAIMS.md`](../../docs/PUBLIC_CLAIMS.md).

## Source export

- `benchmarks/external_evidence/offline_graph_export_upstream.json` (`live_upstream_dump`)
- [`benchmarks/external_evidence/EXPORT_PROVENANCE.json`](../../benchmarks/external_evidence/EXPORT_PROVENANCE.json)
- Refresh log: [`benchmarks/reports/reference_refresh_log.md`](../../benchmarks/reports/reference_refresh_log.md)

## Further reading

- Public entry: [`docs/COMMUNITY_LAYER.md`](../../docs/COMMUNITY_LAYER.md)
- Index consumers: [`docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md`](../../docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md)
- Maintainers: [`CONTRIBUTING.md`](../../CONTRIBUTING.md)

