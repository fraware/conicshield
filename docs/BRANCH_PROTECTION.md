# Branch protection (`main`)

Configure in **Settings → Branches**. Record changes in [`BRANCH_PROTECTION_RECORD.md`](BRANCH_PROTECTION_RECORD.md) (screenshot or export).

Must match [`CI_MERGE_GATES.md`](CI_MERGE_GATES.md) and [`.github/expected-branch-protection-main.json`](../.github/expected-branch-protection-main.json).

## Required status checks

| Check | Workflow |
|-------|----------|
| `quality` | [`ci.yml`](../.github/workflows/ci.yml) |
| `conic-trusted-shape` | [`ci.yml`](../.github/workflows/ci.yml) |
| `governance-audit` | [`governance-audit.yml`](../.github/workflows/governance-audit.yml) |
| `reference-authority` | [`reference-authority.yml`](../.github/workflows/reference-authority.yml) |
| `solver-touch` | [`solver-touch.yml`](../.github/workflows/solver-touch.yml) |

**Do not require** `vendor-ci-moreau`.

## Policy B

Solver-touch merges need green `vendor-ci-moreau` **or** maintainer attestation — [`CI_MERGE_GATES.md`](CI_MERGE_GATES.md), [`REVIEWER_MERGE_CHECKLIST.md`](REVIEWER_MERGE_CHECKLIST.md).

## Path-filtered jobs

`solver-touch` and `vendor-ci-moreau` skip on unrelated PRs. Listing them as required is correct; GitHub treats skipped required checks as passing when paths do not match.

## PR template

[`.github/pull_request_template.md`](../.github/pull_request_template.md)
