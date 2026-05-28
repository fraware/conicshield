# Branch protection checklist (`main`)

GitHub branch protection is configured in repository **Settings → Branches** (not in this tree). Use this checklist when enabling or auditing merge gates.

## Required status checks (v1 canonical)

Mark these checks as **required** on `main` and disable bypass for administrators unless your team explicitly allows it. This list must match [`CI_MERGE_GATES.md`](CI_MERGE_GATES.md) and [`.github/expected-branch-protection-main.json`](../.github/expected-branch-protection-main.json).

| Check | Workflow | Notes |
|-------|----------|-------|
| `quality` | [`ci.yml`](../.github/workflows/ci.yml) | Ruff, format, Mypy, default pytest, verification scripts |
| `conic-trusted-shape` | [`ci.yml`](../.github/workflows/ci.yml) | Public CLARABEL/SCS structural gate (no vendor MOREAU) |
| `governance-audit` | [`governance-audit.yml`](../.github/workflows/governance-audit.yml) | Published-run index `--check`, governance audit CLI |
| `reference-authority` | [`reference-authority.yml`](../.github/workflows/reference-authority.yml) | `verify-reference-system`, committed batch viability report, monthly schedule |
| `solver-touch` | [`solver-touch.yml`](../.github/workflows/solver-touch.yml) | Path-filtered: index SHA-256, parity, native-arm evidence |

**Do not** require `vendor-ci-moreau` as a mandatory status check (forks lack secrets; see binding attestation below).

After changing required checks in GitHub, record the change in [`BRANCH_PROTECTION_RECORD.md`](BRANCH_PROTECTION_RECORD.md) (screenshot or link).

**Path-filtered workflows:** `solver-touch` and `vendor-ci-moreau` only run when matching paths change. In GitHub, prefer **“Require status checks to pass”** with these jobs listed; skipped jobs on unrelated PRs are expected.

## Vendor lane (binding attestation, not required check)

| Check | When | Workflow |
|-------|------|----------|
| `vendor-ci-moreau` | PRs touching native/Moreau/parity/published-run paths on the **canonical** repo (secrets present) | [`solver-ci.yml`](../.github/workflows/solver-ci.yml) (`pull_request` + `workflow_dispatch`) |

**Binding rule:** solver-touching PRs merge only with green `vendor-ci-moreau` **or** documented maintainer attestation (workflow URL or `make test-vendor-moreau` summary in the PR). See [`CI_MERGE_GATES.md`](CI_MERGE_GATES.md).

**Forks:** do not inherit secrets; maintainers merge only after attestation.

## PR author checklist

Use [`.github/pull_request_template.md`](../.github/pull_request_template.md) when opening PRs that touch solver, parity, or published benchmark paths.
