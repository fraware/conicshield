# Reference authority

Single map for the governed reference system. Family: **`conicshield-transition-bank-v1`**.

## Flagship (`current_run_id`)

| Field | Value |
|-------|--------|
| `run_id` | **`host-realistic-20260525`** |
| `state` | `published` (gates green) |
| `evidence_tier` | `vendor_native` |
| `projector_mode` | `real_projector` |
| Export | [`benchmarks/external_evidence/offline_graph_export_upstream.json`](../benchmarks/external_evidence/offline_graph_export_upstream.json) |
| `EXPORT_PROVENANCE.export_kind` | `live_upstream_dump` |
| Integrity | [`benchmarks/PUBLISHED_RUN_INDEX.json`](../benchmarks/PUBLISHED_RUN_INDEX.json) (schema v2) |
| Snapshot | [`benchmarks/reports/reference_authority_snapshot.json`](../benchmarks/reports/reference_authority_snapshot.json) |

Comparison bundles: `wsl-real-20260409-132450`, `wsl-native-20260409-091141` (`benchmark_bundle_paths` in `CURRENT.json`).

## Evidence qualification (required language)

Use this wording internally and externally:

1. **Closed loop:** export → bank → `reference_run` → `published_runs/<run_id>/` → parity → finalize → release is implemented and CI-governed.
2. **Live export:** `export_kind: live_upstream_dump` means the graph was captured through pinned **inter-sim-rl `RLEnvironment`** ([`live_dumps/*.provenance.json`](../benchmarks/external_evidence/live_dumps/)).
3. **Graph content:** host-realistic **fork** topology (Root → NodeA/NodeB/NodeC), not a Maps/session-built navigation graph.
4. **Not claimed:** universal batch speedup; production shield autograd; second benchmark family operational coverage.

Bundle detail: [`benchmarks/published_runs/host-realistic-20260525/README.md`](../benchmarks/published_runs/host-realistic-20260525/README.md).

## Closed loop

```text
export → transition_bank → reference_run → published_runs/<run_id>/ → parity → finalize → release
```

Scripts: [`run_host_realistic_publish.py`](../scripts/run_host_realistic_publish.py), [`host_realistic_refresh_cycle.py`](../scripts/host_realistic_refresh_cycle.py).

## Maintainer commands

| Task | Command |
|------|---------|
| Full authority gate | `make reference-authority-check` |
| Public evidence pytest bundle | `make verify-reference-system` |
| Refresh snapshot | `make reference-authority-snapshot` |
| Strict audit | `python -m conicshield.governance.audit_cli --strict` |
| Flagship refresh | `make host-realistic-refresh-cycle` (licensed WSL) |

Cadence log: [`REFERENCE_REFRESH_LOG.md`](REFERENCE_REFRESH_LOG.md).

## Solver and batch

Three solve modes: [`SOLVER_PATHS_AND_BATCHING.md`](SOLVER_PATHS_AND_BATCHING.md).

- Reference: `CVXPYMoreauProjector`
- Sequential native: `Backend.NATIVE_MOREAU`, `batch_size=1`
- Compiled batch: `Backend.NATIVE_MOREAU_BATCH`

CI enforces batch **viability** (`speedup_ratio >= 0.98`, `any_row_meets`). **Throughput** (`>= 1.05`) is advisory only.

## Merge policy

Required on `main`: `quality`, `conic-trusted-shape`, `governance-audit`, `reference-authority`, `solver-touch`.

`vendor-ci-moreau` is **not** required (Policy B). Solver-touch PRs need green vendor CI **or** maintainer attestation: [`CI_MERGE_GATES.md`](CI_MERGE_GATES.md), [`REVIEWER_MERGE_CHECKLIST.md`](REVIEWER_MERGE_CHECKLIST.md).

## Deferred (out of v1 claims)

| Item | Doc |
|------|-----|
| Production shield autograd | [`DIFFERENTIATION_PUBLIC_STANCE.md`](DIFFERENTIATION_PUBLIC_STANCE.md) |
| Second family publish | [`conicshield-shield-qp-micro-v1`](../benchmarks/releases/conicshield-shield-qp-micro-v1/FAMILY_README.md) |
| `progress` / `clearance` constraints | [adr/001](adr/001-progress-clearance-constraints.md) |
| Richer upstream navigation graph | Re-capture when `REVISION` or host dump changes |

Backlog: [`ROADMAP.md`](ROADMAP.md).
