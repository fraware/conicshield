# Engineering status

What is implemented in-tree versus what still needs vendor access, upstream alignment, or operational steps. For **roadmap and external dependencies**, see [`ROADMAP.md`](ROADMAP.md). For **commands and publish flow**, see [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md).

**Documentation index:** [`README.md`](../README.md) (documentation map).

## In the repository today

- Package `conicshield/`: reference path (`CVXPYMoreauProjector`, `cp.MOREAU`) and native path (`NativeMoreauCompiledProjector`, `moreau.CompiledSolver` with batch size 1, shared CSR structure per spec; `NativeMoreauCompiledOptions.use_compiled_solver=False` forces legacy `moreau.Solver`) for the same QP family; telemetry and structured solver errors.
- **Solver smoke CLI:** `python -m conicshield.core.solver_smoke_cli`
- Schemas under `schemas/`, benchmark registry and releases, parity fixture under `tests/fixtures/parity_reference/`, governance and artifact validation CLIs.
- **Default CI** (`.github/workflows/ci.yml`): jobs **`quality`** (Python 3.11/3.12: ruff, mypy, pytest with coverage — **no solver extras**; default pytest excludes `solver`, `requires_moreau`, `inter_sim_rl`, `slow`) and **`conic-trusted-shape`** (Python 3.12 only: [`tests/reference/test_reference_conic_trusted_shape.py`](../tests/reference/test_reference_conic_trusted_shape.py) — CLARABEL/SCS-only structural checks; no vendor Moreau). See [`DEVENV.md`](DEVENV.md). Full Moreau-vs-reference agreement remains in `tests/reference/test_reference_conic_correctness.py` (vendor / `make test-solver`).
- **Published benchmark bundles:** each `current_run_id` in a family `CURRENT.json` should have committed artifacts under [`benchmarks/published_runs/<run_id>/`](../benchmarks/published_runs/README.md) (see [`benchmarks/runs/README.md`](../benchmarks/runs/README.md)).
- **Tests** cover bundle validation, replay, parity gates, governance publish chain, audit, and related adapters. `make cov-gates` enforces coverage thresholds on selected packages.
- **inter-sim-rl pin:** [`tests/test_third_party_pins.py`](../tests/test_third_party_pins.py) checks `third_party/inter-sim-rl/REVISION` against the checkout when `.git` exists.
- **Manual Vendor CI** (`vendor-ci-moreau` in `.github/workflows/solver-ci.yml`): optional workflow with secrets for full solver stack, smoke, reference bundle, and verification artifacts.

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

- **Registry:** [`benchmarks/registry.json`](../benchmarks/registry.json) lists families. **Primary:** [`benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json`](../benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json) — `published`, green artifact/promotion/parity gates, reference arms publishable (native arm listing still requires a `shielded-native-moreau` row in the run `summary.json`). **Second harness (scaffold):** [`benchmarks/releases/conicshield-shield-qp-micro-v1/CURRENT.json`](../benchmarks/releases/conicshield-shield-qp-micro-v1/CURRENT.json) — `uninitialized` until a first governed publish.
- **Governance:** [`BENCHMARK_GOVERNANCE.md`](BENCHMARK_GOVERNANCE.md); machine-readable metrics per run in `summary.json`; consolidated dashboard via `dashboard_cli` (see [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md)).
- **Decision template:** [`benchmarks/templates/governance_decision.template.md`](../benchmarks/templates/governance_decision.template.md) — copy to the run dir as `governance_decision.md` before a real `release_cli` (not used by `finalize_cli` or `release_cli --dry-run`).

Operational sequence (validate → parity → finalize → release → publish → audit): [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md).
