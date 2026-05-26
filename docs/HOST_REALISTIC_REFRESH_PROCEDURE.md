# Host-realistic refresh procedure (repeatable operations)

`host-realistic-20260525` is the **current reference milestone**, not a one-time proof. This procedure turns the closed export loop into a **routine maintainer cycle**.

## Cadence

| Trigger | Action |
|---------|--------|
| **Scheduled** | Monthly, or once per upstream environment change |
| **Event-driven** | See [When live re-export is required](#when-live-re-export-is-required) |

## Standard refresh cycle (structural export)

Uses the committed upstream-shaped export in [`benchmarks/external_evidence/`](../benchmarks/external_evidence/). No live simulator dump required.

```bash
# Refresh the family flagship (default: current_run_id on disk):
make host-realistic-refresh-cycle

# New dated milestone + promote to current_run_id:
make host-realistic-refresh-milestone

# Explicit run_id:
python scripts/host_realistic_refresh_cycle.py \
  --run-id host-realistic-YYYYMMDD \
  --promote-release
```

By default the cycle targets **`current_run_id`** from `benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json` when that published bundle exists. Use `--new-milestone` to allocate `host-realistic-YYYYMMDD` instead.

The script runs: vendor publish → parity → finalize → **release sync** when `run_id` is the family `current_run_id` (or `--promote-release`) → vendor batch sweep → README/index/snapshot refresh.

## Live upstream refresh cycle

Capture the graph from pinned `inter-sim-rl` via `RLEnvironment` (M2 patch required), refresh the committed export, then re-publish:

```bash
# 1. Capture raw offline_transition_graph (host-realistic fork via upstream API)
make capture-inter-sim-graph

# 2. Replace committed export + EXPORT_PROVENANCE (export_kind: live_upstream_dump)
make refresh-live-upstream-export-live

# 3. Full governed refresh (defaults to current_run_id)
python scripts/host_realistic_refresh_cycle.py \
  --live-graph-json benchmarks/external_evidence/live_dumps/offline_transition_graph_host_realistic.json \
  --force
```

Or one shot after capture: pass `--live-graph-json` to the refresh cycle (it re-runs step 2 internally).

## When live re-export is required

Maintainers **must** capture a fresh upstream export when any of the following change materially:

| Change | Why |
|--------|-----|
| Upstream simulator patch / `inter-sim-rl` revision pin | Graph topology or transition semantics may drift |
| Action semantics | Benchmark arms compare against new behavior |
| Transition-bank generation | Bank structure must match upstream |
| Shield context / constraint wiring | Native and reference paths must see same spec |
| Solver path (native Moreau, batch API, warm-start) | Performance and parity claims depend on solver stack |

If only governance metadata or docs change, a structural re-publish with `--refresh-governance` is enough.

## After each cycle

1. Commit `benchmarks/published_runs/<run_id>/` and whitelist in [`.gitignore`](../benchmarks/published_runs/.gitignore) if new.
2. Update `benchmark_bundle_paths` in `CURRENT.json` when the run should remain discoverable.
3. `python scripts/refresh_published_run_index.py` and commit `PUBLISHED_RUN_INDEX.json`.
4. `make reference-authority-snapshot` if `current_run_id` or flagship gates changed.
5. If parity gold moves: follow [`PARITY_AND_FIXTURES.md`](PARITY_AND_FIXTURES.md) and update `REGENERATION_NOTE.md`.
6. Record vendor attestation in the PR (see [`REVIEWER_MERGE_CHECKLIST.md`](REVIEWER_MERGE_CHECKLIST.md)).

## Milestone vs release

| Goal | What to do |
|------|------------|
| New auditable bundle only | Refresh cycle **without** `--promote-release` |
| New family `current_run_id` | Refresh cycle **with** `--promote-release` + approved `governance_decision.md` |

Treat each successful cycle as a **dated milestone** (`host-realistic-YYYYMMDD`). Promote to `current_run_id` only when gates are green and maintainers approve same-family publish.

## Related docs

- [`HOST_REALISTIC_RUNBOOK.md`](HOST_REALISTIC_RUNBOOK.md) — technical checklist
- [`REFERENCE_AUTHORITY.md`](REFERENCE_AUTHORITY.md) — flagship release map
- [`PUBLISHED_BUNDLE_CATALOG.md`](PUBLISHED_BUNDLE_CATALOG.md) — artifact surface per bundle
