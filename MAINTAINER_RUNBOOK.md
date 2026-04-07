# ConicShield Benchmark Maintainer Runbook

This runbook describes the operational procedures for maintaining the ConicShield benchmark system.

It is the human companion to:
- `BENCHMARK_GOVERNANCE.md`
- the artifact validator
- fixture policy
- native parity gate
- promotion policy
- family manifests
- release orchestration
- governance audit
- governance dashboard

The benchmark system is governed. Do not bypass these procedures informally.

## Core principle

A benchmark result is a governed claim about a stable task.

When something changes, always determine which layer changed:
1. implementation
2. reference fixture
3. task contract

Do not treat those as interchangeable.

## Quick decision tree

### Case A: CI is red on native parity
Ask:
- Did the implementation change?
- Did the fixture change?
- Did the task contract change?

### Case B: benchmark run validates but is not promotable
Ask which gate is red:
- parity
- promotion
- review-lock compatibility
- artifact validation

### Case C: a semantic change is intentional
Do not publish into the current family. Start family-bump procedure.

### Case D: fixture needs regeneration
Use the fixture regeneration procedure. Do not overwrite the fixture casually.

### Case E: a run appears good and all gates are green
Use release orchestration. Do not edit `CURRENT.json` manually.

## Standard commands

Tests marked `@pytest.mark.slow` (stress-scale replay, heavy subprocess work) are **excluded** from the default suite by [`pyproject.toml`](pyproject.toml) (`not slow`), matching [`ci.yml`](.github/workflows/ci.yml). Run them locally with `python -m pytest tests/ -q -m "slow or not slow"` (see [`docs/DEVENV.md`](docs/DEVENV.md)). Add a scheduled or manual workflow if you want slow tests in CI.

### Validate a run bundle
```bash
python -m conicshield.artifacts.validator_cli --run-dir benchmarks/runs/<run_id>
```

### Validate the parity fixture
```bash
python -m conicshield.parity.regenerate_fixture --reference-dir tests/fixtures/parity_reference
```

### Build a demo transition bank (offline)
```bash
python -m conicshield.bench.build_transition_bank --demo --out /tmp/demo_bank.json
```

### Build a bank from an inter-sim-rl offline graph export

With the patched `inter-sim-rl`, record `offline_transition_graph` and per-address coordinates into `offline_transition_graph_export/v1` JSON (see `schemas/offline_transition_graph_export.schema.json` and `tests/fixtures/offline_graph_export_minimal.json`).

```bash
python -m conicshield.bench.build_transition_bank \
  --from-offline-graph-export path/to/export.json \
  --out /tmp/from_env_bank.json
```

### Post–wave 4 operational spine (A1–A5)

Execute in order for milestones M2→M6 (see `ENGINEERING_HANDOFF_IMPLEMENTATION_PLAN.md` §9, `ENGINEERING_STATUS.md` operational backlog).

After material edits to banks, replay, artifacts, governance, or adapters, run **`make verify-extended`** (and solver-marked tests or the **Vendor CI track** (`vendor-ci-moreau`) when touching the solver stack) so regressions surface before you promote fixtures or publish.

1. **A1 — Pin and upstream:** Ensure M2 semantics (action-conditioned transitions, `get_shield_context`) are on your canonical fork or upstream. Update `third_party/inter-sim-rl/REVISION` (`sha=`, `commit_url=`, `recorded_utc`) whenever the checkout changes. With a full git checkout, `tests/test_third_party_pins.py` must pass in CI.
2. **A2 — Real bank:** Record `offline_transition_graph_export/v1` JSON from the patched environment, then run `build_transition_bank --from-offline-graph-export` and keep provenance (bank id, notes). Validate the output JSON against project expectations before benchmarking.
3. **A3 — Reference run and fixture:** Run `reference_run` with the real solver path (not `--passthrough-projector`) for reference arms; `python -m conicshield.artifacts.validator_cli --run-dir …`; promote with `scripts/regenerate_parity_fixture.py` per `docs/PARITY_FIXTURE_PROMOTION.md`.
4. **A4 — Native parity:** After the fixture is promoted, green **Vendor CI track** (`vendor-ci-moreau`) or local `make parity-native-licensed`; adjust `conicshield/parity/gates.py` thresholds only using parity artifacts from real runs. Record `moreau` / `cvxpy` / `cvxpylayers` versions in `ENGINEERING_STATUS.md`.
5. **A5 — Publish:** Copy `benchmarks/templates/governance_decision.template.md` to the run dir as `governance_decision.md`; `finalize_cli` → `release_cli` (dry-run then real) → publish via `release_cli` / `publish-benchmark` workflow as appropriate; `audit_cli --strict` and dashboard. Never hand-edit `benchmarks/releases/.../CURRENT.json`.

### Produce a governed run bundle (reference path)
On a machine with the solver stack (or use `--passthrough-projector` only for structural smoke tests):

