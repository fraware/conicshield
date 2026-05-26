# CI merge gates

GitHub branch protection is configured in the repository settings, not in this tree. **Required** checks for `main` (see [`BRANCH_PROTECTION.md`](BRANCH_PROTECTION.md)):

| Check | Workflow | Role |
|-------|----------|------|
| `quality` | [`ci.yml`](../.github/workflows/ci.yml) | Ruff, Ruff format, Mypy, default-marker pytest + coverage, verification scripts |
| `conic-trusted-shape` | [`ci.yml`](../.github/workflows/ci.yml) | Public CLARABEL/SCS conic structural gate (no vendor MOREAU) |
| `governance-audit` | [`governance-audit.yml`](../.github/workflows/governance-audit.yml) | `refresh_published_run_index.py --check` (required + optional integrity surface); governance `audit_cli` rehearsal |
| `solver-touch` | [`solver-touch.yml`](../.github/workflows/solver-touch.yml) | **Path-filtered:** index SHA-256 vs disk, parity-note `run_id`s, native-arm publish evidence, parity tests |

**Path-filtered `solver-touch`:** the job is listed as required in branch protection but **skips** on PRs that do not touch solver/parity/benchmark paths (see workflow `paths:`). That is intentional: unrelated docs-only PRs should not wait on parity replay.

## Binding merge rule (solver-touching changes)

PRs that touch native/Moreau/parity/published-run paths **must not merge** without vendor proof documented in the PR:

1. Green **`vendor-ci-moreau`** on the canonical repository (automatic path match or `workflow_dispatch`), **or**
2. Maintainer attestation: link to a green manual workflow run **or** paste a summary from licensed local `make test-vendor-moreau`.

**Forks (no secrets):** only maintainers merge after attestation; authors run public CI locally and request vendor validation.

`vendor-ci-moreau` is **not** a required GitHub status check (fork-friendly). The attestation rule above is **binding** for humans reviewing merges. See [`CONTRIBUTING.md`](../CONTRIBUTING.md) and [`.github/pull_request_template.md`](../.github/pull_request_template.md).

## Two trust lanes

```mermaid
flowchart TB
  subgraph publicLane [Public lane always on PR]
    Q[quality]
    CTS[conic-trusted-shape]
    GA[governance-audit]
  end
  subgraph conditionalLane [Path-filtered]
    ST[solver-touch]
    VC[vendor-ci-moreau optional]
  end
  publicLane --> Merge[merge to main]
  conditionalLane --> Merge
```

| Lane | Checks | Secrets |
|------|--------|---------|
| **Public** | `quality`, `conic-trusted-shape`, `governance-audit` | None |
| **Vendor** | `vendor-ci-moreau` (path-triggered on canonical repo PRs + manual dispatch) | `GEMFURY_TOKEN`, `MOREAU_LICENSE_KEY` |

`conic-trusted-shape` is the permanent public structural compromise: broad CI coverage without vendor credentials.

## Vendor Moreau workflow

[`solver-ci.yml`](../.github/workflows/solver-ci.yml) (`vendor-ci-moreau`):

- **`workflow_dispatch`** — always available on the canonical repo.
- **`pull_request`** — same path filters as `solver-touch` when secrets exist.

See [`DEVENV.md`](DEVENV.md) for the full matrix and optional workflows.
