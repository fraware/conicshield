# MOREAU Install and Environment Policy

## Purpose

This document defines the official installation, environment, testing, and CI policy for using **Moreau** in this repository.

It is the source of truth for:
- supported development environments,
- how Moreau is installed,
- how licenses are handled,
- how tests are split,
- how CI should behave,
- and how engineers should diagnose failures.

## Executive summary

This repository assumes the **vendor-distributed Moreau solver**, not an arbitrary package that shares the same name on the default public index.

Do not assume:

```bash
pip install moreau
```

from the default public index provides the solver backend required by this repository.

Operationally:
- treat Moreau as a **vendor dependency**,
- install it through the **vendor-approved package source**,
- use a valid **license key**,
- and standardize on **Linux / WSL2** for Moreau-backed development.

## Official policy

### 1) Moreau is a vendor dependency

- Do not rely on default-index `pip install moreau` as the official setup path.
- Do not make vendor Moreau mandatory for all contributors.
- Keep public/reference workflows working without vendor credentials.

Required mindset:
- **public/reference mode** works without vendor access,
- **vendor-accelerated mode** enables Moreau-specific functionality.

### 2) Supported environment

Official runtime for Moreau-backed development:
- Ubuntu Linux, or
- WSL2 Ubuntu on Windows.

Native Windows is treated as unsupported for Moreau-backed development unless explicitly requalified by maintainers.

### 3) Two operating modes

#### Mode A: Public/reference mode

Intended for contributors without vendor access and for open CI.

Expected to work:
- artifacts and validators,
- schema validation,
- governance audit/dashboard/release flows,
- most tests,
- reference optimizer paths using public solvers.

Not required:
- vendor package source,
- Moreau license,
- native Moreau backend.

#### Mode B: Vendor-accelerated mode

Intended for engineers with vendor access.

Requires:
- vendor package source,
- valid Moreau install,
- valid Moreau license,
- Linux/WSL runtime.

Enables:
- `cp.MOREAU`,
- native Moreau tests,
- native parity and benchmark promotion workflows.

### 4) Installation policy

#### 4.1 Baseline setup (public/reference mode)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

#### 4.2 Vendor Moreau setup (vendor mode)

Use `scripts/bootstrap_moreau.sh` for a guided setup, or equivalent commands:

```bash
export MOREAU_EXTRA_INDEX_URL='https://<token>:@pypi.fury.io/optimalintellect/'
export MOREAU_LICENSE_KEY='moreau_v1_...'
python -m pip install "moreau[cuda]" --extra-index-url "$MOREAU_EXTRA_INDEX_URL"
python -m moreau check
```

Important: do not assume default-index installation is equivalent to vendor installation.

### 5) License handling

Allowed:
- `MOREAU_LICENSE_KEY` environment variable,
- `~/.moreau/key` file.

Forbidden:
- committing keys,
- hardcoding keys in scripts,
- writing keys into docs,
- printing keys in CI logs.

### 6) Dependency policy

- Base dependencies include public dependencies used by reference mode.
- Vendor Moreau remains optional and vendor-installed.
- Do not configure base installation to require vendor credentials.

### 7) Bootstrap policy

Repository bootstrap entrypoint:
- `scripts/bootstrap_moreau.sh`

It must:
1. validate OS/runtime,
2. validate vendor index configuration,
3. validate license configuration,
4. install vendor Moreau,
5. run `python -m moreau check`,
6. verify `cvxpy.MOREAU` is available.

### 8) CVXPY integration policy

If a code path uses:

```python
problem.solve(solver=cp.MOREAU)
```

the environment must already contain vendor Moreau and valid integration prerequisites.

If CVXPY reports missing MOREAU solver, treat it as environment/setup issue first.

### 9) Testing policy

Split tests into:
- **core tests** (always runnable),
- **reference tests** (public solver/reference mode),
- **vendor tests** (`vendor_moreau` / `requires_moreau` markers).

Vendor tests run only in vendor-capable environments.

### 10) CI policy

Two tracks are required:
- **open/public CI**: lint, typecheck, core/reference tests, governance checks; no vendor secrets.
- **vendor/protected CI**: vendor install + license + native parity/tests.

In this repository these are represented by:
- `.github/workflows/ci.yml` (public),
- `vendor-ci-moreau` (`.github/workflows/solver-ci.yml`) (vendor).

### 11) Failure guide

- `pip install moreau` works but runtime fails: likely wrong package identity/source.
- `cp.MOREAU` unavailable: vendor integration not installed correctly.
- native Windows issues: move to WSL2/Linux before deeper debugging.
- vendor workflow only failing in CI: likely secrets/license/vendor index path.

### 12) Non-negotiable rules

- Do not trust ambiguous default-index Moreau installs.
- Do not treat native Windows as a qualified Moreau runtime unless explicitly revalidated.
- Do not make vendor Moreau mandatory for all contributors.
- Do not commit secrets.
- Do not publish native benchmark claims without parity gates.
