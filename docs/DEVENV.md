# Development environment

Supported Python, default CI, and local test filters. Align with [`.github/workflows/ci.yml`](../.github/workflows/ci.yml), [`pyproject.toml`](../pyproject.toml), and [`MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md`](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md).

## Supported Python

| Context | Versions |
| -------- | -------- |
| Package | `>=3.11` (`requires-python`) |
| Governed builds | **3.11, 3.12** (`packaging/install_matrix.json`) |
| Default CI | **3.11, 3.12** on Ubuntu |
| Windows public CI (`windows-ci`) | **3.12** on `windows-latest` (**required** public check) |
| Vendor CI (`vendor-ci-moreau`) | **3.11** with `.[solver-moreau-cpu]` or `.[solver-moreau-cuda]` + Moreau license |

Moreau-backed work: use Linux/WSL2 or the **Windows Moreau sidecar** (qualification; see [WINDOWS_OPERATING_MODES.md](WINDOWS_OPERATING_MODES.md)). Native Windows uses **public** backends only — there is **no** native Moreau-on-Windows support claim.

## Dependency extras (no surprise CUDA)

| Extra | Purpose |
|-------|---------|
| `solver-public` | Clarabel + SCS (CPU). No Moreau, no CUDA. |
| `solver-moreau-cpu` | Vendor Moreau CPU (Linux/WSL). |
| `solver-moreau-cuda` | Vendor Moreau + CUDA (explicit opt-in). |
| `diff-torch` / `diff-jax` | Optional differentiation stacks. |
| `dev` | Pytest/ruff/mypy/etc. |
| `solver` | **Deprecated** alias of CPU Moreau (was historically CUDA). |

Exact pins: `packaging/constraints/`. Matrix: `packaging/install_matrix.json`. Production vs quarantine: `packaging/solver_stack_policy.json`.

```bash
python -m pip install -e ".[dev,solver-public]" -c packaging/constraints/solver-public.txt
conicshield solver-doctor --json
```

## Linux / WSL: virtualenv required

On Debian/Ubuntu (including WSL2), system Python is externally managed. Create and activate a venv first:

```bash
cd /path/to/conicshield
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,solver-public]"
make onboard
```

Re-activate in each new shell: `source .venv/bin/activate`.

### WSL paths

Use Linux paths in bash (`/mnt/c/Users/...`). Do not use `cd c:\...` in bash.

### Git Bash on Windows

If `python` fails with `No Python at '/usr/bin/python.exe'`, the `.venv` was created in WSL. Recreate on Windows or run vendor work in WSL.

## Default CI checks (PR / main) — meanings

| Check | Workflow | Meaning |
|-------|----------|---------|
| **quality** | `ci.yml` | Ruff, mypy, public pytest+coverage, min executed tests, schema compatibility, fallback/fail-safe tests, smoke artifacts |
| **conic-trusted-shape** | `ci.yml` | CLARABEL/SCS-only trusted conic structural shape (no vendor Moreau) |
| **governance-audit** | `governance-audit.yml` | Index/authority audit + publish rehearsal |
| **reference-authority** | `reference-authority.yml` | Cadence, `verify-reference-system` (read-only), community-verify, `verify-v1-lock-quick`; **fails if verify dirties the worktree** |
| **solver-touch** | `solver-touch.yml` | Path-filtered parity/governance/verification/platform tests when solver-touch paths change |
| **windows-ci** | `windows-ci.yml` | **Required** Windows public Clarabel qualification (no native Moreau-on-Windows claim) |

**vendor-ci-moreau** is attestation under Policy B (licensed Moreau). It sets `CONICSHIELD_VENDOR_REQUIRED=1`, runs `python -m moreau check`, mandatory known-feasible native + failure-policy checks, JUnit pytest, and a post-test evidence gate that **fails on zero executes / vendor skips / zero native solves**.

**solver-stack-qualification** (scheduled) exercises the approved stack and lists quarantine candidates without promoting them into `packaging/constraints/`.

## Generate vs check / verify (CS-SOLVER-007)

| Kind | Examples | May write committed files? |
|------|----------|----------------------------|
| `generate-*` / `sync-*` / `refresh-*` | `make sync-community-metadata`, `make sync-published-run-readmes` | Yes |
| `check-*` / `verify-*` / `audit-*` | `make check-community-metadata`, `make verify-reference-system`, `make verify-v1-lock` | No |

CI runs `scripts/assert_git_clean.py` after verification jobs. Prefer `--check` modes on synchronizers.

```bash
make check-community-metadata
make verify-reference-system
make assert-git-clean
make verify-v1-lock-quick
```

## Pytest markers

Default suite excludes: `vendor_moreau`, `requires_moreau`, `solver`, `inter_sim_rl`, `slow`.

```bash
make test
make test-vendor-moreau    # needs Moreau + license; set CONICSHIELD_VENDOR_REQUIRED=1 to harden skips
make test-slow
make verify-extended       # ruff + mypy + cov-gates + slow + strict audit
```

## Vendor Moreau (local)

Follow [MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md) and `scripts/bootstrap_moreau.sh` / `.ps1`. Official install: [Moreau docs](https://docs.moreau.so/installation.html).

```bash
export CONICSHIELD_VENDOR_REQUIRED=1
python -m moreau check
python scripts/vendor_mandatory_native_solves.py --out /tmp/mandatory.json
python -m pytest tests/ -q -m "solver or requires_moreau" --junitxml=/tmp/vendor.junit.xml
python scripts/assert_vendor_ci_evidence.py --junit /tmp/vendor.junit.xml --native-evidence /tmp/mandatory.json
```

## Related

- Windows modes: [WINDOWS_OPERATING_MODES.md](WINDOWS_OPERATING_MODES.md)
- Public entry: [COMMUNITY_LAYER.md](COMMUNITY_LAYER.md)
- Contributing: [CONTRIBUTING.md](../CONTRIBUTING.md)
- Solver paths: [SOLVER_PATHS_AND_BATCHING.md](SOLVER_PATHS_AND_BATCHING.md)
- Stabilization ledger: [stabilization/issue_ledger.json](stabilization/issue_ledger.json)