```bash
python -m conicshield.bench.reference_run --out benchmarks/runs/<run_id> --bank /path/to/transition_bank.json
python -m conicshield.bench.reference_run --out /tmp/smoke --bank tests/fixtures/parity_reference/transition_bank.json --passthrough-projector
```

### Promote a validated bundle into the parity fixture
After `validate_run_bundle` passes on the source directory:

```bash
python scripts/regenerate_parity_fixture.py --source benchmarks/runs/<run_id>
```

Then update `tests/fixtures/parity_reference/REGENERATION_NOTE.md` per fixture policy.

Full checklist: `docs/PARITY_FIXTURE_PROMOTION.md`.

### Run native parity against the frozen fixture
```bash
make parity-native-licensed
```

Equivalent explicit invocation:

```bash
python -m conicshield.parity.cli   --reference-dir tests/fixtures/parity_reference   --reference-arm-label shielded-rules-plus-geometry   --out-dir output/native_parity_ci
```

### Finalize governance status for a run
```bash
python -m conicshield.governance.finalize_cli   --run-dir benchmarks/runs/<run_id>   --family-id conicshield-transition-bank-v1   --task-contract-version v1   --fixture-version fixture-v1   --reference-fixture-dir tests/fixtures/parity_reference   --parity-summary-path output/native_parity_ci/parity_summary.json   --current-release-path benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json
```

### Dry-run release decision
```bash
python -m conicshield.governance.release_cli   --run-dir benchmarks/runs/<run_id>   --family-id conicshield-transition-bank-v1   --reason "candidate release review"   --dry-run
```

### Publish same-family release
```bash
python -m conicshield.governance.release_cli   --run-dir benchmarks/runs/<run_id>   --family-id conicshield-transition-bank-v1   --reason "promoted after green artifact, parity, and promotion gates"
```

### Publish with family bump
```bash
python -m conicshield.governance.release_cli   --run-dir benchmarks/runs/<run_id>   --family-id conicshield-transition-bank-v1   --reason "new task contract requires family fork"   --allow-family-bump
```

### Audit the whole governance tree
```bash
python -m conicshield.governance.audit_cli --strict
```

### Generate the governance dashboard
```bash
python -m conicshield.governance.dashboard_cli   --json-output output/governance_dashboard.json   --markdown-output output/governance_dashboard.md
```

## Developer environment and dependency lockfile

### Locked dev install (same as CI)

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

### Regenerate `requirements-dev.txt`

After editing `[project.optional-dependencies] dev` in `pyproject.toml`, use Python **3.11** if possible, then:

```bash
make compile-deps
```

### Solver stack version bumps (release chore)

When changing vendor Moreau setup or CVXPY integration pins in `pyproject.toml` (`cvxpy`, `cvxpylayers`, `moreau`) or upgrading documented lower bounds:

1. Follow the checklist in [`docs/MOREAU_API_NOTES.md`](docs/MOREAU_API_NOTES.md) (*Vendor upgrade checklist*).
2. Run **Vendor CI track** (`vendor-ci-moreau`) (or local Linux/WSL2 vendor mode via `bash scripts/bootstrap_moreau.sh`, then `make test-vendor-moreau` / `make parity-native-licensed`).
3. Update [`ENGINEERING_STATUS.md`](ENGINEERING_STATUS.md) **Validated solver stack** from the job Summary or `vendor_solver_versions` artifact (`solver_versions.json`).

### Local quality gates (optional)

```bash
make lint typecheck format-check cov
```

### Moreau vendor bootstrap (Linux/WSL2)

This repository treats Moreau as a vendor dependency. Do not assume default-index `pip install moreau` is equivalent to vendor installation.

```bash
export MOREAU_EXTRA_INDEX_URL="https://<TOKEN>:@pypi.fury.io/optimalintellect/"
export MOREAU_LICENSE_KEY="<YOUR_MOREAU_LICENSE_KEY>"
bash scripts/bootstrap_moreau.sh
make test-vendor-moreau
make smoke-solver
make parity-native-licensed
```

### Extended local verification (`make verify-extended`)

Before a large merge, after replay/bank/validator/governance changes, or when debugging CI discrepancies, run:

```bash
make verify-extended
```

This runs **Tier 0** (ruff check, ruff format check, mypy), **Tier 1** (full `tests/` with the same coverage packages and `--cov-fail-under` as `make cov-gates`), **Tier 2** (`@pytest.mark.slow` tests), **Tier 3** (`tests/test_inter_sim_rl_e2e.py` with pytest `addopts` overridden so `inter_sim_rl` is not filtered out—tests skip if no checkout), and **strict `audit_cli`**.

It does **not** run solver-marked tests, native parity CLI, or Hypothesis modules. After a licensed install, add:

```bash
make test-solver
make smoke-solver
make parity-native-licensed
```

If `hypothesis` is installed:

