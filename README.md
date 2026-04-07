# ConicShield

ConicShield is a proof-aware runtime safety layer for learned controllers and cyber-physical systems.

A policy proposes an action. ConicShield solves a constrained optimization problem to find the nearest admissible action under explicit safety constraints. The environment executes the corrected action, not the raw proposal. Every intervention produces structured evidence that can be inspected, hashed, replayed, validated, and governed.

This repository is intentionally comprehensive. It contains:
- solver interfaces and reference/native backends
- benchmark schemas and bundle validation
- parity and promotion gates
- benchmark-family governance
- release orchestration
- governance audit and dashboard generation
- maintainer runbooks and policy documents
- a frozen parity fixture contract
- extensive tests for governance, payloads, schemas, family policy, dashboard logic, and shield logic

## Repository status

This repo is a high-quality implementation scaffold and governance system. It is structured so that:
- governance, artifacts, schemas, and release controls run in public/reference mode
- vendor-native Moreau paths are opt-in and explicitly gated
- external environment integration is explicit and documented rather than hidden

## Supported Python

Canonical matrix, CI behavior, **Vendor CI track (`vendor-ci-moreau`)**, and pytest markers: **[docs/DEVENV.md](docs/DEVENV.md)**.

- **Minimum:** Python 3.11 (`requires-python >=3.11` in `pyproject.toml`).
- **CI:** GitHub Actions runs lint, typecheck, tests, and coverage on **3.11 and 3.12** (no solver extras by default).
- **Solver / CUDA:** For local Moreau + GPU stacks, follow [Moreau installation](https://docs.moreau.so/installation.html). Integration with installed Moreau is verified in the **Vendor CI track (`vendor-ci-moreau`)** (manual dispatch) or a licensed local environment.

## Installation

Public/reference install (default, matches public CI):

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Regenerate locked tooling after changing dev dependencies in `pyproject.toml`:

```bash
make compile-deps
```

Vendor Moreau mode (Linux/WSL2 + vendor index + license):

```bash
export MOREAU_EXTRA_INDEX_URL="https://<TOKEN>:@pypi.fury.io/optimalintellect/"
export MOREAU_LICENSE_KEY="<YOUR_MOREAU_LICENSE_KEY>"
bash scripts/bootstrap_moreau.sh
```

Manual vendor install (if not using bootstrap):

```bash
python -m pip install -e ".[dev]"
python -m pip install "moreau[cuda]" --extra-index-url "$MOREAU_EXTRA_INDEX_URL"
python -m moreau check
```

This repository treats Moreau as a vendor dependency. Do not assume that default-index `pip install moreau` provides the correct solver backend for this project. The supported runtime for Moreau-backed development is Linux or WSL2.

### Secrets and local config

- Never commit GemFury tokens, Moreau license keys, or a populated `.env`. `.env` is gitignored.
- Copy [`.env.example`](.env.example) to `.env` for local variable names only; keep real values out of the repo and CI logs.

## Quick commands

Validate a run bundle:

```bash
python -m conicshield.artifacts.validator_cli --run-dir benchmarks/runs/<run_id>
```

Run governance audit:

```bash
python -m conicshield.governance.audit_cli --strict
```

Generate governance dashboard:

```bash
python -m conicshield.governance.dashboard_cli   --json-output output/governance_dashboard.json   --markdown-output output/governance_dashboard.md
```

Dry-run a release decision:

```bash
python -m conicshield.governance.release_cli   --run-dir benchmarks/runs/<run_id>   --family-id conicshield-transition-bank-v1   --reason "candidate release review"   --dry-run
```

## Layout

```text
conicshield/          # Python package
├── adapters/
│   └── inter_sim_rl/
├── artifacts/
├── bench/
├── core/
├── governance/
├── parity/
├── specs/
└── scripts/
schemas/              # JSON Schema sources for run bundles (repo root, not under the package)
benchmarks/           # registry, releases, run bundles
tests/                # pytest suite (repository root)
docs/
scripts/
```

## Tests

Default `pytest` (and `make test`) runs core/reference paths and excludes vendor-only suites.

```bash
make test
# Public/reference-only suite:
make test-reference
# Vendor Moreau suite (requires vendor install + license):
make test-vendor-moreau
# Solver-marked aggregate:
make test-solver
make smoke-solver
```

## Design principles

1. Formal intent, operational enforcement.
2. Minimal intervention.
3. Evidence by default.
4. Reproducible benchmark bundles.
5. Native compiled results are never trusted without parity.
6. Semantic task changes fork benchmark families instead of silently overwriting scores.

## Verification ladder

End-to-end trust layers (environment, smoke, reference correctness, parity, performance, governance): **[docs/VERIFICATION_AND_STRESS_TEST_PLAN.md](docs/VERIFICATION_AND_STRESS_TEST_PLAN.md)**. The full canonical narrative (sections 1–22) is **[docs/VERIFICATION_MASTER_SPEC.md](docs/VERIFICATION_MASTER_SPEC.md)**.

```bash
make env-check
make smoke-check
make reference-correctness
make trust-dashboard
# Vendor-only: make perf-benchmark, make parity-native-licensed
# Layer G / D helpers: make artifact-validation-report; make parity-report (after parity-native-licensed)
```

Quick artifacts: `python scripts/environment_check.py`, `python scripts/smoke_check.py`, then `python scripts/generate_trust_dashboard.py` for a single HTML/MD summary under `output/`. Default CI uploads `output/` as **`verification-output-<python-version>`**. The **Vendor CI** workflow (`vendor-ci-moreau`, manual dispatch) produces **`vendor_verification_bundle`**: env + vendor smoke + reference correctness + performance (including `performance_latency.png` when solves succeed) + native parity + artifact validation report + parity report + trust dashboard.

## Documentation map

- `ENGINEERING_STATUS.md` — what is implemented vs scaffold, CI gaps, and external deps (keep updated)
- `ENGINEERING_HANDOFF_IMPLEMENTATION_PLAN.md` — phased plan for completing the system
- `docs/PROPOSER_DOCUMENTATION.md` — consolidated design rationale and proposal-level notes
- `BENCHMARK_GOVERNANCE.md` — benchmark governance policy
- `MAINTAINER_RUNBOOK.md` — operational procedures
- `docs/ARCHITECTURE.md` — architecture and repo structure
- `docs/INTER_SIM_RL_INTEGRATION.md` — how to integrate with the external environment
- `docs/FIXTURE_POLICY.md` — frozen parity fixture policy
- `docs/RELEASE_POLICY.md` — release orchestration policy
- `docs/MOREAU_API_NOTES.md` — how ConicShield calls Moreau/CVXPY (verify on upgrades)
- `docs/MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md` — normative install/runtime/test policy for Moreau
- `docs/METRICS_INVENTORY.md` — verification plan §13 metric inventory (stress-test roadmap)
- `tests/README.md` — how `tests/` maps to verification plan §15

## Notes on optional dependencies

This repo intentionally keeps the governance, artifact, and audit stack usable without `cvxpy` or `moreau`.

When the optional solver stack is not installed:
- governance and artifact tests still run
- parity replay logic can still be tested against fake shields
- solver-backed shield execution raises a clear optional-dependency error
