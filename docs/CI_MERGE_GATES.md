# CI merge gates (recommended)

GitHub branch protection is configured in the repository settings, not in this tree. Recommended **required** checks for `main`:

| Check | Workflow | Role |
|-------|----------|------|
| `quality` | [`ci.yml`](../.github/workflows/ci.yml) | Ruff, Ruff format, Mypy, default-marker pytest + coverage, verification scripts |
| `conic-trusted-shape` | [`ci.yml`](../.github/workflows/ci.yml) | Public CLARABEL/SCS conic structural gate (no vendor MOREAU) |
| `solver-touch` | [`solver-touch.yml`](../.github/workflows/solver-touch.yml) | Path-filtered job: `refresh_published_run_index.py --check`; pytest for benchmark paths, **full index SHA-256 vs disk** (required bundle files per `validate_run_bundle`), parity-note `run_id` consistency, **current published `summary.json` includes `shielded-native-moreau` when the family lists it**, and parity tests (see workflow `paths:` for triggers) |

**Vendor Moreau** ([`solver-ci.yml`](../.github/workflows/solver-ci.yml)) remains **manual** `workflow_dispatch` (secrets). PRs that touch native solver code should be validated on a licensed host or via that workflow on the canonical repository before merge.

**Operational policy (not encoded in YAML):** Default PR CI does **not** run the full Moreau stack. Teams that want the strongest solver guarantee either (a) mark **`vendor-ci-moreau`** required for specific branches (if secrets exist on the repo), or (b) keep a **maintainer rule**: native/solver-touched PRs get a green manual vendor run or merge only after `make test-vendor-moreau` / Vendor CI on the upstream repo. [`docs/ROADMAP.md`](ROADMAP.md) tracks this as an open policy choice.

See [`DEVENV.md`](DEVENV.md) for the full matrix and optional workflows.
