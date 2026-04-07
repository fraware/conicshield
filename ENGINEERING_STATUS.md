# Engineering status

Living summary of what the repository actually contains versus what remains scaffold or external work. Update this file when milestones in `ENGINEERING_HANDOFF_IMPLEMENTATION_PLAN.md` land.

**Documentation index:** see [`README.md`](README.md) *Documentation map* for policies, verification ladder, and benchmarks.

## Complete in-repo (verified against tree and tests)

- Python package `conicshield/` with core solver seams: **reference path** `CVXPYMoreauProjector` (`specs/compiler.py`) using `cp.MOREAU`, and **native path** `NativeMoreauCompiledProjector` (`core/moreau_compiled.py`) using `moreau.Solver` with the same QP family as the reference (see `specs/shield_qp.py`, `specs/native_moreau_builder.py`).
- Shared **telemetry** normalization (`core/telemetry.py`) and structured **`MissingSolverExtraError`** (`solver_errors.py`).
- **Solver smoke CLI:** `python -m conicshield.core.solver_smoke_cli` (JSON report for reference + native arms).
- Specs, adapters (`inter_sim_rl/shield.py` builds `SafetySpec` with simplex, turn feasibility, box, rate), bench, artifacts, parity, governance (unchanged architecture).
- Root-level JSON Schemas in `schemas/`, benchmark registry/releases, parity fixture, policy docs.
- **Phase 0:** `requirements-dev.txt`, `.env.example`, hygiene/import/schema tests, `Makefile` targets. **Phase 0.3 (metadata):** [`pyproject.toml`](pyproject.toml) authors (`Fraware`), license (MIT), URLs, and trove classifiers are canonical unless org policy requires a change.
- **CI:** `.github/workflows/ci.yml` — Python 3.11/3.12 matrix, ruff, mypy, pytest+coverage (**no solver extras**; default pytest excludes `solver` / `requires_moreau` / `inter_sim_rl` / `slow` per [`docs/DEVENV.md`](docs/DEVENV.md)).
- **Wave 4 (tests + gates):** `validate_run_bundle` validates `transition_bank.json` against `schemas/transition_bank_file.schema.json`. Tests cover missing bundle files, summary drift, bank JSON round-trip replay vs `ReplayGraphEnvironment`, episode-runner `matched_action` / `fallback_used`, parametrized parity missing inputs and ULP gate boundaries, hermetic `finalize_run` → `publish_from_governance_status` with registry/CURRENT/HISTORY checks, `validate_release_directory` and manifest failures, strict `audit_cli` on registry vs `CURRENT.json` skew, reference/native projection telemetry key parity (solver marker), solver smoke CLI with and without `--skip-native`, and JSON Schema validation of upstream `get_shield_context()` beside `validate_shield_context_dict`. `make cov-gates` includes `conicshield.artifacts` and `conicshield.governance` with `--cov-fail-under=76`.
- **Post–wave 4 spine (in-repo gates):** [`tests/test_third_party_pins.py`](tests/test_third_party_pins.py) asserts [`third_party/inter-sim-rl/REVISION`](third_party/inter-sim-rl/REVISION) `sha=` matches `git rev-parse HEAD` in `third_party/inter-sim-rl/checkout` when `.git` exists (skips otherwise). Offline export → bank path is covered by [`tests/fixtures/offline_graph_export_minimal.json`](tests/fixtures/offline_graph_export_minimal.json), [`tests/test_offline_graph_export_bank.py`](tests/test_offline_graph_export_bank.py), and [`tests/test_build_transition_bank_from_json.py`](tests/test_build_transition_bank_from_json.py) CLI tests.
- **Handoff doc + dev matrix:** [`ENGINEERING_HANDOFF_IMPLEMENTATION_PLAN.md`](ENGINEERING_HANDOFF_IMPLEMENTATION_PLAN.md) §1.1 CI note matches [`ci.yml`](.github/workflows/ci.yml) and **Vendor CI track (`vendor-ci-moreau`)** in [`solver-ci.yml`](.github/workflows/solver-ci.yml); Phase 0.2 points to [`docs/DEVENV.md`](docs/DEVENV.md). Vendor upgrade checklist in [`docs/MOREAU_API_NOTES.md`](docs/MOREAU_API_NOTES.md). Slow-tier replay stress: [`tests/test_replay_stress_slow.py`](tests/test_replay_stress_slow.py) (`make test-slow`). Deferred `progress`/`clearance`: [`docs/adr/001-progress-clearance-constraints.md`](docs/adr/001-progress-clearance-constraints.md).
- **Optional Vendor CI track (`vendor-ci-moreau`):** `.github/workflows/solver-ci.yml` — `workflow_dispatch`, secrets `GEMFURY_TOKEN` + `MOREAU_LICENSE_KEY`, runs marked solver tests, smoke CLI, a **live** `reference_run` bundle (artifact `ref_bundle_ci`), then a **full verification bundle** under `/tmp/vendor_verification` (environment_check, smoke_check with `--vendor`, reference_correctness_summary, performance_benchmark with optional `performance_latency.png`, differentiation stub, native Moreau parity via `parity.cli`, `artifact_validation_report` on the reference bundle, `generate_parity_report`, `trust_dashboard`) uploaded as **`vendor_verification_bundle`**, 14-day retention, artifact `vendor_solver_versions` containing **`solver_versions.json`** (filtered `pip freeze` for solver stack), and a Summary snippet for manual paste into the table below.

