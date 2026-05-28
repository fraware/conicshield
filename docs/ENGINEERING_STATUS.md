# Engineering status

What is in-tree vs vendor-only. Roadmap: [`ROADMAP.md`](ROADMAP.md). Commands: [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md).

## In repository

| Area | State |
|------|--------|
| Solvers | CVXPY/Moreau reference; native `CompiledSolver` (batch 1); `NativeMoreauCompiledBatchProjector`; `NATIVE_MOREAU_BATCH` |
| Shield | `InterSimConicShield`; optional `project_softmax_batch` |
| Governance | `finalize_cli`, `release_cli`, `audit_cli`, family manifests |
| CI (public) | `quality`, `conic-trusted-shape`, `governance-audit`, `reference-authority`, path-filtered `solver-touch` |
| CI (vendor) | `vendor-ci-moreau` — Policy B attestation, not required check |
| Flagship | `host-realistic-20260525`, `vendor_native`, `live_upstream_dump` |
| Batch policy | Viability enforced; throughput advisory — [`SOLVER_PATHS_AND_BATCHING.md`](SOLVER_PATHS_AND_BATCHING.md) |
| Differentiation | FD / `--shield-inter-sim` validation only — [`DIFFERENTIATION_PUBLIC_STANCE.md`](DIFFERENTIATION_PUBLIC_STANCE.md) |
| Index | `PUBLISHED_RUN_INDEX.json` v2; `validate_published_bundle_profile.py` |

## Not implemented

| Item | Detail |
|------|--------|
| `progress`, `clearance` constraints | `NotImplementedError` in shield QP — [adr/001](adr/001-progress-clearance-constraints.md) |
| Production shield autograd | Out of public claims |
| Second family publish | `conicshield-shield-qp-micro-v1` uninitialized |

## Validated solver stack

Copy from flagship `solver_versions.json` after each licensed refresh or green `vendor-ci-moreau`.

| Package | Version | Date (UTC) | Source |
|---------|---------|------------|--------|
| `moreau` | `0.3.0` | 2026-05-28 | `benchmarks/published_runs/host-realistic-20260525/solver_versions.json` |
| `cvxpy` | `1.8.2` | 2026-05-28 | `benchmarks/published_runs/host-realistic-20260525/solver_versions.json` |
| `cvxpylayers` | `1.0.4` | 2026-05-28 | `benchmarks/published_runs/host-realistic-20260525/solver_versions.json` |

```bash
pip install -e ".[solver,dev]" --extra-index-url "https://<TOKEN>:@pypi.fury.io/optimalintellect/"
python -m pip freeze | findstr /i "moreau cvxpy cvxpylayers"
```

## Local verification

```bash
make lint typecheck test
make verify-reference-system    # governance + reference evidence
make reference-authority-check  # index + audit + flagship
```

Licensed: `make test-vendor-moreau`, `make parity-native-licensed` — [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md).

## Published family

| Family | `current_run_id` | State |
|--------|------------------|--------|
| `conicshield-transition-bank-v1` | `host-realistic-20260525` | `published` |
| `conicshield-shield-qp-micro-v1` | `null` | `uninitialized` |

Conic suite report (public solvers): `python scripts/conic_suite_report.py --profile standard`
