# Development environment and CI matrix

Single reference for **supported Python**, **default CI**, **optional workflows**, and **solver** integration. Keep this aligned with [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) and [`pyproject.toml`](../pyproject.toml). Normative Moreau policy: [`docs/MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md`](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md).

## Supported Python

| Context | Versions | Notes |
| -------- | -------- | ----- |
| Package | `>=3.11` | [`pyproject.toml`](../pyproject.toml) `requires-python` |
| Trove classifiers | 3.11, 3.12 | Declared supported language versions |
| Default CI | **3.11, 3.12** | Ubuntu, locked dev requirements + editable install |
| vendor-ci-moreau | **3.11** | Ubuntu, `.[solver]` + Gemfury index + Moreau license |

For Moreau-backed development, use Linux/WSL2. Treat green **Vendor CI track** (`vendor-ci-moreau`) (or a licensed local vendor-mode run) as the oracle for native stack health.

## Base CI (`ci.yml`)

On every PR and push to `main`:

- Ruff check and format check
- Mypy on `conicshield` and `tests`
- Pytest with coverage over `conicshield`

Install path matches contributor setup: `pip install -e ".[dev]"` in public/reference mode.

## Default pytest marker filter

[`pyproject.toml`](../pyproject.toml) excludes from the default suite:

- `vendor_moreau`, `requires_moreau` — need vendor Moreau install and license
- `solver` — solver-related tests (reference and/or vendor paths)
- `inter_sim_rl` — needs fork checkout or `INTERSIM_RL_ROOT`
- `slow` — stress-scale replay and other subprocess-heavy tests

Run everything including slow tests locally:

```bash
python -m pytest tests/ -q -m "slow or not slow" --durations=15
```

Or override addopts:

```bash
python -m pytest tests/ -q --override-ini addopts="-q --durations=15"
```

## Vendor CI track (`vendor-ci-moreau`)

Manual **`workflow_dispatch`** only in [`.github/workflows/solver-ci.yml`](../.github/workflows/solver-ci.yml). Requires repository secrets: `GEMFURY_TOKEN`, `MOREAU_LICENSE_KEY`.

Runs solver-marked tests, solver smoke CLI, optional `reference_run` bundle (validated), a **full verification bundle** (env, vendor smoke, reference correctness, performance + latency PNG, differentiation stub, native parity, **`artifact_validation_report`** on the reference bundle, **`generate_parity_report`**, trust dashboard) uploaded as **`vendor_verification_bundle`**, plus artifacts `ref_bundle_ci` and `vendor_solver_versions` (`solver_versions.json`), and appends a filtered `pip freeze` (moreau/cvxpy/cvxpylayers) to the job Summary for copying into [`ENGINEERING_STATUS.md`](ENGINEERING_STATUS.md).

## Other workflows (path-filtered or manual)

Under `.github/workflows/`: governance audit, governance dashboard, fixture policy, native parity (replay), inter-sim-rl, release orchestration, publish-benchmark. See each file’s `on:` triggers.

## Vendor Moreau install (local)

Use Linux/WSL2 and follow [`README.md`](../README.md), [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md), and `scripts/bootstrap_moreau.sh`. Do not assume default-index `pip install moreau` is valid for this repository.

## Verification ladder

Verification ladder (layers, commands, artifacts): [`docs/VERIFICATION_AND_STRESS_TEST_PLAN.md`](VERIFICATION_AND_STRESS_TEST_PLAN.md).

On each PR/push, **ci.yml** runs `environment_check`, `smoke_check`, `differentiation_check`, and `generate_trust_dashboard`, then uploads the `output/` directory as the **`verification-output-<python-version>`** artifact (download from the workflow run).

## Related

- Vendor API re-verification: [`docs/MOREAU_API_NOTES.md`](MOREAU_API_NOTES.md)
- First publish sequence: [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md)
- Slow tests only: `make test-slow` (see [`tests/test_replay_stress_slow.py`](../tests/test_replay_stress_slow.py))
- One-shot extended gate (static + cov-gates + slow + inter_sim e2e + strict audit): `make verify-extended` (see runbook *Extended local verification*)
