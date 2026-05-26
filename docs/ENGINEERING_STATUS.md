# Engineering status

What is implemented in-tree versus what still needs vendor access, upstream alignment, or operational steps. For **roadmap and external dependencies**, see [`ROADMAP.md`](ROADMAP.md). For **commands and publish flow**, see [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md).

**Documentation index:** [`README.md`](../README.md) (documentation map).

## In the repository today

- Package `conicshield/`: reference path (`CVXPYMoreauProjector`, `cp.MOREAU`) and native path (`NativeMoreauCompiledProjector`, `moreau.CompiledSolver` with batch size 1, shared CSR structure per spec; `NativeMoreauCompiledOptions.use_compiled_solver=False` forces legacy `moreau.Solver`) for the same QP family; **`NativeMoreauCompiledBatchProjector`** for true multi-problem batch solves; optional batched softmax path on `InterSimConicShield`; telemetry and structured solver errors.
- **Solver smoke CLI:** `python -m conicshield.core.solver_smoke_cli`
- Schemas under `schemas/`, benchmark registry and releases, parity fixture under `tests/fixtures/parity_reference/` (promoted from a committed reference bundle; see [`REGENERATION_NOTE.md`](../tests/fixtures/parity_reference/REGENERATION_NOTE.md)), governance and artifact validation CLIs.
- **Default CI** (`.github/workflows/ci.yml`): jobs **`quality`** and **`conic-trusted-shape`** (public lane; no vendor secrets). **`governance-audit.yml`** checks published-run index drift on every PR. **[`solver-touch.yml`](../.github/workflows/solver-touch.yml)** (path-filtered) runs index integrity, native-arm evidence, and parity tests. **[`solver-ci.yml`](../.github/workflows/solver-ci.yml)** (`vendor-ci-moreau`): hybrid policy — `pull_request` on solver paths for the canonical repo plus `workflow_dispatch`. See [`CI_MERGE_GATES.md`](CI_MERGE_GATES.md) and [`BRANCH_PROTECTION.md`](BRANCH_PROTECTION.md). Full Moreau-vs-reference agreement remains vendor-only (`make test-solver`).
- **Published benchmark bundles:** each `current_run_id` in a family `CURRENT.json` should have committed artifacts under [`benchmarks/published_runs/<run_id>/`](../benchmarks/published_runs/README.md) (see [`benchmarks/runs/README.md`](../benchmarks/runs/README.md)). **[`PUBLISHED_RUN_INDEX.json`](../benchmarks/PUBLISHED_RUN_INDEX.json)** (schema v2) records SHA-256 for required bundle files and optional sidecars; see [`conicshield/published_run_index.py`](../conicshield/published_run_index.py) constants.
- **Tests** cover bundle validation, replay, parity gates, governance publish chain, audit, and related adapters. `make cov-gates` enforces coverage thresholds on selected packages.
- **inter-sim-rl pin:** [`tests/environment/test_third_party_pins.py`](../tests/environment/test_third_party_pins.py) checks `third_party/inter-sim-rl/REVISION` against the checkout when `.git` exists.
- **Host-realistic evidence:** [`benchmarks/external_evidence/`](../benchmarks/external_evidence/), published run `host-realistic-20260525`, orchestration [`scripts/run_host_realistic_publish.py`](../scripts/run_host_realistic_publish.py). Passthrough rehearsal until licensed `--no-passthrough` upgrade.
- **Native batching (first-class):** `Backend.NATIVE_MOREAU_BATCH`, [`scripts/batch_solve_report.py`](../scripts/batch_solve_report.py).
- **Layer F (differentiation):** partial — finite-difference sanity via `differentiation_check.py`; shield autograd vs production QP is **deferred** (not a public capability claim).

## Local verification

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -e .
make lint typecheck cov
```

**Broader gate (no solver solve in default CI):** `make verify-extended` — adds slow tests, optional inter-sim e2e (skips without checkout), strict `audit_cli`. With a licensed stack, add `make test-solver`, `make smoke-solver`, `make parity-native-licensed` as in [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md).

## Not implemented yet (projection)

Constraint kinds `progress` and `clearance` raise `NotImplementedError` in [`conicshield/specs/shield_qp.py`](../conicshield/specs/shield_qp.py). See [adr/001-progress-clearance-constraints.md](adr/001-progress-clearance-constraints.md).

**v1 scope:** They are **not** part of solver-backed v1. Treat them as deferred until an explicit product decision promotes them; do not imply parity or native coverage for those kinds in release language until implemented.

## Validated solver stack

Pinned **dev lockfile** versions (public CI) and project lower bounds; replace the `moreau` row with the exact wheel from **Vendor CI** `solver_versions.json` when you run a licensed stack.

| Package       | Version (reference) | Date validated (UTC) | Notes        |
| ------------- | ------------------- | -------------------- | ------------ |
| `moreau`      | `0.3.0` (vendor wheel; not in public `requirements-dev.txt`) | 2026-04-09 | WSL licensed stack; pair with Vendor CI / `solver_versions.json` when automating |
| `cvxpy`       | `1.8.2` (`requirements-dev.txt`); project `>=1.8.2` | 2026-04-09 | Last full-stack check with row above |
| `cvxpylayers` | `1.0.4` (`requirements-dev.txt`); project `>=1.0.4` | 2026-04-09 | Required with `cp.MOREAU` |

The Vendor CI job uploads `solver_versions.json` and may append a filtered `pip freeze` to the job Summary for copying here.

After each green **vendor-ci-moreau** run, copy the **exact** `moreau` wheel version string from the uploaded `solver_versions.json` (or the job Summary table) into the first row above and set **Date validated** to the workflow run date (UTC). Do not guess from the public PyPI index.

```bash
pip install -e ".[solver,dev]" --extra-index-url "https://<TOKEN>:@pypi.fury.io/optimalintellect/"
python -m pip freeze | findstr /i "moreau cvxpy cvxpylayers"
```

## Published benchmark family

- **Registry:** [`benchmarks/registry.json`](../benchmarks/registry.json) lists families. **Primary:** [`benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json`](../benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json) — `published`, green gates; `publishable_arms` includes native when parity and promotion gates allow. Committed bundles: `benchmark_bundle_paths` in `CURRENT.json` and trees under [`benchmarks/published_runs/`](../benchmarks/published_runs/README.md). **Second harness (scaffold):** [`benchmarks/releases/conicshield-shield-qp-micro-v1/CURRENT.json`](../benchmarks/releases/conicshield-shield-qp-micro-v1/CURRENT.json) — `uninitialized` until a first governed publish.
- **Governance:** [`BENCHMARK_GOVERNANCE.md`](BENCHMARK_GOVERNANCE.md); machine-readable metrics per run in `summary.json`; consolidated dashboard via `dashboard_cli` (see [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md)).
- **Decision template:** [`benchmarks/templates/governance_decision.template.md`](../benchmarks/templates/governance_decision.template.md) — copy to the run dir as `governance_decision.md` before a real `release_cli` (not used by `finalize_cli` or `release_cli --dry-run`).

Operational sequence (validate → parity → finalize → release → publish → audit): [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md).

**Conic suite JSON report (public solvers):** `python scripts/conic_suite_report.py --profile standard` (optional `--out output/conic_suite_report.json`).
