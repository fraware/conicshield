# Branch protection checklist (`main`)

GitHub branch protection is configured in repository **Settings → Branches** (not in this tree). Use this checklist when enabling or auditing merge gates.

## Required status checks

Mark these checks as **required** and disable bypass for administrators unless your team explicitly allows it:

| Check | Workflow | Notes |
|-------|----------|-------|
| `quality` | [`ci.yml`](../.github/workflows/ci.yml) | Ruff, format, Mypy, default pytest, verification scripts |
| `conic-trusted-shape` | [`ci.yml`](../.github/workflows/ci.yml) | Public CLARABEL/SCS structural gate (no vendor MOREAU) |
| `governance-audit` | [`governance-audit.yml`](../.github/workflows/governance-audit.yml) | Published-run index `--check`, governance audit CLI |
| `solver-touch` | [`solver-touch.yml`](../.github/workflows/solver-touch.yml) | Path-filtered: index SHA-256, parity, native-arm evidence |

**Path-filtered workflows:** `solver-touch` and `vendor-ci-moreau` only run when matching paths change. In GitHub, prefer **“Require status checks to pass”** with these jobs listed; skipped jobs on unrelated PRs are expected.

## Vendor lane (hybrid policy)

| Check | When | Workflow |
|-------|------|----------|
| `vendor-ci-moreau` | PRs touching native/Moreau/parity/published-run paths on the **canonical** repo (secrets present) | [`solver-ci.yml`](../.github/workflows/solver-ci.yml) (`pull_request` + `workflow_dispatch`) |

**Forks:** do not inherit secrets; maintainers validate with a green manual `workflow_dispatch` or local `make test-vendor-moreau` before merge. See [`CI_MERGE_GATES.md`](CI_MERGE_GATES.md).

## PR author checklist

Use [`.github/pull_request_template.md`](../.github/pull_request_template.md) when opening PRs that touch solver, parity, or published benchmark paths.
