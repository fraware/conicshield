# Reference authority

ConicShield is maintained as a **governed reference system** for one primary benchmark family (`conicshield-transition-bank-v1`). This page is the single map of what “reference authority” means in practice.

## Flagship release

| Item | Value |
|------|--------|
| Family | `conicshield-transition-bank-v1` |
| `current_run_id` | **`host-realistic-20260525`** |
| Evidence tier | `vendor_native` (`RUN_PROVENANCE.json`) |
| Export | [`benchmarks/external_evidence/offline_graph_export_upstream.json`](../benchmarks/external_evidence/offline_graph_export_upstream.json) |
| Integrity | [`benchmarks/PUBLISHED_RUN_INDEX.json`](../benchmarks/PUBLISHED_RUN_INDEX.json) (schema v2) |

Historical bundles (`wsl-real-*`, `wsl-native-*`) remain in `benchmark_bundle_paths` for comparison.

## Closed loop (in-repo)

```text
export → transition_bank → reference_run → published_runs/<run_id>/ → parity → finalize → release
```

Orchestration: [`scripts/run_host_realistic_publish.py`](../scripts/run_host_realistic_publish.py), [`scripts/upgrade_host_realistic_vendor.py`](../scripts/upgrade_host_realistic_vendor.py).

## Maintainer gates

| Gate | Command |
|------|---------|
| Reference authority (index + audit + flagship) | `make reference-authority-check` or `python scripts/reference_authority_check.py` |
| Refresh committed snapshot | `make reference-authority-snapshot` → `benchmarks/reports/reference_authority_snapshot.json` |
| Public verification bundle | `make verify-reference-system` |
| Strict governance audit | `python -m conicshield.governance.audit_cli --strict` |

## Solver evidence (three paths)

See [`SOLVER_PATHS_AND_BATCHING.md`](SOLVER_PATHS_AND_BATCHING.md): reference CVXPY, sequential native (`batch_size=1`), true compiled batch (`NATIVE_MOREAU_BATCH`).

## Merge trust (binding)

Solver-touching PRs require documented vendor proof (`vendor-ci-moreau` or maintainer attestation). See [`CI_MERGE_GATES.md`](CI_MERGE_GATES.md), [`BRANCH_PROTECTION.md`](BRANCH_PROTECTION.md).

## Repeatable host-realistic operations

Scheduled or event-driven refresh: [`HOST_REALISTIC_REFRESH_PROCEDURE.md`](HOST_REALISTIC_REFRESH_PROCEDURE.md), `make host-realistic-refresh-cycle`.

## Optional refresh

| When | Action |
|------|--------|
| Live inter-sim dump available | `python scripts/refresh_live_upstream_export.py --graph-json <dump.json>` then `make host-realistic-refresh-cycle` |
| Governance only | `python scripts/upgrade_host_realistic_vendor.py --refresh-governance` |

## Explicitly deferred

- Production shield autograd product claims (FD validation only)
- Second benchmark family until published
- `progress` / `clearance` constraint semantics

See [`ROADMAP.md`](ROADMAP.md) open backlog.
