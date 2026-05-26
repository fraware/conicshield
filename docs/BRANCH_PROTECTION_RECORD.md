# Branch protection record (`main`)

Repository settings are configured in GitHub (**Settings → Branches → Branch protection rules**). This file is the **in-repo audit trail**; attach a screenshot or export when you change required checks.

## Required status checks (canonical)

Must match [`BRANCH_PROTECTION.md`](BRANCH_PROTECTION.md) and [`CI_MERGE_GATES.md`](CI_MERGE_GATES.md):

| Check | Required on `main` |
|-------|-------------------|
| `quality` | yes |
| `conic-trusted-shape` | yes |
| `governance-audit` | yes |
| `reference-authority` | yes |
| `solver-touch` | yes (skips when paths do not match) |
| `vendor-ci-moreau` | **no** (Policy B attestation instead) |

## Maintainer attestation

Solver-touching PRs must include vendor proof in the PR body even when `vendor-ci-moreau` is not a required check. See [`REVIEWER_MERGE_CHECKLIST.md`](REVIEWER_MERGE_CHECKLIST.md).

## Audit log

| Date (UTC) | Changed by | Evidence |
|------------|------------|----------|
| 2026-05-26 | Engineering plan v1 lock | Docs aligned; enable `reference-authority` in GitHub UI and attach screenshot below |

### Screenshot / export (attach in PR or paste link)

<!-- Maintainer: paste image or link to GitHub branch protection screenshot showing required checks listed above. -->
