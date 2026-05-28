# Development environment

Supported Python, default CI, and local test filters. Align with [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) and [`pyproject.toml`](../pyproject.toml).

## Supported Python

| Context | Versions |
| -------- | -------- |
| Package | `>=3.11` (`requires-python`) |
| Default CI | **3.11, 3.12** on Ubuntu |
| Vendor CI (`vendor-ci-moreau`) | **3.11** with `.[solver]` + Moreau license |

Moreau-backed work: use Linux/WSL2. Green **Vendor CI** or a licensed local run is the oracle for the native stack.

## Linux / WSL: virtualenv required

On Debian/Ubuntu (including WSL2), system Python is externally managed. Create and activate a venv first:

```bash
cd /path/to/conicshield
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
make onboard
```

Re-activate in each new shell: `source .venv/bin/activate`.

### WSL paths

Use Linux paths in bash (`/mnt/c/Users/...`). Do not use `cd c:\...` in bash.

### Git Bash on Windows

If `python` fails with `No Python at '/usr/bin/python.exe'`, the `.venv` was created in WSL. Recreate on Windows or run vendor work in WSL.

## Default CI checks (PR / main)

- **quality** — ruff, mypy, pytest with coverage
- **conic-trusted-shape** — reference conic structural test
- **governance-audit** — index check, audit CLI, publish rehearsal
- **reference-authority** — community-verify, verify-v1-lock-quick
- **solver-touch** — path-filtered; no vendor Moreau required

**vendor-ci-moreau** is optional attestation (Policy B), not a default required check.

## Pytest markers

Default suite excludes: `vendor_moreau`, `requires_moreau`, `solver`, `inter_sim_rl`, `slow`.

```bash
make test
make test-vendor-moreau    # needs Moreau + license
make test-slow
make verify-extended       # ruff + mypy + cov-gates + slow + strict audit
```

## Vendor Moreau (local)

Follow [README.md](../README.md) and `scripts/bootstrap_moreau.sh`. Official install: [Moreau docs](https://docs.moreau.so/installation.html).

## Related

- Public entry: [COMMUNITY_LAYER.md](COMMUNITY_LAYER.md)
- Contributing: [CONTRIBUTING.md](../CONTRIBUTING.md)
