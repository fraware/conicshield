# Changelog

## Reference system (host-realistic flagship)

### 2026-05-28 — Community front door and frozen published-runs v1 API

- README **Start here** block; [COMMUNITY_LAYER.md](docs/COMMUNITY_LAYER.md) as default public map.
- [PUBLISHED_RUNS_API.md](docs/PUBLISHED_RUNS_API.md) v1 stability contract; CLI `summary` / `provenance`.
- Publication-grade bundle README template + `check_public_claim_phrases.py`; examples discipline pass.

### 2026-05-28 — v1 lock verification script

- `scripts/verify_v1_lock.py` + `make verify-v1-lock-quick`; CONTRIBUTING leads with Community layer for consumers.

### 2026-05-28 — Community onboarding hub and read-only verify gate

- `docs/COMMUNITY_LAYER.md`, `docs/PUBLISHED_RUNS_API.md`; `community-verify` no longer mutates bundles in CI.
- Public examples smoke tests (`tests/examples/test_public_examples_smoke.py`).

### 2026-05-28 — Community API and examples alignment

- `get_current_run`, `load_provenance` (`RunProvenance`); `examples/verify_published_run_index.py`.
- Flagship `inspect_flagship_bundle` walkthrough; README export-source row; differentiation Layer F stance in report MD.

### 2026-05-28 — Remove branch protection tooling

- Dropped GitHub branch protection scripts, workflow, docs, and `expected-branch-protection-main.json`.
- `verify-v1-lock` and `reference_system_status.json` use `ci_merge_checks` only; see [`CI_MERGE_GATES.md`](docs/CI_MERGE_GATES.md).

### 2026-05-28 — v1 lock checklist and branch protection apply tooling

- `docs/V1_LOCK_CHECKLIST.md`, `make verify-v1-lock`, `apply_branch_protection_github.py`.
- Windows Makefile uses `python` (not `python3`); `branch_protection` block in reference system status.

### 2026-05-28 — Community dataset verification hardening

- `community_metadata_contract` enforced in `validate_published_bundle_profile.py` and governance tests.
- `make community-verify` and `make finalize-community-dataset`; wired into `reference-authority` CI and refresh cycle.
- `community_dataset` block in `reference_system_status.json`; `finalize_community_dataset.py` orchestrator.
- Published bundle README validate commands use repo-relative paths; index hashes refreshed.
- `conicshield-published-runs` console script; README path regression test.

### 2026-05-28 — Community-facing quickstarts, published_runs API, and examples

- Audience entrypoints: `QUICKSTART_RESEARCHER`, `QUICKSTART_INTEGRATOR`, `QUICKSTART_MAINTAINER`.
- `conicshield.published_runs` API + CLI; `COMMUNITY_METADATA.json` public schema; `examples/` suite.

### 2026-05-28 — Full refresh cadence gate and branch protection audit

- `check_flagship_full_refresh_cadence.py` (requires `live-export-full` + `authority_ok` within 35 days).
- `batch_public_narrative` in reference system status; branch protection snapshot export workflow.

### 2026-05-28 — Refresh #4 full cycle (licensed)

- `make host-realistic-refresh-cycle-licensed` on WSL; refresh #4 amended to `live-export-full` with `authority_ok`.
- `check_flagship_refresh_triggers.py` in CI; `record_reference_refresh.py --amend-last`.

### 2026-05-28 — Cadence policy, community bundles, batch story v2

- `HOST_REALISTIC_CADENCE_POLICY.md`, `REFERENCE_AUTHORITY_LOG.md`, monthly `host-realistic-refresh-cadence` workflow.
- `COMMUNITY_METADATA.json` per published bundle; `PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md`.
- `batch_solve_report` v2 with `batch_story`; refresh #4 recorded (scheduled export path).

### 2026-05-28 — Calendar refresh #3 (cadence)

- `make capture-inter-sim-graph` → `refresh-live-upstream-export-live` → `host-realistic-refresh-cycle` on licensed WSL host.
- `reference_authority_check` green; `EXPORT_PROVENANCE.refresh_history` entry 3 (`calendar-cadence`).

### 2026-05-26 — v1 reference system lock (`49672a2`)

- Required-check docs: `reference-authority` aligned across `CI_MERGE_GATES.md` and `BRANCH_PROTECTION.md`.
- Flagship evidence qualification in bundle READMEs; `REFERENCE_REFRESH_LOG.md` cadence record.
- Batch policy v2: viability enforced, throughput advisory non-blocking.
- `validate_published_bundle_profile.py` for published bundle file profiles.

### 2026-05-26 — Live export path (`381004e`)

- `capture_inter_sim_offline_graph.py`; `EXPORT_PROVENANCE.export_kind: live_upstream_dump`.
- Full `host-realistic-refresh-cycle` on licensed host.

### 2026-05-26 — Refresh execution (`2ff5fea`)

- Flagship re-validation, batch viability report, reference authority gates.
