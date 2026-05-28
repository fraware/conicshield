# CI merge gates

GitHub **Settings → Branches → `main`** must match [`BRANCH_PROTECTION.md`](BRANCH_PROTECTION.md) and [`.github/expected-branch-protection-main.json`](../.github/expected-branch-protection-main.json). Audit: [`BRANCH_PROTECTION_RECORD.md`](BRANCH_PROTECTION_RECORD.md).

## Required status checks

| Check | Workflow | Role |
|-------|----------|------|
| `quality` | [`ci.yml`](../.github/workflows/ci.yml) | Lint, types, default pytest |
| `conic-trusted-shape` | [`ci.yml`](../.github/workflows/ci.yml) | CLARABEL/SCS structural gate |
| `governance-audit` | [`governance-audit.yml`](../.github/workflows/governance-audit.yml) | Index `--check`, publish rehearsal |
| `reference-authority` | [`reference-authority.yml`](../.github/workflows/reference-authority.yml) | `verify-reference-system`, batch viability, bundle profile |
| `solver-touch` | [`solver-touch.yml`](../.github/workflows/solver-touch.yml) | Path-filtered parity + native-arm evidence |

**Not required:** `vendor-ci-moreau` (Policy B below).

`solver-touch` skips when PR paths do not match — expected for docs-only PRs.

## Policy B (binding)

Solver-touch PRs merge only with vendor proof in the PR body:

1. Green `vendor-ci-moreau` on canonical repo, **or**
2. Maintainer attestation (`workflow_dispatch` URL or `make test-vendor-moreau` excerpt).

Forks: maintainer merges after attestation. Checklist: [`REVIEWER_MERGE_CHECKLIST.md`](REVIEWER_MERGE_CHECKLIST.md), [PR template](../.github/pull_request_template.md).

## Lanes

| Lane | Checks | Secrets |
|------|--------|---------|
| Public | All required above except vendor solves | None |
| Vendor | `vendor-ci-moreau` when secrets present | `GEMFURY_TOKEN`, `MOREAU_LICENSE_KEY` |

`vendor-ci-moreau`: [`solver-ci.yml`](../.github/workflows/solver-ci.yml) — `workflow_dispatch` + path-filtered PRs.

Verify expected list: `python scripts/verify_expected_branch_protection.py`
