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
| 2026-05-26 | Engineering plan v1 lock | Docs aligned; machine-readable spec: `.github/expected-branch-protection-main.json` |
| 2026-05-28 | Calendar refresh #3 | Cadence in [`REFERENCE_REFRESH_LOG.md`](REFERENCE_REFRESH_LOG.md) (`5485dfb`) |

### Verify locally

```bash
make verify-branch-protection-expectations
# After `gh auth login` (admin read): compares GitHub required checks to spec; exits 1 on mismatch.
```

### Apply / audit (maintainer)

```bash
python scripts/print_branch_protection_gh_recipe.py   # gh api PUT recipe
make verify-branch-protection-expectations            # compare after gh auth login
python scripts/audit_branch_protection_api.py         # GITHUB_TOKEN / gh with admin read
```

Weekly GitHub Action: [`.github/workflows/branch-protection-audit.yml`](../.github/workflows/branch-protection-audit.yml) (`workflow_dispatch` + Mondays 09:00 UTC).

### Screenshot / export (attach in PR or paste link)

<!-- Required: quality, conic-trusted-shape, governance-audit, reference-authority, solver-touch -->
<!-- NOT required: vendor-ci-moreau -->
