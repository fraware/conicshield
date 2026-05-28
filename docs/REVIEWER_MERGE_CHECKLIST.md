# Reviewer merge checklist (repository law)

**Adopted policy: B** — public required checks stay fork-friendly; **solver-touching PRs must not merge without vendor attestation.**

`vendor-ci-moreau` is intentionally **not** a required GitHub status check. Attestation is **binding** for humans merging to `main`.

## Scope: solver-touching changes

Applies when the PR touches any of:

- `conicshield/core/moreau*`, `conicshield/core/moreau_batched.py`, `solver_factory.py`
- `conicshield/parity/`, `conicshield/bench/` (native/reference paths)
- `benchmarks/published_runs/`, `benchmarks/releases/`, `benchmarks/PUBLISHED_RUN_INDEX.json`
- `benchmarks/external_evidence/`
- `scripts/run_host_realistic_publish.py`, `upgrade_host_realistic_vendor.py`, `refresh_published_run_index.py`, `performance_benchmark.py`, `batch_solve_report.py`, parity/governance scripts listed in [`solver-touch.yml`](../.github/workflows/solver-touch.yml)

## Required before merge

| Step | Requirement |
|------|-------------|
| 1 | Public lane green: `quality`, `conic-trusted-shape`, `governance-audit`, `reference-authority` |
| 2 | If paths match: `solver-touch` green (or explain skip) |
| 3 | **Vendor attestation** in PR body: green `vendor-ci-moreau` run URL **or** maintainer `workflow_dispatch` link **or** pasted `make test-vendor-moreau` summary |
| 4 | If published bundles changed: `refresh_published_run_index.py` committed; `reference_authority_check` passes locally |
| 5 | No secrets, license keys, or filled `.env` in the diff |

## Reviewer sign-off (copy into PR comment)

```text
Merge checklist:
- [ ] Public CI green (including reference-authority)
- [ ] solver-touch green or N/A (paths)
- [ ] Vendor attestation linked: <URL or summary> (required for solver-touch PRs)
- [ ] Published-run index refreshed if bundles changed
```

## Fork PRs

Maintainers merge only after running or dispatching vendor CI on the fork branch and linking evidence.

See also: [`CI_MERGE_GATES.md`](CI_MERGE_GATES.md), [`.github/pull_request_template.md`](../.github/pull_request_template.md).
