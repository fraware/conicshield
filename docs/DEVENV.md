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

### Linux / WSL: venv required (PEP 668)

On Debian/Ubuntu (including WSL2), the system Python is **externally managed**: `pip install` without a virtual environment fails with `externally-managed-environment`. Always create and **activate** a venv first, then run installs and tools with that interpreter.

Many images ship **`python3` only** (`python` may be missing until you use the venv’s `bin/python`).

```bash
cd /path/to/conicshield
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e ".[dev]"
python -m ruff check conicshield tests
```

Re-activate the venv in each new shell: `source .venv/bin/activate` (from the repo root).

### WSL (bash): Windows paths

In **WSL**, use Linux-style paths to the repo (for example `cd /mnt/c/Users/<you>/conicshield`). Do not use `cd c:\...` in bash (it will fail). **PowerShell** on Windows may use `cd C:\Users\<you>\conicshield`.

### Git Bash on Windows: do not reuse a WSL `.venv`

If `make` or `python` fails with `No Python at '/usr/bin/python.exe'`, the active `.venv` was created inside **WSL** (Unix layout under `.venv/bin/`) but you are running **Git Bash** on Windows. Either:

1. **Run vendor work in WSL** (recommended for Moreau): `cd /mnt/c/Users/<you>/conicshield`, `source .venv/bin/activate`, then `make upgrade-host-realistic-vendor`.
2. **Recreate the venv on Windows** from the repo root in Git Bash or PowerShell:

   ```bash
   deactivate 2>/dev/null || true
   rm -rf .venv
   py -3 -m venv .venv
   source .venv/Scripts/activate
   python -m pip install -r requirements-dev.txt
   python -m pip install -e ".[dev]"
   ```

3. **One-off override:** `make PYTHON="py -3" upgrade-host-realistic-vendor`

### Pytest tips

Use `--tb=short` (not `short*`) for short tracebacks. To see **skipped** tests: add `-rs` to pytest.

## Base CI (`ci.yml`)

On every PR and push to `main`:

- **`conic-trusted-shape`** — runs only [`tests/reference/test_reference_conic_trusted_shape.py`](../tests/reference/test_reference_conic_trusted_shape.py) (CLARABEL/SCS structural correctness; no vendor MOREAU).
- **`quality`** — Ruff check and format check, Mypy on `conicshield` and `tests`, full default-marker pytest with coverage over `conicshield`, then verification scripts.
- **`governance-audit`** ([`.github/workflows/governance-audit.yml`](../.github/workflows/governance-audit.yml)) — on every PR/push to `main`: `refresh_published_run_index.py --check` (required + optional integrity surface), `audit_cli`, passthrough publish rehearsal, strict audit.
- **`solver-touch`** ([`.github/workflows/solver-touch.yml`](../.github/workflows/solver-touch.yml)) — path-filtered (see workflow `paths:`). Index checks, host-realistic provenance tests, native-arm evidence, parity. No vendor Moreau required.

Install path matches contributor setup: `pip install -e ".[dev]"` in public/reference mode.

### Merge gates

See [`CI_MERGE_GATES.md`](CI_MERGE_GATES.md). Typical PR checks: **`quality`**, **`conic-trusted-shape`**, **`governance-audit`**, **`reference-authority`**, **`solver-touch`** (path-filtered). **`vendor-ci-moreau`** is Policy B attestation, not a default required check.

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

[`.github/workflows/solver-ci.yml`](../.github/workflows/solver-ci.yml): **`workflow_dispatch`** plus **path-filtered `pull_request`** on the canonical repo (same paths as `solver-touch`). Requires secrets: `GEMFURY_TOKEN`, `MOREAU_LICENSE_KEY`.

Runs solver-marked tests, solver smoke CLI, optional `reference_run` bundle (validated), a **full verification bundle** (env, vendor smoke, reference correctness, performance benchmark + **`batch_solve_report`**, differentiation stub, native parity, **`artifact_validation_report`**, **`generate_parity_report`**, trust dashboard) uploaded as **`vendor_verification_bundle`**, plus `ref_bundle_ci` and `vendor_solver_versions`. See [`CONTRIBUTING.md`](../CONTRIBUTING.md) for fork policy.

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
- One-shot extended gate (ruff check + format check + mypy + `cov-gates` pytest + slow + inter-sim e2e + strict audit): `make verify-extended` (see [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md) *Extended local verification*)
