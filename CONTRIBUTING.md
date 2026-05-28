# Contributing to ConicShield

Thank you for contributing. This repository separates **public structural CI** from **vendor Moreau validation** by design.

**Using the repo (not changing it)?** Start at [Community layer](docs/COMMUNITY_LAYER.md) — then run `make onboard`.

**Changing the repo?** Continue below. Guides: [Researcher](docs/QUICKSTART_RESEARCHER.md) · [Integrator](docs/QUICKSTART_INTEGRATOR.md) · [Public claims](docs/PUBLIC_CLAIMS.md)

## Before you open a PR

1. Install the dev environment ([`docs/DEVENV.md`](docs/DEVENV.md)).
2. Run `make onboard` (or `make community-verify` when touching published bundles or `conicshield.published_runs`).
3. Run `make lint typecheck` and `make test`.
4. For benchmark/governance changes: `make verify-reference-system`, `make community-verify`, and `make verify-v1-lock-quick` when appropriate.

## Public claim surface

PRs that change **README**, **docs/**, **examples/**, or **published bundle READMEs** must:

1. Align with [`docs/PUBLIC_CLAIMS.md`](docs/PUBLIC_CLAIMS.md) (and related stance docs linked from [COMMUNITY_LAYER.md](docs/COMMUNITY_LAYER.md)).
2. Pass `python scripts/check_public_claim_phrases.py` (included in `make verify-v1-lock-quick`).

## Required CI (public lane)

| Check | What it proves |
|-------|----------------|
| `quality` | Lint, types, default pytest, verification scripts |
| `conic-trusted-shape` | CLARABEL/SCS structural conic correctness |
| `governance-audit` | Index integrity, audit CLI, publish rehearsal |
| `reference-authority` | `verify-reference-system`, `community-verify`, bundle profile |

Path-filtered: `solver-touch`, `vendor-ci-moreau` (see [`docs/DEVENV.md`](docs/DEVENV.md)).

## Vendor Moreau (Policy B)

Solver-touching PRs need vendor proof in the PR body: green `vendor-ci-moreau`, maintainer workflow link, or licensed `make test-vendor-moreau` summary. Do not commit license keys or `.env` secrets.

## Published benchmark bundles

1. Validate under `benchmarks/runs/<run_id>/`.
2. Copy to `benchmarks/published_runs/<run_id>/` (update `.gitignore` allowlist).
3. Update family `CURRENT.json` when appropriate.
4. `make finalize-community-dataset` then `python scripts/refresh_published_run_index.py`.
5. `make verify-v1-lock-quick` before merge.

**Host-realistic refresh:** `make host-realistic-refresh-cycle-licensed` (records [`benchmarks/reports/reference_refresh_log.md`](benchmarks/reports/reference_refresh_log.md)).

## Scope discipline

Do not claim: `progress`/`clearance` constraints, production autograd, non-flagship families as reference authority, Maps/session navigation graphs, universal batch speedup. See [`docs/PUBLIC_CLAIMS.md`](docs/PUBLIC_CLAIMS.md).
