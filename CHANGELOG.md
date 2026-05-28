# Changelog

## Reference system (host-realistic flagship)

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
