# Engineering status

What is implemented in-tree versus what still needs vendor access, upstream alignment, or operational steps. For **roadmap and external dependencies**, see [`ROADMAP.md`](ROADMAP.md). For **commands and publish flow**, see [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md).

**Documentation index:** [`README.md`](../README.md) (documentation map).

## In the repository today

- Package `conicshield/`: reference path (`CVXPYMoreauProjector`, `cp.MOREAU`) and native path (`NativeMoreauCompiledProjector`, `moreau.Solver`) for the same QP family; telemetry and structured solver errors.
- **Solver smoke CLI:** `python -m conicshield.core.solver_smoke_cli`
- Schemas under `schemas/`, benchmark registry and releases, parity fixture under `tests/fixtures/parity_reference/`, governance and artifact validation CLIs.
- **Default CI** (`.github/workflows/ci.yml`): Python 3.11/3.12, ruff, mypy, pytest with coverage — **no solver extras**; default pytest excludes `solver`, `requires_moreau`, `inter_sim_rl`, `slow` (see [`DEVENV.md`](DEVENV.md)).
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

## Validated solver stack

After a green **Vendor CI** or local `make test-solver` on a licensed machine, record versions for auditability:

| Package       | Version (pip) | Date validated (UTC) | Notes        |
| ------------- | ------------- | -------------------- | ------------ |
| `moreau`      | _from CI Summary or `pip freeze`_ | | Vendor wheel |
| `cvxpy`       | _from CI Summary or `pip freeze`_ | | `pyproject` lower bound |
| `cvxpylayers` | _from CI Summary or `pip freeze`_ | | `pyproject` lower bound |

The Vendor CI job uploads `solver_versions.json` and may append a filtered `pip freeze` to the job Summary for copying here.

```bash
pip install -e ".[solver,dev]" --extra-index-url "https://<TOKEN>:@pypi.fury.io/optimalintellect/"
python -m pip freeze | findstr /i "moreau cvxpy cvxpylayers"
```

## Published benchmark family

- **Registry:** [`benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json`](../benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json) — `state` stays `uninitialized` until the first governed publish.
- **Governance:** [`BENCHMARK_GOVERNANCE.md`](BENCHMARK_GOVERNANCE.md); machine-readable metrics per run in `summary.json`; consolidated dashboard via `dashboard_cli` (see [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md)).
- **Decision template:** [`benchmarks/templates/governance_decision.template.md`](../benchmarks/templates/governance_decision.template.md)

Operational sequence (validate → parity → finalize → release → publish → audit): [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md).
