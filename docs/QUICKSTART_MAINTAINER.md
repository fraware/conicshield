# Quickstart: maintainer

Curated path for **refreshing, publishing, and gating** the reference system.

## Refresh cycle (flagship)

Licensed Linux/WSL with project `.venv` and Moreau:

```bash
make host-realistic-refresh-cycle-licensed
```

Policy and triggers: [HOST_REALISTIC_CADENCE_POLICY.md](HOST_REALISTIC_CADENCE_POLICY.md).  
Step list: [HOST_REALISTIC_REFRESH_PROCEDURE.md](HOST_REALISTIC_REFRESH_PROCEDURE.md).

Log each cycle: [REFERENCE_AUTHORITY_LOG.md](REFERENCE_AUTHORITY_LOG.md) (also updated by the Makefile target).

## Published-run workflow

1. Produce under `benchmarks/runs/<run_id>/` (non-passthrough for vendor claims).
2. `validator_cli` → parity → `finalize_cli` → copy to `benchmarks/published_runs/<run_id>/`.
3. `governance_decision.md` (approve) → `release_cli` → `audit_cli --strict`.
4. `make finalize-community-dataset` (metadata, READMEs, index hashes, `COMMUNITY_METADATA` contract)
5. `make community-verify` before opening the PR

Full procedures: [MAINTAINER_RUNBOOK.md](MAINTAINER_RUNBOOK.md), [PUBLISHED_BUNDLE_CATALOG.md](PUBLISHED_BUNDLE_CATALOG.md).

## Index refresh

```bash
python scripts/refresh_published_run_index.py
python scripts/refresh_published_run_index.py --check   # CI style
```

Consumer-facing index docs: [PUBLISHED_RUN_INDEX_SCHEMA.md](PUBLISHED_RUN_INDEX_SCHEMA.md).

## Reference authority checks

```bash
make reference-authority-check
make verify-reference-system
python scripts/generate_reference_system_status.py --check
```

Map: [REFERENCE_SYSTEM.md](REFERENCE_SYSTEM.md), [REFERENCE_AUTHORITY.md](REFERENCE_AUTHORITY.md).

## After a flagship refresh (commit checklist)

- `benchmarks/published_runs/host-realistic-20260525/` (if changed)
- `benchmarks/PUBLISHED_RUN_INDEX.json`
- `benchmarks/external_evidence/EXPORT_PROVENANCE.json`
- `benchmarks/reports/reference_authority_snapshot.json`
- `benchmarks/reports/reference_system_status.json`
- `docs/REFERENCE_AUTHORITY_LOG.md`
- `docs/ENGINEERING_STATUS.md` (or `python scripts/update_engineering_status_from_flagship.py`)

## Strategy

Stay on **Option A** (deepen same family): [V2_STRATEGY.md](V2_STRATEGY.md), [ROADMAP.md](ROADMAP.md). Defer second family, autograd product, and `progress`/`clearance` semantics.

## Next steps

- [CI_MERGE_GATES.md](CI_MERGE_GATES.md)
- [REVIEWER_MERGE_CHECKLIST.md](REVIEWER_MERGE_CHECKLIST.md)