## Local verification

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -e .
make lint typecheck cov
```

**Heavy regression gate (no solver solve):** `make verify-extended` — ruff, mypy, `cov-gates` coverage run, slow replay stress, `inter_sim_rl` e2e module (skips without checkout), `audit_cli --strict`. See [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md) *Extended local verification* for solver + Hypothesis follow-ups and when to run the **Vendor CI track** (`vendor-ci-moreau`) on GitHub.

With solver extras + license:

```bash
pip install -e ".[solver,dev]" --extra-index-url "https://<TOKEN>:@pypi.fury.io/optimalintellect/"
make test-solver
make smoke-solver
make parity-native-licensed
```

## Scaffold / follow-on

- **Phase 2 (in-repo done):** `schemas/shield_context.schema.json`, fake env + shield integration tests, policy adapter tests, `inter_sim_rl` pytest marker, optional `inter-sim-rl-ci.yml`, fork pin docs under `third_party/inter-sim-rl/`.
- **Phase 2 (external):** upstream patches on [fraware/inter-sim-rl](https://github.com/fraware/inter-sim-rl) for `get_shield_context()`, action-conditioned transitions; pin is `third_party/inter-sim-rl/REVISION` (SHA `f1f04ee11d064262f5ee2810abfcb01715260182` as of 2026-04-06). Fork / clone URL policy: `third_party/inter-sim-rl/README.md` (optional Actions variable `INTERSIM_RL_REPO_URL` for `inter-sim-rl-ci`).
- **Phase 3–5 (in-repo):** `python -m conicshield.bench.build_transition_bank` (including `--from-offline-graph-export` for M3), `reference_run`, replay determinism / no-HTTP tests, `scripts/regenerate_parity_fixture.py`, fixture promotion checklist `docs/PARITY_FIXTURE_PROMOTION.md`, Hypothesis-backed contract property test (optional dep), **Vendor CI track (`vendor-ci-moreau`)** reference bundle + native parity gate.
- **Constraint kinds** `progress` and `clearance` in `SafetySpec` are not implemented for projection (`NotImplementedError` in [`conicshield/specs/shield_qp.py`](conicshield/specs/shield_qp.py)). Deferred ADR: [`docs/adr/001-progress-clearance-constraints.md`](docs/adr/001-progress-clearance-constraints.md).
- **Parity fixture** remains bootstrap/synthetic until you promote a real reference run via `scripts/regenerate_parity_fixture.py`.
- **Vendor drift:** re-run checks in `docs/MOREAU_API_NOTES.md` when upgrading `moreau` / `cvxpy` / `cvxpylayers`.

## Package metadata

- `pyproject.toml` lists Fraware, URLs, classifiers.

## Solver verification

- Automated only in the **Vendor CI track** (`vendor-ci-moreau`) with secrets, or locally with `make test-solver` / `make parity-native-licensed`. Base CI does not call `solve()`.

## Validated solver stack (Phase 1 closeout)

After a green **Vendor CI track** run (`vendor-ci-moreau`) or local `make test-solver` run on a licensed machine, record the resolved versions here so upgrades are auditable.

| Package        | Version (pip) | Date validated (UTC) | Notes                          |
| -------------- | ------------- | -------------------- | ------------------------------ |
| `moreau`       | _from Vendor CI track (`vendor-ci-moreau`) Summary or local freeze_ | | From Gemfury / vendor install |
| `cvxpy`        | _from Vendor CI track (`vendor-ci-moreau`) Summary or local freeze_ | | `pyproject` asks `>=1.8.2`     |
| `cvxpylayers`  | _from Vendor CI track (`vendor-ci-moreau`) Summary or local freeze_ | | `pyproject` asks `>=1.0.4`     |

**Vendor CI track (`vendor-ci-moreau`):** the workflow uploads artifact `vendor_solver_versions` containing `solver_versions.json` and appends a filtered `pip freeze` to the job Summary on each dispatch; copy those lines (or the JSON) into the table when you promote a release or change the solver pin.

Capture versions locally in one shot:

```bash
pip install -e ".[solver,dev]" --extra-index-url "https://<TOKEN>:@pypi.fury.io/optimalintellect/"
python -m pip freeze | findstr /i "moreau cvxpy cvxpylayers"
# or: python -m pip freeze | grep -iE 'moreau|cvxpy|cvxpylayers'
```

Then paste the three lines into the table above and set the date.

## Current published benchmark family (M6)

- **Registry:** [`benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json`](benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json) — `state` is `uninitialized` until the first governed publish.
- **Benchmark card:** requirements and publication wording are defined in [`BENCHMARK_GOVERNANCE.md`](BENCHMARK_GOVERNANCE.md) (see §10). After publish, the **machine-readable** headline metrics live in each run’s `summary.json`; **`dashboard_cli`** emits consolidated JSON/Markdown under paths you pass (see `MAINTAINER_RUNBOOK.md`).
- **Decision record template for runs:** [`benchmarks/templates/governance_decision.template.md`](benchmarks/templates/governance_decision.template.md) (copy to `governance_decision.md` inside the run directory before publish).
- **Operational sequence:** validate bundle → `make parity-native-licensed` (or **Vendor CI track (`vendor-ci-moreau`)**) → `finalize_cli` → `release_cli` (dry-run then real) → `publish_from_governance_status` via [`publish-benchmark` workflow](.github/workflows/publish-benchmark.yml) or equivalent local orchestration → `audit_cli` / dashboard workflows. Details: `MAINTAINER_RUNBOOK.md`, `BENCHMARK_GOVERNANCE.md`.

## M2–M6 operational closure and release gates

Closing milestones **M2** through **M6** requires licensed solver runs, a real inter-sim-rl export and transition bank, promotion of the parity fixture from a real `reference_run`, green native parity on that fixture, and a first governed publish. The repository code and tests support this path; they do not replace it.

- **Release gate checklist (human):** [`ENGINEERING_HANDOFF_IMPLEMENTATION_PLAN.md`](ENGINEERING_HANDOFF_IMPLEMENTATION_PLAN.md) §8 — use before treating a run as real, before endorsing native, and before publish.
- **Command sequence:** [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md) — *Post–wave 4 operational spine (A1–A5)*.
- **Progress:** track **A1–A5** in *Operational backlog* below; update [`CURRENT.json`](benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json) only through publish orchestration.

## Operational backlog (handoff Phases 2–6, tasks A1–A5)

Check these off as the team completes external or licensed steps (see `ENGINEERING_HANDOFF_IMPLEMENTATION_PLAN.md` §9 steps 6–26). The wave-4 test additions above do **not** substitute for these operational steps; they exercise orchestration and validation paths in isolation.

**Ordered runbook (commands):** see [MAINTAINER_RUNBOOK.md](MAINTAINER_RUNBOOK.md) section *Post–wave 4 operational spine (A1–A5)*.

- **A1 — Upstream control:** M2 semantics merged or fork is canonical; [`third_party/inter-sim-rl/REVISION`](third_party/inter-sim-rl/REVISION) `repository=` + `sha=` updated; patch apply is no-op when upstream matches. **In-repo:** pin-vs-checkout test above; after changing the checkout, run `git rev-parse HEAD` in the checkout and update `sha=` + `commit_url=` + `recorded_utc` in `REVISION`. **Status:** confirm upstream merge independently when using a fork.
- **A2 — Real bank:** Transition bank produced from patched `inter-sim-rl` offline export (see `docs/INTER_SIM_RL_INTEGRATION.md`, `build_transition_bank --from-offline-graph-export`). **In-repo:** schema + library + CLI path validated on `tests/fixtures/offline_graph_export_minimal.json`; replace with a real env export for benchmark runs.
- **A3 — Real fixture:** Licensed `reference_run` (no passthrough) → validate → [`scripts/regenerate_parity_fixture.py`](scripts/regenerate_parity_fixture.py) → [`docs/PARITY_FIXTURE_PROMOTION.md`](docs/PARITY_FIXTURE_PROMOTION.md) checklist. **On completion:** refresh the “parity fixture” bullet under *Scaffold / follow-on* and this file’s wave-4 notes if fixture semantics change.
- **A4 — Parity endorsement:** [`.github/workflows/native-parity.yml`](.github/workflows/native-parity.yml) stays replay-only; **Vendor CI track (`vendor-ci-moreau`)** (or local licensed parity) green on promoted fixture; tighten [`conicshield/parity/gates.py`](conicshield/parity/gates.py) only with evidence from real distributions. **On completion:** fill *Validated solver stack* table from Vendor CI track (`vendor-ci-moreau`) Summary.
- **A5 — First publish:** `governance_decision.md` on run → finalize → release → publish orchestration → strict audit/dashboard; [`CURRENT.json`](benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json) updated only via publish path. **On completion:** set *Current published benchmark family* above to reflect `state: published` and real `current_run_id`.

Pre-publish checklist: `ENGINEERING_HANDOFF_IMPLEMENTATION_PLAN.md` §8 (*Benchmark and release operations checklist*).

**While advancing A1–A5:** run `make verify-extended` after material changes to replay, transition banks, artifacts, governance, or inter-sim adapters; add `make test-solver` / **Vendor CI track** (`vendor-ci-moreau`) after solver or parity-gate edits. Operational steps themselves (real export, licensed `reference_run`, publish) still require the runbook spine and §8.

## Deferred roadmap (Phases 7–9)

Work **after** first governed publish (M6) unless leadership assigns parallel owners. Full phase text: `ENGINEERING_HANDOFF_IMPLEMENTATION_PLAN.md` (Phases 7, 8, 9).

| Phase | Goal (summary) | Entry criteria | Owner (assign) | Exit criteria (measurable) |
| ----- | -------------- | -------------- | -------------- | --------------------------- |
| **7 — Retraining** | Retrain in action-conditioned env; compare unshielded vs shield-at-inference vs shield-in-loop; govern results. | M6 done; freeze or fork family if state contract / objective / semantics change materially. | TBD | Governed run bundles + summary for each training variant under an explicit family/version. |
| **8 — Formal methods** | Intermediate constraint IR; proof provenance on specs/evidence; optional metadata first. | Does not block M6; start when a family needs proof linkage. | TBD | ADR + optional schema fields; proof-linked metadata round-trips without ambiguity in artifacts. |
| **9 — LabTrust-Gym** | Second benchmark host; new family; reuse artifact and governance stack. | After inter-sim-rl path is stable and published, or parallel team. | TBD | New `FAMILY_MANIFEST` + registry row; at least one validated run bundle for the new host. |

Handoff §9 maps tasks 27–29 to Phase 7 and task 30 to Phase 8 design entry.
