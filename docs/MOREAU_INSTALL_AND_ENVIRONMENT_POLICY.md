# Moreau install and environment policy

Governed installation profiles, AUTO backend policy, and provenance expectations for ConicShield solver stacks.

Machine-readable matrix: [`packaging/install_matrix.json`](../packaging/install_matrix.json). Exact pins: [`packaging/constraints/`](../packaging/constraints/).

## Profiles

| Extra | CUDA | Vendor credentials | Platforms |
|-------|------|--------------------|-----------|
| `solver-public` | No | No | Linux, macOS, Windows |
| `solver-moreau-cpu` | No | Yes (extra-index + license) | Linux / WSL2 only |
| `solver-moreau-cuda` | Yes | Yes | Linux / WSL2 + NVIDIA |
| `diff-torch` / `diff-jax` | No by default | No | See matrix |
| `dev` | No | No | All supported |

**CPU-only hosts must not install `solver-moreau-cuda`.** Public and Moreau-CPU profiles never declare CUDA package extras.

### Deprecated `solver` extra

Historically `.[solver]` installed `moreau[cuda]`. It now aliases **CPU-only** Moreau to avoid surprise CUDA pulls. Prefer explicit `solver-moreau-cpu` or `solver-moreau-cuda`. Bootstrap scripts emit migration warnings.

Do **not** `pip install moreau` from the default PyPI index. Wrong stubs can import as `moreau` without `CompiledSolver`.

## Supported Python

Governed builds: **3.11 and 3.12**. Other versions fail install markers / bootstrap with actionable errors. See [`DEVENV.md`](DEVENV.md).

## AUTO backend policy

| Selection | Behavior |
|-----------|----------|
| Explicit `CVXPY_MOREAU` / `NATIVE_*` / `PUBLIC_*` | Honored exactly |
| `AUTO` | Uses `CONICSHIELD_PRODUCTION_BACKEND` when set; otherwise **`PUBLIC_CLARABEL`** |
| Importability of `moreau` | **Never** influences AUTO |
| Failure recovery | Must not silently switch production backends; use declared S2 fallback evidence |

Default `create_projector(...)` remains explicit `CVXPY_MOREAU` for compatibility. Pass `backend=Backend.AUTO` for the public default policy.

## Provenance

Package identity is **not** established by `import moreau` alone. Use:

```bash
conicshield solver-doctor --json
# or
python -m conicshield.cli solver-doctor --json
```

The report records Python/OS/arch, executable, environment type, distribution names/versions/locations/hashes when available, installer source when recoverable, Moreau API capabilities, CVXPY solver registration, devices, optional license check, CUDA driver probe, ConicShield commit, and selected solver settings. Secrets (license keys, index tokens) are redacted.

Production evidence may attach `capabilities_evidence_subset` from the same discovery path.

## Bootstrap

```bash
# Public (Windows / macOS / Linux) — idempotent, no credentials
CONICSHIELD_BOOTSTRAP_PROFILE=public bash scripts/bootstrap_moreau.sh
# PowerShell
pwsh scripts/bootstrap_moreau.ps1 -Profile public

# Vendor CPU (Linux/WSL only)
export MOREAU_EXTRA_INDEX_URL=...   # do not echo
export MOREAU_LICENSE_KEY=...       # written to ~/.moreau/key without printing
CONICSHIELD_BOOTSTRAP_PROFILE=moreau-cpu bash scripts/bootstrap_moreau.sh
```

Native Windows Moreau installs are unsupported; the PowerShell script directs vendor profiles to WSL2.

Qualified Windows modes (public / WSL-native repo / Moreau sidecar) are documented in
[`WINDOWS_OPERATING_MODES.md`](WINDOWS_OPERATING_MODES.md). The sidecar is a qualification
surface over a persistent WSL worker — it does **not** claim native Moreau-on-Windows or
production readiness until qualification notes say what passed.

## Both approved channels during migration

1. Vendor GemFury (or successor) extra-index + license file — primary governed channel.
2. Explicitly attested internal mirrors listed in Vendor CI — secondary.

Default PyPI `moreau` is **not** an approved channel.
