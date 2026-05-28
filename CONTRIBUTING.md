# Contributing to ConicShield

Thank you for contributing. This repository separates **public structural CI** from **vendor Moreau validation** by design.

**Using the repo (not changing it)?** Start at [Community layer](docs/COMMUNITY_LAYER.md) — quickstarts, published-run API, and runnable examples.

**Changing the repo?** Continue below. Audience guides: [Researcher](docs/QUICKSTART_RESEARCHER.md) · [Integrator](docs/QUICKSTART_INTEGRATOR.md) · [Maintainer](docs/QUICKSTART_MAINTAINER.md) · [Public claims](docs/PUBLIC_CLAIMS.md)

## Before you open a PR

1. Install the dev environment ([`docs/DEVENV.md`](docs/DEVENV.md)).
2. Run `make lint typecheck` and `make test` (or `python -m pytest tests/ -q`).
3. For benchmark/governance changes, run `make verify-reference-system` and `make community-verify` when touching published bundles or `conicshield.published_runs`.
4. Read [`docs/CI_MERGE_GATES.md`](docs/CI_MERGE_GATES.md), [`docs/REVIEWER_MERGE_CHECKLIST.md`](docs/REVIEWER_MERGE_CHECKLIST.md), and [`docs/REFERENCE_EVIDENCE_TIERS.md`](docs/REFERENCE_EVIDENCE_TIERS.md).

## Required CI (public lane)

These checks run on every PR to `main` and should be green:

| Check | What it proves |
|-------|----------------|
| `quality` | Lint, types, default pytest, verification scripts |
| `conic-trusted-shape` | CLARABEL/SCS structural conic correctness (no vendor secrets) |
| `governance-audit` | Published-run index integrity, governance audit CLI, publish rehearsal |
| `reference-authority` | `verify-reference-system`, `community-verify`, batch viability, bundle profile |

## Path-filtered checks

| Check | When it runs |
|-------|----------------|
| `solver-touch` | PRs touching solver, parity, `benchmarks/published_runs/`, governance scripts, etc. |
| `vendor-ci-moreau` | Same paths on the **canonical** repository when `GEMFURY_TOKEN` and `MOREAU_LICENSE_KEY` are configured |

If `solver-touch` does not appear on your PR, you did not change tracked paths — that is expected.

## Vendor Moreau policy (binding attestation)

Solver-touching PRs **must not merge** without vendor proof in the PR body. `vendor-ci-moreau` is **not** a required GitHub status check (fork-friendly); the attestation rule is binding for reviewers.

**Canonical repository (secrets available):** include one of:

- Green `vendor-ci-moreau` (automatic on path match), or
- Link to a maintainer `workflow_dispatch` run on your branch, or
- Licensed local `make test-vendor-moreau` summary (paste key pass/fail lines).

**Forks (no secrets):** run public CI locally, then ask a maintainer to merge only after vendor attestation above.

Do not commit license keys, Gemfury tokens, or filled `.env` files.

## Changing published benchmark bundles

1. Produce and validate under `benchmarks/runs/<run_id>/`.
2. Copy to `benchmarks/published_runs/<run_id>/` and whitelist the path in [`benchmarks/published_runs/.gitignore`](benchmarks/published_runs/.gitignore).
3. Add the path to the family `benchmark_bundle_paths` in `benchmarks/releases/<family_id>/CURRENT.json` when appropriate.
4. Run `python scripts/refresh_published_run_index.py` and commit `benchmarks/PUBLISHED_RUN_INDEX.json`.
5. Follow [`docs/MAINTAINER_RUNBOOK.md`](docs/MAINTAINER_RUNBOOK.md) for finalize / release / audit when publishing.

**Host-realistic export evidence:** use [`scripts/run_host_realistic_publish.py`](scripts/run_host_realistic_publish.py) with a non-minimal export JSON (see [`benchmarks/external_evidence/`](benchmarks/external_evidence/)).

## Scope discipline

Do not claim or document support for:

- `progress` / `clearance` constraint kinds ([ADR](docs/adr/001-progress-clearance-constraints.md)),
- production shield autograd ([`docs/DIFFERENTIATION_PUBLIC_STANCE.md`](docs/DIFFERENTIATION_PUBLIC_STANCE.md)),
- `conicshield-shield-qp-micro-v1` or other families as reference authority (flagship is `host-realistic-20260525` only),
- Maps/session navigation graphs (export is host-realistic fork via inter-sim),
- universal batch speedup (viability ≠ throughput advisory).

See [`docs/ROADMAP.md`](docs/ROADMAP.md), [`docs/REFERENCE_AUTHORITY.md`](docs/REFERENCE_AUTHORITY.md).