```bash
python -m pytest tests/test_replay_hypothesis_optional.py tests/test_replay_banks_hypothesis_optional.py -q --override-ini "addopts=-q --durations=15" --hypothesis-show-statistics
```

**GitHub:** run the **Vendor CI track** (`vendor-ci-moreau`) in [`.github/workflows/solver-ci.yml`](.github/workflows/solver-ci.yml) manually when solver pins change; use artifacts and Summary for [`ENGINEERING_STATUS.md`](ENGINEERING_STATUS.md).

### Slow test visibility (pytest durations)

Default `pytest` (via `pyproject.toml`) prints the **15 slowest** tests (`--durations=15`) so regressions in replay or governance integration show up in logs without wall-clock assertions. For a longer list locally:

```bash
python -m pytest tests/ -q --durations=25
```

### CI split: default tests vs solver vs native parity

- **Default PR CI** runs `pytest` with `-m "not solver and not requires_moreau and not inter_sim_rl and not slow"` (see `pyproject.toml`). This keeps forks green without GemFury, Moreau, an `inter-sim-rl` checkout, or slow stress tests.
- **Vendor CI track (`vendor-ci-moreau`)** in `.github/workflows/solver-ci.yml` (manual dispatch with secrets) installs the private solver stack and exercises native / CVXPY paths that need a license.
- **Native parity workflow** (`.github/workflows/native-parity.yml`) replays the frozen fixture only; it does not install the full solver stack. Use solver CI (or a licensed workstation) when you need an end-to-end native solve via `conicshield.parity.cli`.
- **Targeted coverage gate** for adapters, bench, and parity modules: `make cov-gates` (see `Makefile` for the current `--cov-fail-under` threshold).


### Secrets

- Do not commit `.env`, GemFury tokens, or Moreau license keys. Use `.env.example` as a template only.
- Public **base CI** does not install the private `moreau` wheel.
- **Vendor CI track (`vendor-ci-moreau`)** in `.github/workflows/solver-ci.yml` (manual `workflow_dispatch`) expects these repository secrets:
  - `GEMFURY_TOKEN` — GemFury read token only (not the full URL).
  - `MOREAU_LICENSE_KEY` — full license string written to `~/.moreau/key` in the job.
- Forks do not receive these secrets; maintainers run solver checks on the canonical repository or locally via `make test-solver`.
- Integration details and doc links: `docs/MOREAU_API_NOTES.md`.

### `inter-sim-rl` checkout and offline tests

- **Pinned upstream:** `third_party/inter-sim-rl/REVISION` and [PATCHES.md](third_party/inter-sim-rl/PATCHES.md) (apply `patches/conicshield-m2-shield-context-and-transitions.patch` until merged upstream).
- **Local clone:** `git clone https://github.com/fraware/inter-sim-rl.git third_party/inter-sim-rl/checkout` then `git checkout <sha>` and `git apply` the M2 patch, **or** rely on CI to clone/apply.
- **`pytest -m inter_sim_rl`:** requires `INTERSIM_RL_ROOT` pointing at that checkout (or a populated `third_party/inter-sim-rl/checkout`). Tests use `offline_transition_graph` only—no Google Maps calls.
- **Published benchmarks:** do not rely on live Maps API during evaluation; build banks offline per `ENGINEERING_HANDOFF_IMPLEMENTATION_PLAN.md` §3.5.

### Optional solver stack verification (Phase 0 acceptance)

Complete once per machine or release candidate:

1. Install: `pip install -e ".[solver,dev]" --extra-index-url "https://<TOKEN>:@pypi.fury.io/optimalintellect/"` (see [Moreau docs](https://docs.moreau.so/installation.html)).
2. Place the license key in `~/.moreau/key` (Windows: `%USERPROFILE%\.moreau\key`).
3. Smoke: `python -c "import moreau"` must succeed.
4. Record in your team notes who verified and when (optional: add a dated line under `ENGINEERING_STATUS.md`).

## Incident playbooks

### Native parity failure
Freeze publication of any run that endorses `shielded-native-moreau`. Inspect parity artifacts and recent changes.

### Artifact validation failure
Treat the run as invalid. Do not review performance claims yet.

### Promotion gate failure
Keep the run as candidate. Do not publish.

### Family compatibility failure
The task changed materially. Do not overwrite the current family.

### Fixture regeneration request
Allowed only for deliberate reference-side reasons. Never regenerate to make parity green.

## What maintainers must never do

- Never edit `CURRENT.json` manually to publish a run
- Never regenerate the fixture casually
- Never promote a run with red artifact, promotion, or required parity gates
- Never overwrite a family when the task contract changed
- Never use a live benchmark run as the parity reference
- Never bypass the run-finalization step

## Triage priorities

1. artifact validity
2. fixture validity
3. parity validity
4. family compatibility
5. promotion thresholds
6. publication state
7. dashboard cosmetics
