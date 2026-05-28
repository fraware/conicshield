# Architecture

## Mission

Proof-aware runtime safety + governed benchmarks. Policy proposes actions; ConicShield projects to the nearest admissible action under `SafetySpec`; evidence and publication gates decide what claims are allowed.

## Layers

| Layer | Responsibility |
|-------|----------------|
| Policy | Q-values / scores |
| Shield | Simplex + constraints + decode (`simplex`, `turn_feasibility`, `box`, `rate`) |
| Solver | Reference (CVXPY/Moreau); native sequential; native compiled batch |
| Evidence | Interventions, timing, solver status |
| Benchmark | Frozen banks → validated bundles |
| Governance | `review-locked` → `published`; family forks on contract change |

`progress` / `clearance`: schema only — [adr/001](adr/001-progress-clearance-constraints.md).

## Solver paths

| Mode | API |
|------|-----|
| Reference | `CVXPYMoreauProjector` |
| Sequential native | `Backend.NATIVE_MOREAU` |
| Compiled batch | `Backend.NATIVE_MOREAU_BATCH` |

Parity binds native to reference on frozen fixture. Detail: [`SOLVER_PATHS_AND_BATCHING.md`](SOLVER_PATHS_AND_BATCHING.md).

## Governance flow

```text
parity_summary → finalize_cli → governance_status (review-locked)
  → governance_decision.md (approve) → release_cli → CURRENT.json / HISTORY
```

`finalize_cli --sync-current-release`: refresh gate columns on published `current_run_id` without new `run_id`.

## Layout

| Path | Content |
|------|---------|
| `conicshield/` | Package |
| `schemas/` | Bundle + context schemas |
| `benchmarks/published_runs/` | Committed governed bundles |
| `benchmarks/runs/` | Ephemeral (gitignored) |
| `benchmarks/external_evidence/` | Flagship export |
| `tests/fixtures/parity_reference/` | Parity gold |
| `scripts/` | Refresh, reports, checks |

## Reference system (v1)

Flagship: `host-realistic-20260525`. Map: [`REFERENCE_AUTHORITY.md`](REFERENCE_AUTHORITY.md).

## Related

[`VERIFICATION_AND_STRESS_TEST_PLAN.md`](VERIFICATION_AND_STRESS_TEST_PLAN.md), [`BENCHMARK_GOVERNANCE.md`](BENCHMARK_GOVERNANCE.md), [`README.md`](README.md).
