# Engineering status

Living summary of what the repository actually contains versus what remains scaffold or external work. Update this file when milestones in `ENGINEERING_HANDOFF_IMPLEMENTATION_PLAN.md` land.

## Complete in-repo (verified against tree and tests)

- Python package `conicshield/` with core solver seams (`solver_factory`, `moreau_compiled`), specs (`compiler`), inter-sim-rl adapter (`adapters/inter_sim_rl/shield.py`, `policy.py`, `geometry_prior.py`), bench modules (`transition_bank`, `replay_graph_env`, episode runner, metrics, report), artifacts (validator, writer, run spec, payloads), parity (replay, gates, fixture policy, CLI), and governance (finalize, release, publish, audit, dashboard, family manifest/policy, registry helpers).
- Root-level JSON Schemas in `schemas/` (config, summary, episodes, governance status).
- Benchmark layout: `benchmarks/registry.json`, family release directory for `conicshield-transition-bank-v1`, run bundle area documented under `benchmarks/runs/`.
- Reference parity fixture under `tests/fixtures/parity_reference/` with explicit bootstrap/synthetic note in `REGENERATION_NOTE.md`.
- Policy and runbook markdown: `BENCHMARK_GOVERNANCE.md`, `MAINTAINER_RUNBOOK.md`, `docs/*` including architecture, integration, fixture and release policy.
- GitHub Actions: **`ci` workflow** runs full `pytest tests/` on every pull request and on pushes to `main` (`.[dev]` only, no solver extras); plus path-filtered governance audit, dashboard, fixture policy, native parity spot-check, and manual release/publish workflows.

## Local verification

- `pip install -e ".[dev]"` then `pytest tests/` runs the full current suite (on the order of twenty tests across governance, artifacts, shield logic, transition bank, replay env, parity, and dashboard).

## Scaffold / not production-complete

- Moreau reference and native call sites must be validated against a real installed Moreau package (signatures, telemetry fields, optional dependency errors).
- No solver smoke-test CLI yet (Phase 1.5 in the handoff).
- Pytest markers for optional solver integration (`solver`, `requires_moreau`, etc.) are not configured in `pyproject.toml` or tests yet (Phase 1.4).
- Parity reference fixture is explicitly a bootstrap synthetic stream until replaced through the governed regeneration process.
- `inter-sim-rl` is not vendored; adapter and docs describe seams only until a pinned fork and live integration exist.

## External dependencies

- Optional `solver` extra (`cvxpy`, `moreau`, etc.) and license setup described in `README.md`.
- Real benchmark substrate depends on patched `inter-sim-rl` (or mirror) and offline transition-bank generation, as described in `docs/INTER_SIM_RL_INTEGRATION.md` and Phase 2–3 of the handoff.

## CI layout

- Base coverage: `.github/workflows/ci.yml` runs the full suite without solver extras on all PRs and on `main`.
- Solver-heavy checks remain in path-filtered workflows (for example native parity) until a separate solver-enabled job is added per the handoff test plan.

## Python baseline

- `pyproject.toml` declares `requires-python = ">=3.11"`; several workflows use Python 3.12. Align documented canonical version with CI (Phase 0.2).

## Package metadata

- Author field in `pyproject.toml` is still placeholder scaffold text (Phase 0.3).
